from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Sequence

from midterm_memory import (
    ChunkBuilder,
    ContextEvent,
    ContextResolutionConfig,
    ContextRetriever,
    ExportedPromptContext,
    HostEventAdapter,
    SessionContextManager,
    SessionRetrievalBoundaryPolicy,
    SQLiteFTSIndex,
    default_prompt_export_sections,
    normalize_context_event_type,
    validate_ordered_context_events,
)


logger = logging.getLogger(__name__)

_DEFAULT_RECENT_WINDOW_TOKEN_BUDGET = 800
_DEFAULT_RETRIEVAL_TOKEN_BUDGET = 300
_DEFAULT_TOP_K = 5
_DEFAULT_MEMORY_DB_FILENAME = "session_context_memory.db"


def _safe_positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _recent_window_token_budget() -> int:
    return _safe_positive_int_env(
        "YUE_SESSION_CONTEXT_RECENT_WINDOW_TOKEN_BUDGET",
        _DEFAULT_RECENT_WINDOW_TOKEN_BUDGET,
    )


def _retrieval_token_budget() -> int:
    return _safe_positive_int_env(
        "YUE_SESSION_CONTEXT_RETRIEVAL_TOKEN_BUDGET",
        _DEFAULT_RETRIEVAL_TOKEN_BUDGET,
    )


def _session_context_top_k() -> int:
    return _safe_positive_int_env(
        "YUE_SESSION_CONTEXT_TOP_K",
        _DEFAULT_TOP_K,
    )


def _session_context_db_path() -> str:
    configured = _safe_text(os.getenv("YUE_SESSION_CONTEXT_DB_PATH"))
    if configured:
        path = Path(os.path.expanduser(configured))
    else:
        data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
        path = data_dir / _DEFAULT_MEMORY_DB_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def _safe_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    return datetime.min


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _serialize_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def _message_sort_key(message: Any) -> tuple[datetime, str, str]:
    return (
        _safe_datetime(getattr(message, "timestamp", None)),
        _safe_text(getattr(message, "assistant_turn_id", None)),
        _safe_text(getattr(message, "role", None)),
    )


def _tool_sort_key(tool_call: Any) -> tuple[datetime, datetime, str]:
    return (
        _safe_datetime(
            getattr(tool_call, "started_ts", None)
            or getattr(tool_call, "created_at", None)
            or getattr(tool_call, "finished_ts", None)
        ),
        _safe_datetime(getattr(tool_call, "finished_ts", None) or getattr(tool_call, "finished_at", None)),
        _safe_text(getattr(tool_call, "call_id", None)),
    )


def _timeline_sort_key(event: ContextEvent) -> tuple[int, datetime, int, str]:
    event_priority = {
        "user_message": 0,
        "tool_call": 1,
        "tool_result": 2,
        "assistant_message": 3,
    }
    return (
        event.turn_id,
        _safe_datetime(event.created_at),
        event_priority.get(event.event_type, 9),
        event.event_id,
    )


def _is_message_record(record: Any) -> bool:
    return hasattr(record, "role") and hasattr(record, "content") and hasattr(record, "timestamp")


def _is_tool_call_record(record: Any) -> bool:
    return hasattr(record, "call_id") and hasattr(record, "tool_name") and hasattr(record, "status")


def _build_tool_call_content(tool_call: Any) -> str:
    tool_name = _safe_text(getattr(tool_call, "tool_name", None)) or "tool"
    args = getattr(tool_call, "args", None)
    if args in (None, {}, []):
        return tool_name
    return f"{tool_name} args={_serialize_json(args)}"


def _build_tool_result_content(tool_call: Any) -> str:
    tool_name = _safe_text(getattr(tool_call, "tool_name", None)) or "tool"
    error = _safe_text(getattr(tool_call, "error", None))
    if error:
        return f"{tool_name} error: {error}"
    result = getattr(tool_call, "result", None)
    result_text = _safe_text(result) if isinstance(result, str) else ""
    if result_text:
        return result_text
    if result not in (None, ""):
        return _serialize_json(result)
    status = _safe_text(getattr(tool_call, "status", None)) or "success"
    return f"{tool_name} status={status}"


