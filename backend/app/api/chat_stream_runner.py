import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic_ai.exceptions import UsageLimitExceeded

from app.api.chat_trace_schemas import RequestAttachmentItem, RequestHistoryItem, RequestSnapshotRecord
from app.api.chat_stream_types import StreamRunContext, StreamRunMetrics
from app.services.chat_streaming import StreamEventEmitter, StreamState
from app.services.llm.routing import RoutingContext, resolve_runtime_model
from app.services.skills.models import (
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionInvocationRequest,
)


def _safe_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_role_lookup(config_service: Any, role_name: str) -> Optional[dict[str, str]]:
    resolver = getattr(config_service, "resolve_model_role", None)
    if not callable(resolver):
        return None
    resolved = resolver(role_name)
    if not isinstance(resolved, dict):
        return None
    provider = _safe_text(resolved.get("provider"))
    model = _safe_text(resolved.get("model"))
    if not provider or not model:
        return None
    return {"provider": provider, "model": model}


@dataclass
class PromptRuntimeDeps:
    skill_registry: Any
    skill_action_execution_service: Any
    markdown_skill_adapter: Any
    skill_policy_gate: Any
    assemble_runtime_prompt: Any
    build_scope_summary_block: Any
    emit_skill_effectiveness_event: Any
    resolve_skill_runtime_state: Any
    action_preflight_message_builder: Any
    action_approval_message_builder: Any
    action_execution_message_builder: Any


@dataclass
class RetryRuntimeDeps:
    resolve_retry_targets: Any
    build_tool_call_retry_event: Any
    build_tool_call_retry_success_event: Any
    build_tool_call_retry_failed_event: Any
    build_tool_call_mismatch_event: Any
    build_tool_call_mismatch_message: Any


@dataclass
class StreamRunnerDeps:
    logger: Any
    agent_store: Any
    tool_registry: Any
    fetch_ollama_models: Any
    get_model: Any
    chat_service: Any
    config_service: Any
    build_system_prompt: Any
    get_parser: Any
    calculate_usage: Any
    handle_llm_exception: Any
    prompt: PromptRuntimeDeps
    retry: RetryRuntimeDeps
    collect_tool_names: Any
    patch_model_settings: Any
    build_agent_deps: Any
    ensure_ollama_model_available: Any
    format_citations_suffix: Any
    append_continue_message_if_needed: Any
    append_citation_suffix_if_needed: Any
    persist_assistant_message: Any
    should_handle_tool_call_mismatch: Any
    tool_event_tracker_cls: Any
    normalize_finished_ts: Any
    serialize_sse_payload: Any
    iso_utc_now: Any
    resolve_reasoning_state: Any
    build_runtime_meta_payload: Any
    run_agent_stream: Any
    refine_title_once_fn: Any
    build_chat_response_log_payload: Any
    safe_json_log: Any
    env_flag: Any
    env_flag_with_fallback: Any
    agent_cls: Any
    usage_limits_cls: Any


@dataclass
class PreparedRuntime:
    emitter: StreamEventEmitter
    tool_tracker: Any
    tools: List[Any]
    model: Any
    multimodal_service: Any
    validated_images: List[str]
    request: Any
    model_capabilities: Any
    vision_enabled: bool


@dataclass
class PromptPreparation:
    final_tools_list: List[str]
    selected_skill_spec: Any
    selection_reason_code: str
    selection_source: str
    selection_score: int
    visible_skill_count: int
    available_skill_count: int
    always_injected_count: int
    selected_group_ids: List[str]
    resolved_skill_count: int
    summary_injected: bool
    scope_summary_injected: bool
    effective_scope_count: int


def _build_requested_action_content(preflight_result: Any, message_builder: Any) -> str:
    return message_builder(preflight_result)


async def _drain_tool_event_queue(*, ctx: StreamRunContext, deps: StreamRunnerDeps) -> AsyncIterator[str]:
    while not ctx.tool_event_queue.empty():
        payload = await ctx.tool_event_queue.get()
        yield deps.serialize_sse_payload(payload)


async def _invoke_requested_action_platform_tool(
    *,
    ctx: StreamRunContext,
    deps: StreamRunnerDeps,
    tool_tracker: Any,
    agent_id: Optional[str],
    mapped_tool: str,
    enabled_tools: List[str],
    arguments: Dict[str, Any],
) -> str:
    tools = await deps.tool_registry.get_tools_for_agent(
        agent_id,
        enabled_tools=enabled_tools,
    )
    selected_tool = None
    raw_name = mapped_tool.split(":", 1)[1] if mapped_tool.startswith("builtin:") else mapped_tool
    for tool in tools:
        tool_name = getattr(tool, "name", "")
        composite_name = f"builtin:{tool_name}"
        if mapped_tool in {tool_name, composite_name}:
            selected_tool = tool
            break

    if selected_tool is None:
        raise ValueError(f"Requested action tool is unavailable: {mapped_tool}")

    tool_ctx = SimpleNamespace(deps=ctx.deps)
    call_id = f"call_{uuid.uuid4().hex[:8]}"
    validated_args = selected_tool.validate_params(arguments or {})
    started_event = {
        "event": "tool.call.started",
        "call_id": call_id,
        "tool_name": raw_name,
        "args": validated_args,
        "run_id": ctx.run_id,
        "assistant_turn_id": ctx.assistant_turn_id,
    }
    await tool_tracker.on_tool_event(started_event)

    start_time = time.time()
    try:
        result = await selected_tool.execute(tool_ctx, validated_args)
    except Exception as tool_err:
        duration_ms = (time.time() - start_time) * 1000
        await tool_tracker.on_tool_event(
            {
                "event": "tool.call.finished",
                "call_id": call_id,
                "tool_name": raw_name,
                "error": str(tool_err),
                "duration_ms": duration_ms,
                "run_id": ctx.run_id,
                "assistant_turn_id": ctx.assistant_turn_id,
            }
        )
        raise

    duration_ms = (time.time() - start_time) * 1000
    await tool_tracker.on_tool_event(
        {
            "event": "tool.call.finished",
            "call_id": call_id,
            "tool_name": raw_name,
            "result": result,
            "duration_ms": duration_ms,
            "run_id": ctx.run_id,
            "assistant_turn_id": ctx.assistant_turn_id,
        }
    )
    return result


