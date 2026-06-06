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
            "workspace_note_context": getattr(ctx, "workspace_note_context", None),
            "workspace_memory_context": getattr(ctx, "workspace_memory_context", None),
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


def build_workspace_memory_event(ctx: Any) -> Optional[Dict[str, Any]]:
    context = getattr(ctx, "workspace_memory_context", None)
    if not isinstance(context, dict):
        return None

    loaded_memories = context.get("loaded_memories")
    if not isinstance(loaded_memories, list):
        loaded_memories = []

    summarized = []
    for item in loaded_memories[:8]:
        if not isinstance(item, dict):
            continue
        summarized.append(
            {
                "id": item.get("id"),
                "memory_type": item.get("memory_type"),
                "title": item.get("title"),
                "content": item.get("content"),
                "source_session_id": item.get("source_session_id"),
                "source_message_id": item.get("source_message_id"),
            }
        )

    return {
        "workspace_memory": {
            "workspace_id": context.get("workspace_id"),
            "loaded_memory_ids": context.get("loaded_memory_ids") if isinstance(context.get("loaded_memory_ids"), list) else [],
            "loaded_memories": summarized,
            "loaded_memory_count": len(summarized),
        }
    }


def build_workspace_note_event(ctx: Any) -> Optional[Dict[str, Any]]:
    context = getattr(ctx, "workspace_note_context", None)
    if not isinstance(context, dict):
        return None

    loaded_notes = context.get("loaded_notes")
    if not isinstance(loaded_notes, list):
        loaded_notes = []

    summarized = []
    for item in loaded_notes[:5]:
        if not isinstance(item, dict):
            continue
        summarized.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "content": item.get("content"),
                "note_type": item.get("note_type"),
                "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                "source_session_id": item.get("source_session_id"),
                "source_message_id": item.get("source_message_id"),
            }
        )

    return {
        "workspace_notes": {
            "workspace_id": context.get("workspace_id"),
            "loaded_note_ids": context.get("loaded_note_ids") if isinstance(context.get("loaded_note_ids"), list) else [],
            "loaded_notes": summarized,
            "loaded_note_count": len(summarized),
        }
    }


def build_workspace_capture_suggestion_event(
    ctx: Any,
    *,
    response_content: Optional[str],
    citations: Optional[List[Any]] = None,
) -> Optional[Dict[str, Any]]:
    workspace_id = None
    workspace_note_context = getattr(ctx, "workspace_note_context", None)
    workspace_memory_context = getattr(ctx, "workspace_memory_context", None)
    if isinstance(workspace_note_context, dict):
        workspace_id = workspace_note_context.get("workspace_id") or workspace_id
    if isinstance(workspace_memory_context, dict):
        workspace_id = workspace_memory_context.get("workspace_id") or workspace_id
    if not workspace_id:
        return None

    compact = " ".join(str(response_content or "").split()).strip()
    if not compact:
        return None

    recalled_note_count = 0
    recalled_memory_count = 0
    if isinstance(workspace_note_context, dict):
        recalled_note_count = len(workspace_note_context.get("loaded_note_ids") or [])
    if isinstance(workspace_memory_context, dict):
        recalled_memory_count = len(workspace_memory_context.get("loaded_memory_ids") or [])
    citation_count = len(citations or [])
    bullet_count = compact.count("- ") + compact.count("* ")
    lower = compact.lower()
    looks_structured = bullet_count >= 2 or any(
        token in compact for token in ["总结", "结论", "建议", "下一步", "方案", "要点"]
    ) or any(
        token in lower for token in ["summary", "decision", "recommend", "next step", "plan"]
    )
    looks_durable = any(
        token in compact for token in ["偏好", "默认", "习惯", "约束", "规则", "决定", "采用", "记住", "结论"]
    ) or any(
        token in lower for token in ["preference", "default", "constraint", "rule", "decision", "remember"]
    )
    substantial = len(compact) >= 120 or citation_count > 0 or recalled_note_count > 0 or recalled_memory_count > 0 or looks_structured
    if not substantial:
        return None

    show_note_action = True
    show_memory_action = bool(looks_durable or citation_count > 0 or len(compact) >= 220)
    if looks_durable:
        reason = "This reply looks like a reusable preference, rule, or decision worth keeping."
    elif citation_count > 0:
        reason = "This grounded answer has source support and may be useful to reuse later."
    else:
        reason = (
            "This summary looks worth saving as reusable workspace context."
            if ("summary" in lower or any(token in compact for token in ["总结", "结论", "要点"]))
            else "This substantial answer may be worth capturing for future workspace recall."
        )

    return {
        "workspace_capture_suggestion": {
            "workspace_id": workspace_id,
            "show_note_action": show_note_action,
            "show_memory_action": show_memory_action,
            "reason": reason,
            "source": "backend",
            "citation_count": citation_count,
            "recalled_note_count": recalled_note_count,
            "recalled_memory_count": recalled_memory_count,
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