@dataclass(frozen=True)
class YuePromptContextBridge:
    exported_context: ExportedPromptContext
    rendered_prompt_block: str
    selected_candidate_ids: list[str]
    source_chunk_ids: list[str]
    block_names: list[str]
    sections: list[str]


@dataclass(frozen=True)
class YueSessionContextResult:
    plan: Any
    prompt_context: YuePromptContextBridge
    inspection: dict[str, Any]


def build_session_context_inspection_payload(
    *,
    session_id: str,
    recent_events: Sequence[ContextEvent],
    plan: Any,
    prompt_context: YuePromptContextBridge,
) -> dict[str, Any]:
    telemetry = dict(getattr(plan, "telemetry", {}) or {})
    event_counts = {
        "user_message": 0,
        "assistant_message": 0,
        "tool_call": 0,
        "tool_result": 0,
    }
    recent_event_types: list[str] = []
    for event in recent_events:
        event_type = _safe_text(getattr(event, "event_type", None)) or "unknown"
        recent_event_types.append(event_type)
        if event_type in event_counts:
            event_counts[event_type] += 1

    return {
        "session_id": session_id,
        "host": "yue",
        "recent_event_count": len(recent_events),
        "recent_event_types": recent_event_types,
        "event_counts": event_counts,
        "action": telemetry.get("action"),
        "reason": telemetry.get("reason"),
        "should_retrieve": telemetry.get("should_retrieve"),
        "reference_signal_strength": telemetry.get("reference_signal_strength"),
        "matched_signals": list(telemetry.get("matched_signals", []) or []),
        "selected_candidate_ids": list(prompt_context.selected_candidate_ids),
        "source_chunk_ids": list(prompt_context.source_chunk_ids),
        "block_names": list(prompt_context.block_names),
        "sections": list(prompt_context.sections),
        "telemetry": telemetry,
    }


class YueHostEventAdapter(HostEventAdapter):
    def build_recent_events(
        self,
        *,
        session_id: str,
        host_records: Sequence[Any],
    ) -> list[ContextEvent]:
        message_records = sorted(
            [record for record in host_records if _is_message_record(record)],
            key=_message_sort_key,
        )
        tool_call_records = sorted(
            [record for record in host_records if _is_tool_call_record(record)],
            key=_tool_sort_key,
        )

        turn_id_by_assistant_turn_id: dict[str, int] = {}
        turn_id_by_message_key: dict[int, int] = {}
        message_events: list[ContextEvent] = []

        for index, message in enumerate(message_records, start=1):
            event_type = normalize_context_event_type(_safe_text(getattr(message, "role", None)) or "user")
            message_key = id(message)
            turn_id_by_message_key[message_key] = index

            assistant_turn_id = _safe_text(getattr(message, "assistant_turn_id", None))
            if assistant_turn_id:
                turn_id_by_assistant_turn_id[assistant_turn_id] = index

            message_events.append(
                ContextEvent(
                    event_id=f"message:{session_id}:{index}:{event_type}",
                    session_id=session_id,
                    turn_id=index,
                    event_type=event_type,
                    content=_safe_text(getattr(message, "content", None)) or "(empty)",
                    source_ref=assistant_turn_id or None,
                    metadata={
                        key: value
                        for key, value in {
                            "run_id": _safe_text(getattr(message, "run_id", None)) or None,
                            "image_count": len(getattr(message, "images", None) or []),
                            "attachment_count": len(getattr(message, "attachments", None) or []),
                        }.items()
                        if value not in (None, 0)
                    },
                    created_at=getattr(message, "timestamp", datetime.min),
                )
            )

        events: list[ContextEvent] = list(message_events)
        fallback_turn_id = max(turn_id_by_message_key.values(), default=0)

        for index, tool_call in enumerate(tool_call_records, start=1):
            assistant_turn_id = _safe_text(getattr(tool_call, "assistant_turn_id", None))
            turn_id = turn_id_by_assistant_turn_id.get(assistant_turn_id, fallback_turn_id)
            if turn_id <= 0:
                continue

            tool_name = _safe_text(getattr(tool_call, "tool_name", None)) or "tool"
            call_id = _safe_text(getattr(tool_call, "call_id", None)) or f"tool-{index}"
            metadata = {
                key: value
                for key, value in {
                    "status": _safe_text(getattr(tool_call, "status", None)) or None,
                    "run_id": _safe_text(getattr(tool_call, "run_id", None)) or None,
                    "assistant_turn_id": assistant_turn_id or None,
                    "duration_ms": getattr(tool_call, "duration_ms", None),
                }.items()
                if value is not None
            }

            events.append(
                ContextEvent(
                    event_id=f"tool_call:{session_id}:{call_id}",
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=normalize_context_event_type("tool_call"),
                    content=_build_tool_call_content(tool_call),
                    source=tool_name,
                    source_ref=call_id,
                    metadata=metadata,
                    created_at=getattr(tool_call, "started_ts", None)
                    or getattr(tool_call, "created_at", None)
                    or datetime.min,
                )
            )

            has_result = getattr(tool_call, "result", None) not in (None, "")
            has_error = _safe_text(getattr(tool_call, "error", None)) != ""
            status = _safe_text(getattr(tool_call, "status", None))
            if has_result or has_error or status in {"success", "error"}:
                events.append(
                    ContextEvent(
                        event_id=f"tool_result:{session_id}:{call_id}",
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=normalize_context_event_type("tool_result"),
                        content=_build_tool_result_content(tool_call),
                        source=tool_name,
                        source_ref=call_id,
                        metadata=metadata,
                        created_at=getattr(tool_call, "finished_ts", None)
                        or getattr(tool_call, "finished_at", None)
                        or getattr(tool_call, "created_at", None)
                        or datetime.min,
                    )
                )

        ordered_events = sorted(events, key=_timeline_sort_key)
        return validate_ordered_context_events(session_id, ordered_events)