def _resolve_requested_action_tool_args(preflight_result: Any, request: Any) -> Dict[str, Any]:
    return (
        (preflight_result.metadata or {}).get("validated_arguments")
        or getattr(request, "requested_action_arguments", None)
        or {}
    )


def _resolve_requested_action_request_id(request: Any) -> str:
    approval_token = getattr(request, "requested_action_approval_token", None)
    if isinstance(approval_token, str) and approval_token:
        parts = approval_token.rsplit(":", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
    return uuid.uuid4().hex[:12]


def _summarize_history_item(item: Any) -> RequestHistoryItem:
    role = "user"
    content_type = "text"
    content_summary = None
    image_count = 0
    truncated = False

    class_name = item.__class__.__name__
    if class_name == "ModelResponse":
        role = "assistant"
    elif class_name == "ModelRequest":
        role = "user"
    elif class_name.lower().startswith("tool"):
        role = "tool"

    parts = getattr(item, "parts", None)
    if isinstance(parts, list) and parts:
        fragments: List[str] = []
        for part in parts:
            content = getattr(part, "content", None)
            if isinstance(content, list):
                content_type = "mixed"
                for nested in content:
                    if isinstance(nested, str):
                        fragments.append(nested)
                    else:
                        image_count += 1
            elif isinstance(content, str):
                fragments.append(content)
            elif content is not None:
                fragments.append(str(content))
        joined = " ".join(fragment.strip() for fragment in fragments if isinstance(fragment, str) and fragment.strip()).strip()
        if joined:
            content_summary = joined[:240]
            truncated = len(joined) > 240
    else:
        content_summary = str(item)[:240]
        truncated = len(str(item)) > 240

    return RequestHistoryItem(
        role=role,
        content_type=content_type,
        content_summary=content_summary,
        image_count=image_count,
        truncated=truncated,
    )


def _build_request_snapshot_record(
    *,
    ctx: StreamRunContext,
    request: Any,
    prompt_result: Any,
    selected_skill_spec: Any,
    final_tools_list: List[str],
) -> RequestSnapshotRecord:
    attachments = [
        RequestAttachmentItem(
            kind="image",
            name=(image.rsplit("/", 1)[-1] if isinstance(image, str) and image else None),
            content_type=None,
            size_bytes=None,
            redacted=False,
        )
        for image in (ctx.validated_images or [])
    ]
    skill_context: Dict[str, Any] = {}
    if selected_skill_spec is not None:
        skill_context = {
            "selected_skill": {
                "name": getattr(selected_skill_spec, "name", None),
                "version": getattr(selected_skill_spec, "version", None),
            }
        }

    return RequestSnapshotRecord(
        chat_id=ctx.chat_id,
        assistant_turn_id=ctx.assistant_turn_id,
        request_id=ctx.request_id,
        run_id=ctx.run_id,
        created_at=datetime.now(UTC),
        provider=ctx.provider,
        model=ctx.model_name,
        agent_id=getattr(request, "agent_id", None),
        requested_skill=getattr(request, "requested_skill", None),
        deep_thinking_enabled=bool(getattr(request, "deep_thinking_enabled", False)),
        system_prompt=ctx.system_prompt,
        user_message=str(getattr(request, "message", "") or ""),
        message_history=[_summarize_history_item(item) for item in (ctx.history or [])],
        attachments=attachments,
        tool_context={"enabled_tools": list(final_tools_list or [])},
        skill_context=skill_context,
        runtime_flags={
            "event_v2_enabled": bool(ctx.event_v2_enabled),
            "turn_binding_enabled": bool(ctx.turn_binding_enabled),
            "reasoning_display_gated_enabled": bool(ctx.reasoning_display_gated_enabled),
            "summary_injected": bool(getattr(prompt_result, "summary_injected", False)),
            "scope_summary_injected": bool(getattr(prompt_result, "scope_summary_injected", False)),
        },
        redaction={},
        truncation={},
    )


def _persist_request_snapshot(
    *,
    ctx: StreamRunContext,
    deps: StreamRunnerDeps,
    snapshot: RequestSnapshotRecord,
) -> None:
    try:
        deps.chat_service.add_action_event(
            ctx.chat_id,
            {
                "event": "chat.request.snapshot",
                "request_id": ctx.request_id,
                "run_id": ctx.run_id,
                "assistant_turn_id": ctx.assistant_turn_id,
                "snapshot": snapshot.model_dump(mode="json"),
            },
            assistant_turn_id=ctx.assistant_turn_id,
            run_id=ctx.run_id,
        )
    except Exception:
        deps.logger.exception("Failed to persist request snapshot")


def _create_stream_runtime(
    *,
    chat_id: str,
    request: Any,
    history: List[Any],
    validated_images: List[str],
    deps: StreamRunnerDeps,
) -> tuple[StreamRunContext, StreamRunMetrics, StreamEventEmitter, Any]:
    feature_flags = deps.config_service.get_feature_flags()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    assistant_turn_id = f"turn_{uuid.uuid4().hex[:12]}"
    ctx = StreamRunContext(
        chat_id=chat_id,
        request=request,
        history=history,
        validated_images=validated_images,
        feature_flags=feature_flags,
        run_id=run_id,
        request_id=request_id,
        assistant_turn_id=assistant_turn_id,
        event_v2_enabled=bool(feature_flags.get("transparency_event_v2_enabled", True)),
        turn_binding_enabled=bool(feature_flags.get("transparency_turn_binding_enabled", True)),
        reasoning_display_gated_enabled=bool(feature_flags.get("reasoning_display_gated_enabled", True)),
        provider=request.provider,
        model_name=request.model,
        system_prompt=request.system_prompt,
    )
    metrics = StreamRunMetrics()
    emitter = StreamEventEmitter(
        event_v2_enabled=ctx.event_v2_enabled,
        run_id=ctx.run_id,
        assistant_turn_id=ctx.assistant_turn_id,
        serialize_payload=deps.serialize_sse_payload,
        iso_utc_now=deps.iso_utc_now,
    )
    tool_tracker = deps.tool_event_tracker_cls(
        chat_id=ctx.chat_id,
        assistant_turn_id=ctx.assistant_turn_id,
        run_id=ctx.run_id,
        turn_binding_enabled=ctx.turn_binding_enabled,
        emitter=emitter,
        tool_event_queue=ctx.tool_event_queue,
        chat_service=deps.chat_service,
        normalize_finished_ts=deps.normalize_finished_ts,
    )
    return ctx, metrics, emitter, tool_tracker


async def _prepare_prompt_runtime(
    *,
    ctx: StreamRunContext,
    emitter: StreamEventEmitter,
    request: Any,
    deps: StreamRunnerDeps,
) -> AsyncIterator[PromptPreparation | str]:
    ctx.agent_config = None
    if request.agent_id:
        ctx.agent_config = deps.agent_store.get_agent(request.agent_id)

    skill_runtime_state = deps.prompt.resolve_skill_runtime_state(
        agent_config=ctx.agent_config,
        feature_flags=ctx.feature_flags,
        chat_id=ctx.chat_id,
        request_message=request.message,
        requested_skill=request.requested_skill,
    )
    selected_skill_spec = skill_runtime_state["selected_skill_spec"]
    always_skill_specs = skill_runtime_state["always_skill_specs"]
    selection_reason_code = skill_runtime_state["selection_reason_code"]
    selection_source = skill_runtime_state["selection_source"]
    selection_score = skill_runtime_state["selection_score"]
    visible_skill_count = skill_runtime_state["visible_skill_count"]
    available_skill_count = skill_runtime_state["available_skill_count"]
    always_injected_count = skill_runtime_state["always_injected_count"]
    selected_group_ids = skill_runtime_state["selected_group_ids"]
    resolved_skill_count = skill_runtime_state["resolved_skill_count"]
    summary_block = skill_runtime_state["summary_block"]

    prompt_result = deps.prompt.assemble_runtime_prompt(
        agent_config=ctx.agent_config,
        request_system_prompt=ctx.system_prompt,
        request_message=request.message,
        provider=ctx.provider,
        model_name=ctx.model_name,
        selected_skill_spec=selected_skill_spec,
        always_skill_specs=always_skill_specs,
        summary_block=summary_block,
        feature_flags=ctx.feature_flags,
        skill_registry=deps.prompt.skill_registry,
        markdown_skill_adapter=deps.prompt.markdown_skill_adapter,
        skill_policy_gate=deps.prompt.skill_policy_gate,
        build_scope_summary_block=deps.prompt.build_scope_summary_block,
    )
    selected_skill_spec = prompt_result.selected_skill_spec
    agent_provider = _safe_text(getattr(ctx.agent_config, "provider", None))
    agent_model = _safe_text(getattr(ctx.agent_config, "model", None))
    agent_model_selection_mode = _safe_text(getattr(ctx.agent_config, "model_selection_mode", None)) or "direct"
    agent_model_tier = _safe_text(getattr(ctx.agent_config, "model_tier", None))
    agent_model_role = _safe_text(getattr(ctx.agent_config, "model_role", None))
    agent_model_policy = _safe_text(getattr(ctx.agent_config, "model_policy", None)) or "prefer_role"
    upgrade_on_tools = bool(getattr(ctx.agent_config, "upgrade_on_tools", True))
    upgrade_on_multi_skill = bool(getattr(ctx.agent_config, "upgrade_on_multi_skill", True))
    routing_config = {}
    get_routing_config = getattr(deps.config_service, "get_llm_routing_config", None)
    if callable(get_routing_config):
        loaded_routing_config = get_routing_config()
        if isinstance(loaded_routing_config, dict):
            routing_config = loaded_routing_config
    routing_rules = routing_config.get("rules", {}) if isinstance(routing_config.get("rules"), dict) else {}
    resolved_model = resolve_runtime_model(
        RoutingContext(
            request_provider=getattr(request, "provider", None),
            request_model=getattr(request, "model", None),
            request_model_role=getattr(request, "model_role", None),
            agent_provider=agent_provider,
            agent_model=agent_model,
            agent_model_selection_mode=agent_model_selection_mode,
            agent_model_tier=agent_model_tier,
            agent_model_role=agent_model_role,
            agent_model_policy=agent_model_policy,
            routing_default_mode=_safe_text(routing_config.get("default_mode")) or "legacy",
            routing_fallback_policy=_safe_text(routing_config.get("fallback_policy")) or "use_legacy_agent_model",
            auto_upgrade_enabled=bool(routing_config.get("auto_upgrade_enabled", True)),
            tool_call_requires_role=_safe_text(routing_rules.get("tool_call_requires_role")) or "tool_use",
            multi_skill_requires_role=_safe_text(routing_rules.get("multi_skill_requires_role")) or "reasoning",
            upgrade_on_tools=upgrade_on_tools,
            upgrade_on_multi_skill=upgrade_on_multi_skill,
            has_tools=bool(prompt_result.final_tools_list),
            selected_tool_count=len(prompt_result.final_tools_list or []),
            skill_count=max(0, _safe_int(resolved_skill_count, 0)),
            has_images=bool(ctx.validated_images),
            task_hints=[],
        ),
        role_lookup=lambda role_name: _safe_role_lookup(deps.config_service, role_name),
        tier_lookup=lambda tier_name: getattr(deps.config_service, "resolve_model_tier", lambda _name: None)(tier_name),
        default_provider=prompt_result.provider or "openai",
        default_model=prompt_result.model_name or "gpt-4o",
    )
    prompt_provider = _safe_text(getattr(prompt_result, "provider", None))
    prompt_model_name = _safe_text(getattr(prompt_result, "model_name", None))
    if (
        resolved_model.provider != (prompt_provider or resolved_model.provider)
        or resolved_model.model != (prompt_model_name or resolved_model.model)
    ):
        prompt_result = deps.prompt.assemble_runtime_prompt(
            agent_config=ctx.agent_config,
            request_system_prompt=ctx.system_prompt,
            request_message=request.message,
            provider=resolved_model.provider,
            model_name=resolved_model.model,
            selected_skill_spec=selected_skill_spec,
            always_skill_specs=always_skill_specs,
            summary_block=summary_block,
            feature_flags=ctx.feature_flags,
            skill_registry=deps.prompt.skill_registry,
            markdown_skill_adapter=deps.prompt.markdown_skill_adapter,
            skill_policy_gate=deps.prompt.skill_policy_gate,
            build_scope_summary_block=deps.prompt.build_scope_summary_block,
        )
        selected_skill_spec = prompt_result.selected_skill_spec
    ctx.provider = resolved_model.provider
    ctx.model_name = resolved_model.model
    ctx.model_resolution = resolved_model.model_dump(mode="json")
    ctx.system_prompt = prompt_result.system_prompt
    _persist_request_snapshot(
        ctx=ctx,
        deps=deps,
        snapshot=_build_request_snapshot_record(
            ctx=ctx,
            request=request,
            prompt_result=prompt_result,
            selected_skill_spec=selected_skill_spec,
            final_tools_list=prompt_result.final_tools_list,
        ),
    )
    if prompt_result.emitted_event:
        deps.logger.info("Skill %s selected. Tool intersection: %s", selected_skill_spec.name, prompt_result.final_tools_list)
        yield emitter.emit(prompt_result.emitted_event)

    yield deps.prompt.emit_skill_effectiveness_event(
        chat_id=ctx.chat_id,
        emitter=emitter,
        selection_reason_code=selection_reason_code,
        selection_source=selection_source,
        selection_score=selection_score,
        selected_skill_spec=selected_skill_spec,
        visible_skill_count=visible_skill_count,
        available_skill_count=available_skill_count,
        always_injected_count=prompt_result.always_injected_count,
        selected_group_ids=selected_group_ids,
        resolved_skill_count=resolved_skill_count,
        summary_injected=prompt_result.summary_injected,
        scope_summary_injected=prompt_result.scope_summary_injected,
        effective_scope_count=prompt_result.effective_scope_count,
        feature_flags=ctx.feature_flags,
        system_prompt=ctx.system_prompt,
        request_message=request.message,
    )

    yield PromptPreparation(
        final_tools_list=prompt_result.final_tools_list,
        selected_skill_spec=selected_skill_spec,
        selection_reason_code=selection_reason_code,
        selection_source=selection_source,
        selection_score=selection_score,
        visible_skill_count=visible_skill_count,
        available_skill_count=available_skill_count,
        always_injected_count=prompt_result.always_injected_count,
        selected_group_ids=selected_group_ids,
        resolved_skill_count=resolved_skill_count,
        summary_injected=prompt_result.summary_injected,
        scope_summary_injected=prompt_result.scope_summary_injected,
        effective_scope_count=prompt_result.effective_scope_count,
    )


async def _handle_tool_call_mismatch_retry(
    *,
    ctx: StreamRunContext,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    mismatch_resolved = False
    mismatch_config = deps.config_service.get_tool_call_mismatch_config()
    retry_targets = deps.retry.resolve_retry_targets(
        mismatch_config=mismatch_config,
        provider=ctx.provider,
        model_name=ctx.model_name,
    )
    for retry_target in retry_targets:
        retry_provider = retry_target.provider
        retry_model_name = retry_target.model_name
        try:
            yield prepared.emitter.emit(
                deps.retry.build_tool_call_retry_event(
                    from_provider=ctx.provider,
                    from_model=ctx.model_name,
                    to_provider=retry_provider,
                    to_model=retry_model_name,
                )
            )
            retry_model = deps.get_model(retry_provider, retry_model_name)
            retry_model_settings = deps.patch_model_settings(
                deps.config_service.get_model_settings(retry_provider, retry_model_name)
            )
            retry_capabilities = deps.config_service.get_model_capabilities(retry_provider, retry_model_name)
            retry_parser = deps.get_parser(retry_provider, retry_model_name, retry_capabilities)
            retry_input = prepared.multimodal_service.build_user_input(
                message=prepared.request.message,
                validated_images=prepared.validated_images,
                vision_enabled=prepared.vision_enabled,
            )
            retry_result_holder = {}
            async for payload in deps.run_agent_stream(
                agent=deps.agent_cls(
                    retry_model,
                    system_prompt=ctx.system_prompt,
                    tools=prepared.tools,
                ),
                user_input=retry_input,
                history=ctx.history,
                deps=ctx.deps,
                model_settings=retry_model_settings,
                parser=retry_parser,
                tool_event_queue=ctx.tool_event_queue,
                emitter=prepared.emitter,
                stream_state=ctx.stream_state,
                log_label="retry stream_iter",
                result_holder=retry_result_holder,
                usage_limits=ctx.usage_limits,
            ):
                yield payload
            retry_result = retry_result_holder.get("result")
            retry_finish_reason = getattr(getattr(retry_result, "response", None), "finish_reason", None)
            if prepared.tool_tracker.counts["started"] > 0 or retry_finish_reason != "tool_call":
                mismatch_resolved = True
            if mismatch_resolved:
                yield prepared.emitter.emit(
                    deps.retry.build_tool_call_retry_success_event(
                        provider=retry_provider,
                        model=retry_model_name,
                        started=prepared.tool_tracker.counts["started"],
                        finished=prepared.tool_tracker.counts["finished"],
                    )
                )
                break
        except Exception as retry_err:
            deps.logger.exception("Auto retry after tool_call mismatch failed")
            yield prepared.emitter.emit(
                deps.retry.build_tool_call_retry_failed_event(
                    provider=retry_provider,
                    model=retry_model_name,
                    error=str(retry_err),
                )
            )
    if not mismatch_resolved:
        tool_msg = deps.retry.build_tool_call_mismatch_message()
        ctx.stream_state.full_response += tool_msg
        yield prepared.emitter.emit(
            deps.retry.build_tool_call_mismatch_event(
                started=prepared.tool_tracker.counts["started"],
                finished=prepared.tool_tracker.counts["finished"],
            )
        )
        yield prepared.emitter.emit({"content": tool_msg})


async def _prepare_runtime_dependencies(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    emitter: StreamEventEmitter,
    tool_tracker: Any,
    multimodal_service: Any,
    validated_images: List[str],
    request: Any,
    deps: StreamRunnerDeps,
) -> AsyncIterator[PreparedRuntime | str]:
    prompt_prep: PromptPreparation | None = None
    async for step in _prepare_prompt_runtime(
        ctx=ctx,
        emitter=emitter,
        request=request,
        deps=deps,
    ):
        if isinstance(step, PromptPreparation):
            prompt_prep = step
        else:
            yield step
    if prompt_prep is None:
        return

    if getattr(request, "requested_action", None):
        selected_skill = prompt_prep.selected_skill_spec
        if selected_skill is None:
            blocked_payload = {
                "event": "skill.action.result",
                "status": "blocked",
                "lifecycle_phase": "preflight",
                "lifecycle_status": "preflight_blocked",
                "skill_name": None,
                "skill_version": None,
                "action_id": request.requested_action,
                "accepted": False,
                "approval_required": False,
                "approval_policy": None,
                "mapped_tool": None,
                "execution_mode": "tool_only",
                "request_id": None,
                "validation_errors": ["No skill selected for requested action"],
                "missing_requirements": [],
            }
            yield emitter.emit(blocked_payload)
            yield emitter.emit({"content": f"[Action Preflight] `{request.requested_action}` is blocked: no skill selected. Yue will only continue through approved platform tools, not a skill-owned runner."})
            return

        action_request_id = _resolve_requested_action_request_id(request)
        preflight_result = deps.prompt.skill_action_execution_service.preflight(
            RuntimeSkillActionExecutionRequest(
                request_id=action_request_id,
                invocation=RuntimeSkillActionInvocationRequest(
                    skill_name=selected_skill.name,
                    skill_version=selected_skill.version,
                    action_id=request.requested_action,
                    provider=ctx.provider,
                    model_name=ctx.model_name,
                    arguments=getattr(request, "requested_action_arguments", None) or {},
                    enabled_tools=prompt_prep.final_tools_list,
                )
            )
        )
        lifecycle_results = [preflight_result]
        approval_result = None
        ctx.deps = deps.build_agent_deps(ctx.agent_config)
        if (
            preflight_result.lifecycle_status == "preflight_approval_required"
            and getattr(request, "requested_action_approved", None) is not None
        ):
            approval_result = deps.prompt.skill_action_execution_service.build_approval_result(
                preflight_result=preflight_result,
                approval_request=RuntimeSkillActionApprovalRequest(
                    skill_name=selected_skill.name,
                    skill_version=selected_skill.version,
                    action_id=request.requested_action,
                    approved=bool(request.requested_action_approved),
                    approval_token=getattr(request, "requested_action_approval_token", None),
                    request_id=action_request_id,
                ),
            )
            lifecycle_results.append(approval_result)

        should_execute_tool = preflight_result.lifecycle_status == "preflight_ready" or (
            preflight_result.lifecycle_status == "preflight_approval_required"
            and approval_result is not None
            and approval_result.lifecycle_status == "approved"
        )
        tool_result_payload = None
        tool_error_payload = None

        if should_execute_tool:
            tool_args = _resolve_requested_action_tool_args(preflight_result, request)
            queued_result = deps.prompt.skill_action_execution_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="queued",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="queued",
                metadata={
                    "reason": "platform_tool_dispatch",
                    "mapped_tool": preflight_result.invocation.mapped_tool,
                    "approval_token": getattr(approval_result, "approval_token", None),
                    "tool_args": tool_args,
                },
            )
            running_result = deps.prompt.skill_action_execution_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="running",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="running",
                metadata={
                    "reason": "platform_tool_running",
                    "mapped_tool": preflight_result.invocation.mapped_tool,
                    "approval_token": getattr(approval_result, "approval_token", None),
                    "tool_args": tool_args,
                },
            )
            lifecycle_results.extend([queued_result, running_result])

            for lifecycle_result in lifecycle_results:
                for event_payload in lifecycle_result.event_payloads:
                    enveloped_event = emitter.event_payload(event_payload)
                    deps.chat_service.add_action_event(
                        ctx.chat_id,
                        enveloped_event,
                        assistant_turn_id=ctx.assistant_turn_id,
                        run_id=ctx.run_id,
                    )
                    yield deps.serialize_sse_payload(enveloped_event)

            try:
                tool_result_payload = await _invoke_requested_action_platform_tool(
                    ctx=ctx,
                    deps=deps,
                    tool_tracker=tool_tracker,
                    agent_id=request.agent_id,
                    mapped_tool=preflight_result.invocation.mapped_tool or "",
                    enabled_tools=prompt_prep.final_tools_list,
                    arguments=tool_args,
                )
                async for tool_payload in _drain_tool_event_queue(ctx=ctx, deps=deps):
                    yield tool_payload
                success_result = deps.prompt.skill_action_execution_service.build_transition_result(
                    invocation=preflight_result.invocation,
                    status="succeeded",
                    request_id=preflight_result.request_id,
                    lifecycle_phase="execution",
                    lifecycle_status="succeeded",
                    metadata={
                        "reason": "platform_tool_completed",
                        "mapped_tool": preflight_result.invocation.mapped_tool,
                        "tool_result": tool_result_payload,
                        "approval_token": getattr(approval_result, "approval_token", None),
                        "tool_args": tool_args,
                    },
                )
                lifecycle_results = [success_result]
            except Exception as tool_err:
                async for tool_payload in _drain_tool_event_queue(ctx=ctx, deps=deps):
                    yield tool_payload
                tool_error_payload = str(tool_err)
                failed_result = deps.prompt.skill_action_execution_service.build_transition_result(
                    invocation=preflight_result.invocation,
                    status="failed",
                    request_id=preflight_result.request_id,
                    lifecycle_phase="execution",
                    lifecycle_status="failed",
                    metadata={
                        "reason": "platform_tool_failed",
                        "mapped_tool": preflight_result.invocation.mapped_tool,
                        "tool_error": tool_error_payload,
                        "approval_token": getattr(approval_result, "approval_token", None),
                        "tool_args": tool_args,
                    },
                )
                lifecycle_results = [failed_result]
        else:
            lifecycle_results.extend(
                deps.prompt.skill_action_execution_service.build_stub_execution_results(
                    preflight_result=preflight_result,
                    approval_result=approval_result,
                )
            )
        for lifecycle_result in lifecycle_results:
            for event_payload in lifecycle_result.event_payloads:
                enveloped_event = emitter.event_payload(event_payload)
                deps.chat_service.add_action_event(
                    ctx.chat_id,
                    enveloped_event,
                    assistant_turn_id=ctx.assistant_turn_id,
                    run_id=ctx.run_id,
                )
                yield deps.serialize_sse_payload(enveloped_event)
        preflight_message = _build_requested_action_content(
            preflight_result,
            deps.prompt.action_preflight_message_builder,
        )
        ctx.stream_state.full_response += preflight_message
        yield emitter.emit({"content": preflight_message})
        if approval_result is not None:
            approval_message = deps.prompt.action_approval_message_builder(approval_result)
            ctx.stream_state.full_response += "\n" + approval_message
            yield emitter.emit({"content": approval_message})
        if len(lifecycle_results) > 1:
            execution_message = deps.prompt.action_execution_message_builder(lifecycle_results[-1])
            ctx.stream_state.full_response += "\n" + execution_message
            yield emitter.emit({"content": execution_message})
        elif lifecycle_results:
            execution_message = deps.prompt.action_execution_message_builder(lifecycle_results[-1])
            ctx.stream_state.full_response += "\n" + execution_message
            yield emitter.emit({"content": execution_message})
        if tool_result_payload is not None:
            tool_result_message = f"[Tool Result] `{preflight_result.invocation.mapped_tool}` returned:\n{tool_result_payload}"
            ctx.stream_state.full_response += "\n" + tool_result_message
            yield emitter.emit({"content": tool_result_message})
        if tool_error_payload is not None:
            tool_error_message = f"[Tool Error] `{preflight_result.invocation.mapped_tool}` failed:\n{tool_error_payload}"
            ctx.stream_state.full_response += "\n" + tool_error_message
            yield emitter.emit({"content": tool_error_message})
        return

    ctx.model_name, ollama_error = await deps.ensure_ollama_model_available(
        provider=ctx.provider,
        model_name=ctx.model_name,
        fetch_ollama_models=deps.fetch_ollama_models,
    )
    if ollama_error:
        yield emitter.emit(ollama_error)
        return

    tools = await deps.tool_registry.get_pydantic_ai_tools_for_agent(
        request.agent_id,
        ctx.provider,
        on_event=tool_tracker.on_tool_event,
        event_context=lambda: {
            "run_id": ctx.run_id,
            "assistant_turn_id": ctx.assistant_turn_id,
        },
        enabled_tools=prompt_prep.final_tools_list,
    )
    tool_names = deps.collect_tool_names(tools)

    model_capabilities = deps.config_service.get_model_capabilities(ctx.provider, ctx.model_name)
    vision_decision = multimodal_service.decide_vision(
        model_capabilities=model_capabilities,
        request_has_images=bool(validated_images),
        fallback_enabled=bool(ctx.feature_flags.get("multimodal_vision_fallback_enabled", False)),
    )
    supports_vision = bool(vision_decision["supports_vision"])
    vision_enabled = bool(vision_decision["vision_enabled"])
    fallback_mode = str(vision_decision["fallback_mode"])
    if fallback_mode == "reject":
        yield emitter.emit({
            "error": "当前模型不支持图片理解，请切换支持视觉的模型后重试。",
            "error_code": "MODEL_VISION_UNSUPPORTED",
            "supports_vision": supports_vision,
            "vision_enabled": vision_enabled,
        })
        return

    metrics.supports_reasoning = "reasoning" in model_capabilities
    metrics.reasoning_enabled, reasoning_disabled_reason_code = deps.resolve_reasoning_state(
        supports_reasoning=metrics.supports_reasoning,
        deep_thinking_enabled=bool(request.deep_thinking_enabled),
        reasoning_display_gated_enabled=ctx.reasoning_display_gated_enabled,
    )
    yield emitter.emit(
        deps.build_runtime_meta_payload(
            provider=ctx.provider,
            model_name=ctx.model_name,
            model_resolution=getattr(ctx, "model_resolution", None),
            tool_names=tool_names,
            chat_id=ctx.chat_id,
            agent_id=request.agent_id,
            run_id=ctx.run_id,
            assistant_turn_id=ctx.assistant_turn_id,
            turn_binding_enabled=ctx.turn_binding_enabled,
            supports_reasoning=metrics.supports_reasoning,
            deep_thinking_enabled=bool(request.deep_thinking_enabled),
            reasoning_enabled=metrics.reasoning_enabled,
            reasoning_disabled_reason_code=reasoning_disabled_reason_code,
            supports_vision=supports_vision,
            vision_enabled=vision_enabled,
            validated_images=validated_images,
            fallback_mode=fallback_mode,
        )
    )
    if request.deep_thinking_enabled and not metrics.reasoning_enabled and reasoning_disabled_reason_code:
        yield emitter.emit({
            "event": "reasoning_toggle_ignored",
            "reason_code": reasoning_disabled_reason_code,
        })

    ctx.system_prompt = deps.build_system_prompt(
        base_prompt=ctx.system_prompt,
        provider=ctx.provider,
        model_name=ctx.model_name,
        user_message=request.message,
        deep_thinking_enabled=metrics.reasoning_enabled,
    )

    try:
        model = deps.get_model(ctx.provider, ctx.model_name)
    except Exception as model_err:
        if deps.env_flag("PYTEST_CURRENT_TEST", False):
            model = object()
        else:
            raise model_err

    ctx.deps = deps.build_agent_deps(ctx.agent_config)
    ctx.model_settings = deps.patch_model_settings(
        deps.config_service.get_model_settings(ctx.provider, ctx.model_name)
    )
    tier = "default"
    if ctx.agent_config and getattr(ctx.agent_config, "tier", None):
        tier = ctx.agent_config.tier
    usage_policy = deps.config_service.get_usage_limits(tier)
    ctx.usage_limits = deps.usage_limits_cls(
        request_limit=usage_policy.get("request_limit"),
        tool_calls_limit=usage_policy.get("tool_calls_limit"),
    )
    ctx.parser = deps.get_parser(ctx.provider, ctx.model_name, model_capabilities)
    ctx.result = None

    yield PreparedRuntime(
        emitter=emitter,
        tool_tracker=tool_tracker,
        tools=tools,
        model=model,
        multimodal_service=multimodal_service,
        validated_images=validated_images,
        request=request,
        model_capabilities=model_capabilities,
        vision_enabled=vision_enabled,
    )


