from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import sqlite3
from typing import Any

from app.services.chat_service import Message, ToolCall
from app.services.memory.session_context_host import YueHostEventAdapter
from session_context_manager import ContextResolutionConfig, SessionContextManager, SessionContextReplayCase


_REFERENCE_SIGNAL_PATTERN = re.compile(
    r"(刚才|继续|那个|同样|也|版本|方案|链接|link|doc|文档|上面|之前|earlier|same|that)",
    re.IGNORECASE,
)
_HOME_PATH_PATTERN = re.compile(r"/Users/[^/\s]+")
_ABSOLUTE_PATH_PATTERN = re.compile(r"(?<!\w)(?:/[^/\s]+)+")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_LONG_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9_-]{24,}\b")


@dataclass(frozen=True)
class TrafficDerivedExportSummary:
    exported_at: str
    source_db_path: str
    total_sessions_scanned: int
    eligible_sessions: int
    exported_candidates: int
    fixtures: list[dict[str, Any]]


def _redact_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = _HOME_PATH_PATTERN.sub("/Users/<redacted>", text)
    text = _EMAIL_PATTERN.sub("<email>", text)
    text = _URL_PATTERN.sub("<url>", text)
    text = _UUID_PATTERN.sub("<uuid>", text)
    text = _LONG_TOKEN_PATTERN.sub("<token>", text)
    text = _ABSOLUTE_PATH_PATTERN.sub("<path>", text)
    return text


def _hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]


def _parse_dt(raw_value: Any) -> datetime | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    normalized = raw_value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _load_rows(connection: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    cursor = connection.execute(sql, params)
    return list(cursor.fetchall())


def _json_loads(raw_value: Any) -> Any:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, (dict, list)):
        return raw_value
    try:
        return json.loads(raw_value)
    except Exception:
        return raw_value


def _build_host_records(connection: sqlite3.Connection, session_id: str) -> tuple[list[object], list[Message], list[ToolCall]]:
    message_rows = _load_rows(
        connection,
        """
        select role, content, timestamp, assistant_turn_id, run_id
        from messages
        where session_id = ?
        order by timestamp asc, id asc
        """,
        (session_id,),
    )
    tool_rows = _load_rows(
        connection,
        """
        select session_id, call_id, tool_name, assistant_turn_id, run_id, args, result, error, status,
               started_ts, finished_ts, created_at, finished_at, duration_ms
        from tool_calls
        where session_id = ?
        order by coalesce(started_ts, created_at) asc, id asc
        """,
        (session_id,),
    )

    messages = [
        Message(
            role=row["role"],
            content=row["content"],
            timestamp=_parse_dt(row["timestamp"]) or datetime.min,
            assistant_turn_id=row["assistant_turn_id"],
            run_id=row["run_id"],
        )
        for row in message_rows
    ]
    tool_calls = [
        ToolCall(
            session_id=row["session_id"],
            call_id=row["call_id"],
            tool_name=row["tool_name"],
            assistant_turn_id=row["assistant_turn_id"],
            run_id=row["run_id"],
            args=_json_loads(row["args"]),
            result=row["result"],
            error=row["error"],
            status=row["status"],
            started_ts=_parse_dt(row["started_ts"]),
            finished_ts=_parse_dt(row["finished_ts"]),
            created_at=_parse_dt(row["created_at"]) or datetime.min,
            finished_at=_parse_dt(row["finished_at"]),
            duration_ms=row["duration_ms"],
        )
        for row in tool_rows
    ]
    return [*messages, *tool_calls], messages, tool_calls


def _looks_like_reference_query(current_input: str) -> bool:
    return bool(_REFERENCE_SIGNAL_PATTERN.search(current_input or ""))