def render_exported_prompt_context(exported_context: ExportedPromptContext) -> YuePromptContextBridge:
    section_by_block_name = default_prompt_export_sections()
    rendered_sections: list[str] = ["### Session Context"]
    for block in exported_context.blocks:
        if not _safe_text(block.content):
            continue
        rendered_sections.append(f"[{block.section}:{block.name}]")
        rendered_sections.append(block.content)
        if block.selected_candidate_ids:
            rendered_sections.append(
                f"trace.selected_candidate_ids={','.join(block.selected_candidate_ids)}"
            )
        if block.source_chunk_ids:
            rendered_sections.append(f"trace.source_chunk_ids={','.join(block.source_chunk_ids)}")

    if exported_context.selected_candidate_ids:
        rendered_sections.append(
            f"session_trace.selected_candidate_ids={','.join(exported_context.selected_candidate_ids)}"
        )
    if exported_context.source_chunk_ids:
        rendered_sections.append(
            f"session_trace.source_chunk_ids={','.join(exported_context.source_chunk_ids)}"
        )
    rendered_sections.append(
        f"session_trace.sections={','.join(exported_context.sections or section_by_block_name.values())}"
    )

    return YuePromptContextBridge(
        exported_context=exported_context,
        rendered_prompt_block="\n".join(rendered_sections).strip(),
        selected_candidate_ids=list(exported_context.selected_candidate_ids),
        source_chunk_ids=list(exported_context.source_chunk_ids),
        block_names=list(exported_context.block_names),
        sections=list(exported_context.sections),
    )