async def _execute_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    start_time = time.time()
    try:
        user_input = prepared.multimodal_service.build_user_input(
            message=prepared.request.message,
            validated_images=prepared.validated_images,
            vision_enabled=prepared.vision_enabled,
        )

        result_holder: Dict[str, Any] = {}
        async for payload in deps.run_agent_stream(
            agent=deps.agent_cls(
                prepared.model,
                system_prompt=ctx.system_prompt,
                tools=prepared.tools,
            ),
            user_input=user_input,
            history=ctx.history,
            deps=ctx.deps,
            model_settings=ctx.model_settings,
            parser=ctx.parser,
            tool_event_queue=ctx.tool_event_queue,
            emitter=prepared.emitter,
            stream_state=ctx.stream_state,
            log_label="stream_iter",
            result_holder=result_holder,
            usage_limits=ctx.usage_limits,
        ):
            yield payload
        ctx.result = result_holder.get("result")

    except UsageLimitExceeded as limit_err:
        deps.logger.warning("Usage limit exceeded for run %s: %s", ctx.chat_id, limit_err)
        limit_info = {"event": "run.limited", "reason": str(limit_err), "snapshot": {}}
        try:
            if ctx.result is not None and hasattr(ctx.result, "usage"):
                raw_usage = ctx.result.usage()
                if asyncio.iscoroutine(raw_usage):
                    raw_usage = await raw_usage
                limit_info["snapshot"] = raw_usage.model_dump() if hasattr(raw_usage, "model_dump") else str(raw_usage)
        except Exception:
            pass
        yield prepared.emitter.emit(limit_info)
        friendly_msg = f"\n\n> ⚠️ **[系统提示]** 已触达策略上限（{limit_err}）。为了您的账户安全和成本控制，本轮执行已自动停止。您可以根据已有信息继续，或尝试缩小问题范围。"
        ctx.stream_state.full_response += friendly_msg
        yield prepared.emitter.emit({"content": friendly_msg})

    except Exception as stream_err:
        err_str = str(stream_err)
        if "status_code: 502" in err_str and ctx.provider == "ollama":
            yield prepared.emitter.emit({"error": "Ollama 返回 502，请检查模型是否已拉取且服务正常运行"})
            return

        friendly_error = deps.handle_llm_exception(stream_err)
        if friendly_error != err_str:
            yield prepared.emitter.emit({"error": friendly_error})
            return

        if "does not support tools" in err_str or "Tool use is not supported" in err_str:
            deps.logger.info("Model %s does not support tools, falling back to pure chat.", ctx.model_name)
            ctx.parser = deps.get_parser(ctx.provider, ctx.model_name, prepared.model_capabilities)
            ctx.stream_state = StreamState()
            user_input = prepared.multimodal_service.build_user_input(
                message=prepared.request.message,
                validated_images=prepared.validated_images,
                vision_enabled=prepared.vision_enabled,
            )
            result_holder = {}
            async for payload in deps.run_agent_stream(
                agent=deps.agent_cls(prepared.model, system_prompt=ctx.system_prompt),
                user_input=user_input,
                history=ctx.history,
                deps=ctx.deps,
                model_settings=ctx.model_settings,
                parser=ctx.parser,
                tool_event_queue=ctx.tool_event_queue,
                emitter=prepared.emitter,
                stream_state=ctx.stream_state,
                log_label="stream_iter (fallback)",
                result_holder=result_holder,
            ):
                yield payload
            ctx.result = result_holder.get("result")
        else:
            raise stream_err

    total_end_time = time.time()
    metrics.total_duration = total_end_time - start_time
    if ctx.stream_state.first_token_time:
        metrics.ttft = ctx.stream_state.first_token_time - start_time
    if ctx.parser and ctx.parser.thought_start_time:
        if ctx.parser.thought_end_time:
            metrics.thought_duration = ctx.parser.thought_end_time - ctx.parser.thought_start_time
        else:
            metrics.thought_duration = time.time() - ctx.parser.thought_start_time
    if metrics.thought_duration is not None:
        yield prepared.emitter.emit({"thought_duration": metrics.thought_duration})
    if metrics.ttft is not None:
        yield prepared.emitter.emit({"ttft": metrics.ttft})
    yield prepared.emitter.emit({"total_duration": metrics.total_duration})


