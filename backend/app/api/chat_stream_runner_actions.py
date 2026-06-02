import time
import uuid
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict, List, Optional

from app.services.jira import extract_jira_action_preview, find_agent_jira_skill_ref, resolve_repo_jira_skill_runtime
from app.services.skills.models import (
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionInvocationRequest,
)

from .chat_stream_runner_helpers import resolve_requested_action_request_id, split_skill_ref


def build_requested_action_content(preflight_result: Any, message_builder: Any) -> str:
    return message_builder(preflight_result)


async def drain_tool_event_queue(*, ctx: Any, deps: Any) -> AsyncIterator[str]:
    while not ctx.tool_event_queue.empty():
        payload = await ctx.tool_event_queue.get()
        yield deps.serialize_sse_payload(payload)


async def invoke_requested_action_platform_tool(
    *,
    ctx: Any,
    deps: Any,
    tool_tracker: Any,
    agent_id: Optional[str],
    mapped_tool: str,
    enabled_tools: List[str],
    arguments: Dict[str, Any],
) -> str:
    tools = await deps.tool_registry.get_tools_for_agent(agent_id, enabled_tools=enabled_tools)
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
    await tool_tracker.on_tool_event({
        "event": "tool.call.started",
        "call_id": call_id,
        "tool_name": raw_name,
        "args": validated_args,
        "run_id": ctx.run_id,
        "assistant_turn_id": ctx.assistant_turn_id,
    })
    start_time = time.time()
    try:
        result = await selected_tool.execute(tool_ctx, validated_args)
    except Exception as tool_err:
        duration_ms = (time.time() - start_time) * 1000
        await tool_tracker.on_tool_event({
            "event": "tool.call.finished",
            "call_id": call_id,
            "tool_name": raw_name,
            "error": str(tool_err),
            "duration_ms": duration_ms,
            "run_id": ctx.run_id,
            "assistant_turn_id": ctx.assistant_turn_id,
        })
        raise
    duration_ms = (time.time() - start_time) * 1000
    await tool_tracker.on_tool_event({
        "event": "tool.call.finished",
        "call_id": call_id,
        "tool_name": raw_name,
        "result": result,
        "duration_ms": duration_ms,
        "run_id": ctx.run_id,
        "assistant_turn_id": ctx.assistant_turn_id,
    })
    return result


async def emit_jira_action_preview_events(*, ctx: Any, prepared: Any, deps: Any) -> AsyncIterator[str]:
    if getattr(ctx.request, "requested_action", None):
        return
    preview = extract_jira_action_preview(ctx.stream_state.full_response)
    if preview is None:
        return
    skill_ref = find_agent_jira_skill_ref(ctx.agent_config)
    if not skill_ref:
        return

    skill_name, skill_version = split_skill_ref(skill_ref)
    action_service = resolve_requested_action_service(
        skill_ref=skill_ref,
        skill_registry=deps.prompt.skill_registry,
        default_action_service=deps.prompt.skill_action_execution_service,
        provider=ctx.provider,
        model_name=ctx.model_name,
    )
    preflight_result = action_service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id=ctx.request_id,
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name=skill_name,
                skill_version=skill_version,
                action_id=preview.action_id,
                provider=ctx.provider,
                model_name=ctx.model_name,
                arguments=preview.arguments,
                enabled_tools=prepared.authorized_tools,
            ),
        )
    )
    lifecycle_results = [preflight_result]
    lifecycle_results.extend(action_service.build_stub_execution_results(preflight_result=preflight_result))
    for lifecycle_result in lifecycle_results:
        for event_payload in lifecycle_result.event_payloads:
            metadata = event_payload.get("metadata") if isinstance(event_payload.get("metadata"), dict) else {}
            if preview.reason:
                event_payload = {**event_payload, "metadata": {**metadata, "preview_reason": preview.reason}}
            enveloped_event = prepared.emitter.event_payload(event_payload)
            deps.chat_service.add_action_event(ctx.chat_id, enveloped_event, assistant_turn_id=ctx.assistant_turn_id, run_id=ctx.run_id)
            yield deps.serialize_sse_payload(enveloped_event)


def resolve_requested_action_tool_args(preflight_result: Any, request: Any) -> Dict[str, Any]:
    return ((preflight_result.metadata or {}).get("validated_arguments") or getattr(request, "requested_action_arguments", None) or {})


def resolve_requested_action_skill_fallback(
    *,
    requested_skill: Any,
    skill_registry: Any,
    provider: Optional[str],
    model_name: Optional[str],
) -> Any:
    if not isinstance(requested_skill, str) or not requested_skill.strip():
        return None
    skill_name, skill_version = split_skill_ref(requested_skill.strip())
    get_full_skill = getattr(skill_registry, "get_full_skill", None)
    if callable(get_full_skill):
        resolved = get_full_skill(skill_name, skill_version, provider=provider, model_name=model_name)
        if resolved is not None:
            return resolved
    get_skill = getattr(skill_registry, "get_skill", None)
    if callable(get_skill):
        resolved = get_skill(skill_name, skill_version)
        if resolved is not None:
            return resolved
    resolved, _service = resolve_repo_jira_skill_runtime(requested_skill.strip(), provider=provider, model_name=model_name)
    return resolved


