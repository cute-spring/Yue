import time
import uuid
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict, List


async def drain_tool_event_queue(*, ctx: Any, deps: Any) -> AsyncIterator[str]:
    while not ctx.tool_event_queue.empty():
        payload = await ctx.tool_event_queue.get()
        yield deps.serialize_sse_payload(payload)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _merge_browser_resolved_context_args(base_args: Dict[str, Any], preflight_metadata: Dict[str, Any]) -> Dict[str, Any]:
    if preflight_metadata.get("tool_family") != "agent_browser":
        return base_args

    continuity_resolution = _as_dict(preflight_metadata.get("browser_continuity_resolution"))
    if continuity_resolution.get("continuity_status") != "resolved":
        return base_args

    resolved_context = _as_dict(continuity_resolution.get("resolved_context"))
    merged_args = dict(base_args)
    for key in ("session_id", "tab_id", "element_ref"):
        value = resolved_context.get(key)
        if key not in merged_args and value not in (None, ""):
            merged_args[key] = value
    return merged_args


def resolve_requested_action_tool_args(preflight_result: Any, request: Any) -> Dict[str, Any]:
    preflight_metadata = _as_dict(getattr(preflight_result, "metadata", None))
    base_args = (
        (preflight_result.metadata or {}).get("validated_arguments")
        or getattr(request, "requested_action_arguments", None)
        or {}
    )
    if not isinstance(base_args, dict):
        return {}
    return _merge_browser_resolved_context_args(dict(base_args), preflight_metadata)


def resolve_requested_action_request_id(request: Any) -> str:
    approval_token = getattr(request, "requested_action_approval_token", None)
    if isinstance(approval_token, str) and approval_token:
        parts = approval_token.rsplit(":", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
    return uuid.uuid4().hex[:12]


async def invoke_requested_action_platform_tool(
    *,
    ctx: Any,
    deps: Any,
    tool_tracker: Any,
    agent_id: str | None,
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