async def _postprocess_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    try:
        finish_reason_val = getattr(getattr(ctx.result, "response", None), "finish_reason", None)
        if not isinstance(finish_reason_val, str):
            finish_reason_val = None
        raw_usage = ctx.result.usage()
        if asyncio.iscoroutine(raw_usage):
            raw_usage = await raw_usage
        usage_stats = deps.calculate_usage(
            provider=ctx.provider,
            raw_usage=raw_usage,
            duration=metrics.total_duration,
            finish_reason=finish_reason_val,
        )
        metrics.prompt_tokens = usage_stats.prompt_tokens
        metrics.completion_tokens = usage_stats.completion_tokens
        metrics.total_tokens = usage_stats.total_tokens
        metrics.finish_reason = usage_stats.finish_reason
        yield prepared.emitter.emit(usage_stats.model_dump())

        continue_payload = deps.append_continue_message_if_needed(
            finish_reason=metrics.finish_reason,
            stream_state=ctx.stream_state,
        )
        if continue_payload:
            yield prepared.emitter.emit(continue_payload)
        elif deps.should_handle_tool_call_mismatch(
            finish_reason=metrics.finish_reason,
            tool_call_started_count=prepared.tool_tracker.counts["started"],
        ):
            async for payload in _handle_tool_call_mismatch_retry(
                ctx=ctx,
                prepared=prepared,
                deps=deps,
            ):
                yield payload
    except Exception as usage_err:
        deps.logger.error("Failed to get usage via adapter: %s", usage_err)

    citations = ctx.deps.get("citations") if isinstance(ctx.deps, dict) else None
    if isinstance(citations, list) and citations:
        yield prepared.emitter.emit({"citations": citations})
    require_citations = bool(getattr(ctx.agent_config, "require_citations", False)) if ctx.agent_config else False
    citation_payload = deps.append_citation_suffix_if_needed(
        citations=citations,
        require_citations=require_citations,
        format_citations_suffix=deps.format_citations_suffix,
        stream_state=ctx.stream_state,
    )
    if citation_payload:
        yield prepared.emitter.emit(citation_payload)