def resolve_requested_action_service(
    *,
    skill_ref: str,
    skill_registry: Any,
    default_action_service: Any,
    provider: Optional[str],
    model_name: Optional[str],
) -> Any:
    skill_name, skill_version = split_skill_ref(skill_ref)
    get_action_descriptors = getattr(skill_registry, "get_action_descriptors", None)
    if callable(get_action_descriptors):
        descriptors = get_action_descriptors(skill_name, skill_version, provider=provider, model_name=model_name)
        if descriptors:
          return default_action_service
    _skill, fallback_service = resolve_repo_jira_skill_runtime(skill_ref, provider=provider, model_name=model_name)
    return fallback_service or default_action_service


async def run_requested_action_flow(
    *,
    ctx: Any,
    prompt_prep: Any,
    emitter: Any,
    tool_tracker: Any,
    request: Any,
    validated_images: List[str],
    multimodal_service: Any,
    deps: Any,
) -> AsyncIterator[str]:
    selected_skill = prompt_prep.selected_skill_spec
    if selected_skill is None:
        selected_skill = resolve_requested_action_skill_fallback(
            requested_skill=getattr(request, "requested_skill", None),
            skill_registry=deps.prompt.skill_registry,
            provider=ctx.provider,
            model_name=ctx.model_name,
        )
    action_service = deps.prompt.skill_action_execution_service
    requested_skill_ref = getattr(request, "requested_skill", None)
    if isinstance(requested_skill_ref, str) and requested_skill_ref.strip():
        action_service = resolve_requested_action_service(
            skill_ref=requested_skill_ref.strip(),
            skill_registry=deps.prompt.skill_registry,
            default_action_service=deps.prompt.skill_action_execution_service,
            provider=ctx.provider,
            model_name=ctx.model_name,
        )
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

    action_request_id = resolve_requested_action_request_id(request)
    preflight_result = action_service.preflight(
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
    if preflight_result.lifecycle_status == "preflight_approval_required" and getattr(request, "requested_action_approved", None) is not None:
        approval_result = action_service.build_approval_result(
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
        tool_args = resolve_requested_action_tool_args(preflight_result, request)
        queued_result = action_service.build_transition_result(
            invocation=preflight_result.invocation,
            status="queued",
            request_id=preflight_result.request_id,
            lifecycle_phase="execution",
            lifecycle_status="queued",
            metadata={"reason": "platform_tool_dispatch", "mapped_tool": preflight_result.invocation.mapped_tool, "approval_token": getattr(approval_result, "approval_token", None), "tool_args": tool_args},
        )
        running_result = action_service.build_transition_result(
            invocation=preflight_result.invocation,
            status="running",
            request_id=preflight_result.request_id,
            lifecycle_phase="execution",
            lifecycle_status="running",
            metadata={"reason": "platform_tool_running", "mapped_tool": preflight_result.invocation.mapped_tool, "approval_token": getattr(approval_result, "approval_token", None), "tool_args": tool_args},
        )
        lifecycle_results.extend([queued_result, running_result])

        for lifecycle_result in lifecycle_results:
            for event_payload in lifecycle_result.event_payloads:
                enveloped_event = emitter.event_payload(event_payload)
                deps.chat_service.add_action_event(ctx.chat_id, enveloped_event, assistant_turn_id=ctx.assistant_turn_id, run_id=ctx.run_id)
                yield deps.serialize_sse_payload(enveloped_event)
        try:
            tool_result_payload = await invoke_requested_action_platform_tool(
                ctx=ctx,
                deps=deps,
                tool_tracker=tool_tracker,
                agent_id=request.agent_id,
                mapped_tool=preflight_result.invocation.mapped_tool or "",
                enabled_tools=[preflight_result.invocation.mapped_tool or ""],
                arguments=tool_args,
            )
            async for tool_payload in drain_tool_event_queue(ctx=ctx, deps=deps):
                yield tool_payload
            success_result = action_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="succeeded",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="succeeded",
                metadata={"reason": "platform_tool_completed", "mapped_tool": preflight_result.invocation.mapped_tool, "tool_result": tool_result_payload, "approval_token": getattr(approval_result, "approval_token", None), "tool_args": tool_args},
            )
            lifecycle_results = [success_result]
        except Exception as tool_err:
            async for tool_payload in drain_tool_event_queue(ctx=ctx, deps=deps):
                yield tool_payload
            tool_error_payload = str(tool_err)
            failed_result = action_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="failed",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="failed",
                metadata={"reason": "platform_tool_failed", "mapped_tool": preflight_result.invocation.mapped_tool, "tool_error": tool_error_payload, "approval_token": getattr(approval_result, "approval_token", None), "tool_args": tool_args},
            )
            lifecycle_results = [failed_result]
    else:
        lifecycle_results.extend(action_service.build_stub_execution_results(preflight_result=preflight_result, approval_result=approval_result))

    for lifecycle_result in lifecycle_results:
        for event_payload in lifecycle_result.event_payloads:
            enveloped_event = emitter.event_payload(event_payload)
            deps.chat_service.add_action_event(ctx.chat_id, enveloped_event, assistant_turn_id=ctx.assistant_turn_id, run_id=ctx.run_id)
            yield deps.serialize_sse_payload(enveloped_event)

    preflight_message = build_requested_action_content(preflight_result, deps.prompt.action_preflight_message_builder)
    ctx.stream_state.full_response += preflight_message
    yield emitter.emit({"content": preflight_message})
    if approval_result is not None:
        approval_message = deps.prompt.action_approval_message_builder(approval_result)
        ctx.stream_state.full_response += "\n" + approval_message
        yield emitter.emit({"content": approval_message})
    if lifecycle_results:
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
