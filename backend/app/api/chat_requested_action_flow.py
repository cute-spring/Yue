from typing import Any, AsyncIterator

from app.api.chat_requested_action_adapter import (
    build_requested_action_blocked_message,
    build_requested_action_blocked_payload,
    build_requested_action_messages,
    build_requested_action_transition_metadata,
    build_requested_action_runtime_contract_metadata as _runtime_contract_metadata,
    should_execute_requested_action_tool,
)
from app.api.chat_requested_action_events import persist_action_lifecycle_events
from app.api.chat_requested_action_tools import (
    drain_tool_event_queue,
    invoke_requested_action_platform_tool,
    resolve_requested_action_request_id,
    resolve_requested_action_tool_args,
)
from app.services.skills.models import (
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionInvocationRequest,
)


def _build_requested_action_content(preflight_result: Any, message_builder: Any) -> str:
    return message_builder(preflight_result)

async def run_requested_action_flow(
    *,
    ctx: Any,
    emitter: Any,
    tool_tracker: Any,
    request: Any,
    prompt_prep: Any,
    deps: Any,
) -> AsyncIterator[str]:
    selected_skill = prompt_prep.selected_skill_spec
    if selected_skill is None:
        blocked_payload = build_requested_action_blocked_payload(action_id=request.requested_action)
        yield emitter.emit(blocked_payload)
        yield emitter.emit({"content": build_requested_action_blocked_message(action_id=request.requested_action)})
        return

    action_request_id = resolve_requested_action_request_id(request)
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

    should_execute_tool = should_execute_requested_action_tool(
        preflight_result=preflight_result,
        approval_result=approval_result,
    )
    tool_result_payload = None
    tool_error_payload = None

    if should_execute_tool:
        tool_args = resolve_requested_action_tool_args(preflight_result, request)
        queued_result = deps.prompt.skill_action_execution_service.build_transition_result(
            invocation=preflight_result.invocation,
            status="queued",
            request_id=preflight_result.request_id,
            lifecycle_phase="execution",
            lifecycle_status="queued",
            metadata=build_requested_action_transition_metadata(
                preflight_result=preflight_result,
                approval_result=approval_result,
                reason="platform_tool_dispatch",
                tool_args=tool_args,
            ),
        )
        running_result = deps.prompt.skill_action_execution_service.build_transition_result(
            invocation=preflight_result.invocation,
            status="running",
            request_id=preflight_result.request_id,
            lifecycle_phase="execution",
            lifecycle_status="running",
            metadata=build_requested_action_transition_metadata(
                preflight_result=preflight_result,
                approval_result=approval_result,
                reason="platform_tool_running",
                tool_args=tool_args,
            ),
        )
        lifecycle_results.extend([queued_result, running_result])

        for payload in persist_action_lifecycle_events(
            lifecycle_results=lifecycle_results,
            ctx=ctx,
            emitter=emitter,
            deps=deps,
        ):
            yield payload

        try:
            tool_result_payload = await invoke_requested_action_platform_tool(
                ctx=ctx,
                deps=deps,
                tool_tracker=tool_tracker,
                agent_id=request.agent_id,
                mapped_tool=preflight_result.invocation.mapped_tool or "",
                enabled_tools=prompt_prep.final_tools_list,
                arguments=tool_args,
            )
            async for tool_payload in drain_tool_event_queue(ctx=ctx, deps=deps):
                yield tool_payload
            success_result = deps.prompt.skill_action_execution_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="succeeded",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="succeeded",
                metadata=build_requested_action_transition_metadata(
                    preflight_result=preflight_result,
                    approval_result=approval_result,
                    reason="platform_tool_completed",
                    tool_args=tool_args,
                    extra_metadata={"tool_result": tool_result_payload},
                ),
            )
            lifecycle_results = [success_result]
        except Exception as tool_err:
            async for tool_payload in drain_tool_event_queue(ctx=ctx, deps=deps):
                yield tool_payload
            tool_error_payload = str(tool_err)
            failed_result = deps.prompt.skill_action_execution_service.build_transition_result(
                invocation=preflight_result.invocation,
                status="failed",
                request_id=preflight_result.request_id,
                lifecycle_phase="execution",
                lifecycle_status="failed",
                metadata=build_requested_action_transition_metadata(
                    preflight_result=preflight_result,
                    approval_result=approval_result,
                    reason="platform_tool_failed",
                    tool_args=tool_args,
                    extra_metadata={"tool_error": tool_error_payload},
                ),
            )
            lifecycle_results = [failed_result]
    else:
        lifecycle_results.extend(
            deps.prompt.skill_action_execution_service.build_stub_execution_results(
                preflight_result=preflight_result,
                approval_result=approval_result,
            )
        )

    for payload in persist_action_lifecycle_events(
        lifecycle_results=lifecycle_results,
        ctx=ctx,
        emitter=emitter,
        deps=deps,
    ):
        yield payload

    messages = build_requested_action_messages(
        preflight_result=preflight_result,
        approval_result=approval_result,
        lifecycle_results=lifecycle_results,
        prompt_deps=deps.prompt,
        tool_result_payload=tool_result_payload,
        tool_error_payload=tool_error_payload,
    )
    for index, message in enumerate(messages):
        if index == 0:
            ctx.stream_state.full_response += message
        else:
            ctx.stream_state.full_response += "\n" + message
        yield emitter.emit({"content": message})