def _finalize_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    tool_tracker: Any,
    deps: StreamRunnerDeps,
) -> None:
    saved = deps.persist_assistant_message(
        chat_service=deps.chat_service,
        chat_id=ctx.chat_id,
        stream_state=ctx.stream_state,
        thought_duration=metrics.thought_duration,
        ttft=metrics.ttft,
        total_duration=metrics.total_duration,
        prompt_tokens=metrics.prompt_tokens,
        completion_tokens=metrics.completion_tokens,
        total_tokens=metrics.total_tokens,
        finish_reason=metrics.finish_reason,
        current_exception=metrics.current_exception,
        assistant_turn_id=ctx.assistant_turn_id,
        run_id=ctx.run_id,
        turn_binding_enabled=ctx.turn_binding_enabled,
        supports_reasoning=metrics.supports_reasoning,
        deep_thinking_enabled=bool(ctx.request.deep_thinking_enabled),
        reasoning_enabled=metrics.reasoning_enabled,
    )
    if saved:
        asyncio.create_task(
            deps.refine_title_once_fn(
                ctx.chat_id,
                provider_override=ctx.provider,
                model_override=ctx.model_name,
            )
        )
    if deps.env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
        deps.logger.info(
            "BACKLOG_CHAT_RESPONSE %s",
            deps.safe_json_log(
                deps.build_chat_response_log_payload(
                    chat_id=ctx.chat_id,
                    provider=ctx.provider,
                    model_name=ctx.model_name,
                    finish_reason=metrics.finish_reason or (
                        metrics.current_exception.__class__.__name__
                        if isinstance(metrics.current_exception, (GeneratorExit, asyncio.CancelledError))
                        else None
                    ),
                    prompt_tokens=metrics.prompt_tokens,
                    completion_tokens=metrics.completion_tokens,
                    total_tokens=metrics.total_tokens,
                    ttft=metrics.ttft,
                    total_duration=metrics.total_duration,
                    tool_call_started_count=tool_tracker.counts["started"],
                    tool_call_finished_count=tool_tracker.counts["finished"],
                    full_response=ctx.stream_state.full_response,
                    error=metrics.stream_error_message,
                )
            ),
        )