def _strengthen_prompt_context_with_authoritative_reference(
    prompt_context: YuePromptContextBridge,
    plan: Any,
) -> YuePromptContextBridge:
    selected_candidates = list(getattr(plan, "selected_candidates", []) or [])
    numbered_option = next(
        (
            candidate
            for candidate in selected_candidates
            if getattr(candidate, "content_type", None) == "numbered_option"
            and _safe_text(getattr(candidate, "content", None))
        ),
        None,
    )
    if numbered_option is None:
        return prompt_context

    ordinal = getattr(numbered_option, "metadata", {}).get("ordinal") if hasattr(numbered_option, "metadata") else None
    option_content = _safe_text(getattr(numbered_option, "content", None))
    if not option_content:
        return prompt_context

    authority_lines = [
        "resolver.authoritative_reference=numbered_option",
    ]
    if ordinal is not None:
        authority_lines.append(f"resolver.selected_ordinal={ordinal}")
        authority_lines.append(
            f"instruction: 如果用户问的是第{ordinal}个方案，先直接陈述下方命中的方案内容，再继续展开。"
        )
    authority_lines.append(f"resolver.selected_option_content={option_content}")

    rendered_prompt_block = prompt_context.rendered_prompt_block
    if rendered_prompt_block.startswith("### Session Context"):
        rendered_prompt_block = "\n".join(
            ["### Session Context", *authority_lines, rendered_prompt_block[len("### Session Context") :].lstrip("\n")]
        ).strip()
    else:
        rendered_prompt_block = "\n".join([*authority_lines, rendered_prompt_block]).strip()

    return YuePromptContextBridge(
        exported_context=prompt_context.exported_context,
        rendered_prompt_block=rendered_prompt_block,
        selected_candidate_ids=list(prompt_context.selected_candidate_ids),
        source_chunk_ids=list(prompt_context.source_chunk_ids),
        block_names=list(prompt_context.block_names),
        sections=list(prompt_context.sections),
    )


class YueSessionContextService:
    def __init__(
        self,
        *,
        manager: SessionContextManager | None = None,
        adapter: YueHostEventAdapter | None = None,
        retrieval_index: SQLiteFTSIndex | None = None,
        chunk_builder: ChunkBuilder | None = None,
        session_context_db_path: str | None = None,
    ) -> None:
        self._session_context_db_path = session_context_db_path or _session_context_db_path()
        self._retrieval_index = retrieval_index
        self._chunk_builder = chunk_builder

        if manager is None:
            self._retrieval_index = self._retrieval_index or SQLiteFTSIndex(self._session_context_db_path)
            self._chunk_builder = self._chunk_builder or ChunkBuilder()
            manager = SessionContextManager(
                context_retriever=ContextRetriever(index=self._retrieval_index),
            )

        self._manager = manager
        self._adapter = adapter or YueHostEventAdapter()

    def _materialize_session_memory(
        self,
        *,
        session_id: str,
        context_events: Sequence[ContextEvent],
    ) -> int:
        if self._retrieval_index is None or self._chunk_builder is None:
            return 0

        self._retrieval_index.delete_session(session_id)
        chunks = self._chunk_builder.build_chunks(context_events)
        for chunk in chunks:
            self._retrieval_index.add_chunk(chunk)
        return len(chunks)

    def build_prompt_context(
        self,
        *,
        session_id: str,
        current_input: str,
        chat_session: Any,
        tool_calls: Sequence[Any],
    ) -> YueSessionContextResult | None:
        message_records = list(getattr(chat_session, "messages", None) or [])
        host_records = [*message_records, *list(tool_calls or [])]
        if not host_records:
            return None

        recent_events = self._adapter.build_recent_events(
            session_id=session_id,
            host_records=host_records,
        )
        materialized_chunk_count = self._materialize_session_memory(
            session_id=session_id,
            context_events=recent_events,
        )
        plan = self._manager.resolve(
            session_id=session_id,
            current_input=current_input,
            recent_events=recent_events,
            config=ContextResolutionConfig(
                session_id=session_id,
                recent_window_token_budget=_recent_window_token_budget(),
                retrieval_token_budget=_retrieval_token_budget(),
                top_k=_session_context_top_k(),
                include_current_tool_results=False,
                boundary_policy=SessionRetrievalBoundaryPolicy(),
                metadata={"host": "yue"},
            ),
            current_tool_results=None,
        )
        exported_context = self._manager.export_prompt_context(plan)
        prompt_context = render_exported_prompt_context(exported_context)
        prompt_context = _strengthen_prompt_context_with_authoritative_reference(prompt_context, plan)
        inspection = build_session_context_inspection_payload(
            session_id=session_id,
            recent_events=recent_events,
            plan=plan,
            prompt_context=prompt_context,
        )
        inspection["materialized_chunk_count"] = materialized_chunk_count
        inspection["session_context_db_path"] = self._session_context_db_path
        logger.info(
            "SESSION_CONTEXT_RESOLVED %s",
            json.dumps(
                inspection,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        return YueSessionContextResult(plan=plan, prompt_context=prompt_context, inspection=inspection)


yue_session_context_service = YueSessionContextService()
