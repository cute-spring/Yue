from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.api.chat_trace_schemas import RequestAttachmentItem, RequestHistoryItem, RequestSnapshotRecord


def summarize_history_item(item: Any) -> RequestHistoryItem:
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


def build_request_snapshot_record(
    *,
    ctx: Any,
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
        message_history=[summarize_history_item(item) for item in (ctx.history or [])],
        attachments=attachments,
        tool_context={"enabled_tools": list(final_tools_list or [])},
        skill_context=skill_context,
        runtime_flags={
            "event_v2_enabled": bool(ctx.event_v2_enabled),
            "turn_binding_enabled": bool(ctx.turn_binding_enabled),
            "reasoning_display_gated_enabled": bool(ctx.reasoning_display_gated_enabled),
            "summary_injected": bool(getattr(prompt_result, "summary_injected", False)),
            "scope_summary_injected": bool(getattr(prompt_result, "scope_summary_injected", False)),
            "workspace_id": getattr(request, "workspace_id", None),
            "workspace_source_mode": getattr(request, "workspace_source_mode", None) or "all_ready",
            "selected_workspace_source_ids": list(getattr(request, "selected_workspace_source_ids", None) or []),
            "grounding_mode": getattr(request, "grounding_mode", None) or "normal",
            "workspace_source_context": getattr(ctx, "workspace_source_context", None),
        },
        redaction={},
        truncation={},
    )


def build_workspace_grounding_event(
    ctx: Any,
    *,
    final_tools_list: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    context = getattr(ctx, "workspace_source_context", None)
    if not isinstance(context, dict):
        return None

    def summarize_source(source: Any) -> Dict[str, Any]:
        if not isinstance(source, dict):
            return {}
        return {
            "id": source.get("id"),
            "display_name": source.get("display_name"),
            "source_type": source.get("source_type"),
            "status": source.get("status"),
            "citation_capable": bool(source.get("citation_capable")),
            "available_tools": source.get("available_tools") if isinstance(source.get("available_tools"), list) else [],
        }

    eligible_sources = [item for item in (summarize_source(source) for source in context.get("eligible_sources", [])) if item.get("id")]
    unavailable_sources = [item for item in (summarize_source(source) for source in context.get("unavailable_sources", [])) if item.get("id")]
    enabled_tool_count = len(list(final_tools_list or []))
    tooling_warning = None
    if (context.get("grounding_mode") or "normal") == "require_sources" and eligible_sources and enabled_tool_count == 0:
        tooling_warning = "Citation-required mode is active, but no compatible retrieval tools were enabled for this turn."
    return {
        "workspace_grounding": {
            "workspace_id": context.get("workspace_id"),
            "workspace_name": context.get("workspace_name"),
            "workspace_source_mode": context.get("workspace_source_mode") or "all_ready",
            "grounding_mode": context.get("grounding_mode") or "normal",
            "selected_source_ids": context.get("selected_source_ids") if isinstance(context.get("selected_source_ids"), list) else None,
            "eligible_sources": eligible_sources,
            "unavailable_sources": unavailable_sources,
            "enabled_tool_count": enabled_tool_count,
            "tooling_warning": tooling_warning,
        }
    }


def persist_request_snapshot(*, ctx: Any, deps: Any, snapshot: RequestSnapshotRecord) -> None:
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