def build_chat_event_generator(
    *,
    chat_id: str,
    request: Any,
    history: List[Any],
    validated_images: List[str],
    multimodal_service: Any,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    async def event_generator() -> AsyncIterator[str]:
        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id=chat_id,
            request=request,
            history=history,
            validated_images=validated_images,
            deps=deps,
        )
        yield emitter.emit({"chat_id": ctx.chat_id})

        try:
            prepared: PreparedRuntime | None = None
            async for step in _prepare_runtime_dependencies(
                ctx=ctx,
                metrics=metrics,
                emitter=emitter,
                tool_tracker=tool_tracker,
                multimodal_service=multimodal_service,
                validated_images=validated_images,
                request=request,
                deps=deps,
            ):
                if isinstance(step, PreparedRuntime):
                    prepared = step
                else:
                    yield step
            if prepared is None:
                return

            async for payload in _execute_stream_run(
                ctx=ctx,
                metrics=metrics,
                prepared=prepared,
                deps=deps,
            ):
                yield payload

            async for payload in _postprocess_stream_run(
                ctx=ctx,
                metrics=metrics,
                prepared=prepared,
                deps=deps,
            ):
                yield payload

        except (Exception, GeneratorExit, asyncio.CancelledError) as e:
            metrics.current_exception = e
            if isinstance(e, (GeneratorExit, asyncio.CancelledError)):
                deps.logger.info("Chat stream cancelled by client")
                metrics.stream_error_message = e.__class__.__name__
            else:
                metrics.stream_error_message = str(e)
                deps.logger.exception("Chat error")
                yield emitter.emit({"error": deps.handle_llm_exception(e)})
        finally:
            _finalize_stream_run(
                ctx=ctx,
                metrics=metrics,
                tool_tracker=tool_tracker,
                deps=deps,
            )

    return event_generator()
