import uuid
from typing import Any, AsyncIterator, Dict, List

from app.api.chat_stream_types import StreamRunContext, StreamRunMetrics
from app.api.chat_stream_runner_actions import run_requested_action_flow
from app.api.chat_stream_runner_helpers import (
    build_authoritative_session_context_user_hint as _build_authoritative_session_context_user_hint,
    continuation_content_type_for_request as _continuation_content_type_for_request,
    continuation_root_for_request as _continuation_root_for_request,
    safe_int as _safe_int,
    safe_role_lookup as _safe_role_lookup,
    safe_text as _safe_text,
)
from app.api.chat_stream_runner_snapshot import (
    build_request_snapshot_record as _build_request_snapshot_record,
    build_session_context_event as _build_session_context_event,
    build_workspace_note_event as _build_workspace_note_event,
    build_workspace_memory_event as _build_workspace_memory_event,
    build_workspace_grounding_event as _build_workspace_grounding_event,
    persist_request_snapshot as _persist_request_snapshot,
)
from app.api.chat_stream_runner_types import (
    PreparedRuntime,
    PromptPreparation,
    StreamRunnerDeps,
)
from app.services.chat_streaming import StreamEventEmitter
from app.services.llm.routing import RoutingContext, resolve_runtime_model
from app.services.memory.session_context_host import yue_session_context_service
from app.services.notebook_service import notebook_service
from app.services.workspace_service import workspace_service


def create_stream_runtime(
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
        chart_artifact_sink=ctx.stream_state.chart_artifacts,
        logger=deps.logger,
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


async def prepare_prompt_runtime(
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
    session_context_block = None
    workspace_note_context_block = None
    workspace_context_block = None
    effective_request_message = request.message
    if bool(ctx.feature_flags.get("session_context_enabled", False)):
        try:
            chat_session = deps.chat_service.get_chat(ctx.chat_id)
            if chat_session is not None:
                session_context_result = yue_session_context_service.build_prompt_context(
                    session_id=ctx.chat_id,
                    current_input=request.message,
                    chat_session=chat_session,
                    tool_calls=deps.chat_service.get_tool_calls(ctx.chat_id),
                )
                if session_context_result is not None:
                    session_context_block = session_context_result.prompt_context.rendered_prompt_block
                    ctx.session_context_used = session_context_result.inspection
                    authoritative_hint = _build_authoritative_session_context_user_hint(
                        session_context_result.plan
                    )
                    if authoritative_hint:
                        effective_request_message = f"{authoritative_hint}\n\nUser request:\n{request.message}"
        except Exception:
            deps.logger.exception("Session context integration failed; continuing without injected context")

    note_recall_enabled = getattr(request, "note_recall_enabled", None)
    if note_recall_enabled is not False:
        try:
            workspace_note_context = notebook_service.build_prompt_context(
                getattr(request, "workspace_id", None),
                current_query=request.message,
            )
            if workspace_note_context is not None:
                workspace_note_context_block = workspace_note_context.prompt_block
                ctx.workspace_note_context = {
                    "workspace_id": workspace_note_context.workspace_id,
                    "loaded_note_ids": list(workspace_note_context.loaded_note_ids or []),
                    "loaded_notes": [item.model_dump(mode="json") for item in workspace_note_context.loaded_notes],
                }
        except Exception:
            deps.logger.exception("Workspace note context integration failed; continuing without injected workspace notes")

    try:
        workspace_context = workspace_service.build_prompt_context(
            getattr(request, "workspace_id", None),
            workspace_source_mode=getattr(request, "workspace_source_mode", None),
            selected_source_ids=getattr(request, "selected_workspace_source_ids", None),
            grounding_mode=getattr(request, "grounding_mode", None),
            current_query=request.message,
            current_chat_id=ctx.chat_id,
        )
        if workspace_context is not None:
            workspace_context_block = workspace_context.prompt_block
            ctx.workspace_source_context = workspace_context.model_dump(mode="json")
            ctx.workspace_memory_context = {
                "workspace_id": workspace_context.workspace_id,
                "loaded_memory_ids": list(workspace_context.loaded_memory_ids or []),
                "loaded_memories": [item.model_dump(mode="json") for item in workspace_context.loaded_memories],
            }
    except Exception:
        deps.logger.exception("Workspace source context integration failed; continuing without injected workspace context")

    combined_context_blocks = [
        block for block in [session_context_block, workspace_note_context_block, workspace_context_block] if block
    ]
    combined_context_block = "\n\n".join(combined_context_blocks) if combined_context_blocks else None

    prompt_result = deps.prompt.assemble_runtime_prompt(
        agent_config=ctx.agent_config,
        request_system_prompt=ctx.system_prompt,
        request_message=effective_request_message,
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
        session_context_block=combined_context_block,
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
            session_context_block=combined_context_block,
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

    workspace_grounding_event = _build_workspace_grounding_event(
        ctx,
        final_tools_list=list(prompt_result.final_tools_list or []),
    )
    if workspace_grounding_event:
        yield emitter.emit(workspace_grounding_event)
    session_context_event = _build_session_context_event(ctx)
    if session_context_event:
        yield emitter.emit(session_context_event)
    workspace_memory_event = _build_workspace_memory_event(ctx)
    if workspace_memory_event:
        yield emitter.emit(workspace_memory_event)
    workspace_note_event = _build_workspace_note_event(ctx)
    if workspace_note_event:
        yield emitter.emit(workspace_note_event)

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


async def prepare_runtime_dependencies(
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
    async for step in prepare_prompt_runtime(
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
        async for payload in run_requested_action_flow(
            ctx=ctx,
            prompt_prep=prompt_prep,
            emitter=emitter,
            tool_tracker=tool_tracker,
            request=request,
            validated_images=validated_images,
            multimodal_service=multimodal_service,
            deps=deps,
        ):
            yield payload
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
            continuation_of=_safe_text(getattr(request, "continuation_of", None)),
            continuation_root_id=_continuation_root_for_request(request),
            continuation_status="resuming"
            if _safe_text(getattr(request, "continuation_of", None))
            else None,
            content_type=_continuation_content_type_for_request(request),
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
        continuation_context={
            "continuation_of": _safe_text(getattr(request, "continuation_of", None)),
            "content_type": _continuation_content_type_for_request(request),
            "tail": _safe_text(getattr(request, "continuation_tail", None)),
        },
    )

    try:
        model = deps.get_model(ctx.provider, ctx.model_name)
    except Exception as model_err:
        if deps.env_flag("PYTEST_CURRENT_TEST", False):
            model = object()
        else:
            raise model_err

    ctx.deps = deps.build_agent_deps(ctx.agent_config)

    async def emit_chart_artifact_payload(payload: Dict[str, Any]) -> None:
        await tool_tracker.on_tool_event(
            {
                "event": "artifact.chart.created",
                "payload": payload,
                "run_id": ctx.run_id,
                "assistant_turn_id": ctx.assistant_turn_id,
            }
        )

    if isinstance(ctx.deps, dict):
        ctx.deps["emit_chart_artifact"] = emit_chart_artifact_payload
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
        authorized_tools=list(prompt_prep.final_tools_list),
    )