def _select_candidate_sessions(connection: sqlite3.Connection, limit: int) -> tuple[int, list[sqlite3.Row]]:
    total_sessions = _load_rows(connection, "select count(*) as count from sessions")[0]["count"]
    rows = _load_rows(
        connection,
        """
        with message_stats as (
            select
                session_id,
                count(*) as message_count,
                sum(case when role = 'user' then 1 else 0 end) as user_message_count,
                max(case when role = 'user' then timestamp else null end) as last_user_ts
            from messages
            group by session_id
        ),
        tool_stats as (
            select session_id, count(*) as tool_call_count
            from tool_calls
            group by session_id
        )
        select
            s.id as session_id,
            s.updated_at as updated_at,
            s.title as title,
            ms.message_count as message_count,
            ms.user_message_count as user_message_count,
            coalesce(ts.tool_call_count, 0) as tool_call_count,
            (
                select content
                from messages m
                where m.session_id = s.id and m.role = 'user'
                order by m.timestamp desc, m.id desc
                limit 1
            ) as current_input
        from sessions s
        join message_stats ms on ms.session_id = s.id
        left join tool_stats ts on ts.session_id = s.id
        where ms.message_count >= 3
          and ms.user_message_count >= 1
        order by s.updated_at desc
        """,
    )
    eligible_rows = [
        row
        for row in rows
        if isinstance(row["current_input"], str)
        and row["current_input"].strip()
        and (_looks_like_reference_query(row["current_input"]) or int(row["tool_call_count"] or 0) > 0)
    ]
    return total_sessions, eligible_rows[:limit]


def export_traffic_derived_candidates(*, db_path: str, limit: int = 10) -> TrafficDerivedExportSummary:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        total_sessions, candidate_rows = _select_candidate_sessions(connection, limit)
        manager = SessionContextManager()
        adapter = YueHostEventAdapter()
        fixtures: list[dict[str, Any]] = []

        for index, row in enumerate(candidate_rows, start=1):
            host_records, messages, tool_calls = _build_host_records(connection, row["session_id"])
            current_input = str(row["current_input"] or "")
            replay_case = SessionContextReplayCase.from_host_records(
                case_id=f"traffic_candidate_{index:03d}",
                session_id=str(row["session_id"]),
                current_input=current_input,
                host_records=host_records,
                adapter=adapter,
                config=ContextResolutionConfig(session_id=str(row["session_id"])),
            )
            plan = replay_case.run(manager)
            fixtures.append(
                {
                    "case_id": f"traffic_candidate_{index:03d}",
                    "source": "local_yue_db",
                    "review_status": "pending_manual_review",
                    "session_id_hash": _hash_session_id(str(row["session_id"])),
                    "session_title_redacted": _redact_text(str(row["title"] or "")),
                    "updated_at": str(row["updated_at"] or ""),
                    "message_count": int(row["message_count"] or 0),
                    "tool_call_count": int(row["tool_call_count"] or 0),
                    "current_input": _redact_text(current_input),
                    "messages": [
                        {
                            "role": message.role,
                            "content": _redact_text(message.content),
                            "timestamp": message.timestamp.isoformat(),
                            "assistant_turn_id": message.assistant_turn_id,
                            "run_id": message.run_id,
                        }
                        for message in messages
                    ],
                    "tool_calls": [
                        {
                            "tool_name": tool_call.tool_name,
                            "assistant_turn_id": tool_call.assistant_turn_id,
                            "status": tool_call.status,
                            "args": _redact_text(json.dumps(tool_call.args, ensure_ascii=False, sort_keys=True))
                            if tool_call.args is not None
                            else None,
                            "result": _redact_text(tool_call.result),
                            "error": _redact_text(tool_call.error),
                        }
                        for tool_call in tool_calls
                    ],
                    "proposed_resolution": {
                        "action": plan.decision.action.value,
                        "reason": plan.decision.reason.value,
                        "should_retrieve": plan.decision.should_retrieve,
                        "reference_signal_strength": plan.telemetry.get("reference_signal_strength"),
                        "selected_content_type": (
                            plan.selected_candidates[0].content_type if plan.selected_candidates else None
                        ),
                        "selected_source": plan.selected_candidates[0].source if plan.selected_candidates else None,
                        "prompt_block_names": list(plan.telemetry.get("prompt_block_names", []) or []),
                    },
                }
            )

        return TrafficDerivedExportSummary(
            exported_at=datetime.utcnow().isoformat() + "Z",
            source_db_path=db_path,
            total_sessions_scanned=int(total_sessions),
            eligible_sessions=len(candidate_rows),
            exported_candidates=len(fixtures),
            fixtures=fixtures,
        )
    finally:
        connection.close()
