from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.services.memory.traffic_sample_export import export_traffic_derived_candidates


def _seed_db(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            create table sessions (
                id text primary key,
                title text not null,
                updated_at text
            );
            create table messages (
                id integer primary key autoincrement,
                session_id text not null,
                role text not null,
                content text not null,
                timestamp text,
                assistant_turn_id text,
                run_id text
            );
            create table tool_calls (
                id integer primary key autoincrement,
                session_id text not null,
                call_id text not null,
                tool_name text not null,
                assistant_turn_id text,
                run_id text,
                args text,
                result text,
                error text,
                status text not null,
                started_ts text,
                finished_ts text,
                created_at text,
                finished_at text,
                duration_ms real
            );
            """
        )
        connection.execute(
            "insert into sessions (id, title, updated_at) values (?, ?, ?)",
            ("sess-1", "Alice followup /Users/gavinzhang/project", "2026-05-25 14:00:00"),
        )
        connection.execute(
            "insert into sessions (id, title, updated_at) values (?, ?, ?)",
            ("sess-2", "Standalone question", "2026-05-25 13:00:00"),
        )
        connection.executemany(
            "insert into messages (session_id, role, content, timestamp, assistant_turn_id, run_id) values (?, ?, ?, ?, ?, ?)",
            [
                ("sess-1", "user", "给我三个持久化方案", "2026-05-25T10:00:00", None, None),
                ("sess-1", "assistant", "方案一 Redis，方案二 SQLite 持久化。联系 alice@example.com", "2026-05-25T10:00:02", "turn-1", "run-1"),
                ("sess-1", "user", "继续按刚才第二个方案展开，并保留 /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app.py", "2026-05-25T10:00:03", None, None),
                ("sess-2", "assistant", "今天天气不错", "2026-05-25T09:00:00", "turn-2", "run-2"),
                ("sess-2", "assistant", "文档在 docs/specs/a.md", "2026-05-25T09:00:01", "turn-3", "run-3"),
                ("sess-2", "user", "写一个新的 Python 函数", "2026-05-25T09:00:02", None, None),
            ],
        )
        connection.execute(
            """
            insert into tool_calls (
                session_id, call_id, tool_name, assistant_turn_id, run_id, args, result, error, status,
                started_ts, finished_ts, created_at, finished_at, duration_ms
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sess-1",
                "call-1",
                "exec",
                "turn-1",
                "run-1",
                json.dumps({"cmd": "rg session_context /Users/gavinzhang/ws-ai-recharge-2026/Yue"}),
                "/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/memory/session_context_host.py",
                None,
                "success",
                "2026-05-25T10:00:01",
                "2026-05-25T10:00:02",
                "2026-05-25T10:00:01",
                "2026-05-25T10:00:02",
                1000.0,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_export_traffic_derived_candidates_selects_and_redacts(tmp_path: Path) -> None:
    db_path = tmp_path / "traffic.db"
    _seed_db(db_path)

    export = export_traffic_derived_candidates(db_path=str(db_path), limit=5)

    assert export.total_sessions_scanned == 2
    assert export.eligible_sessions == 1
    assert export.exported_candidates == 1
    fixture = export.fixtures[0]
    assert fixture["review_status"] == "pending_manual_review"
    assert fixture["session_id_hash"] != "sess-1"
    assert "<email>" in fixture["messages"][1]["content"]
    assert "<path>" in fixture["current_input"]
    assert fixture["tool_calls"][0]["result"] == "<path>"
    assert fixture["proposed_resolution"]["action"] in {
        "use_recent_artifact",
        "use_recent_context",
        "retrieve_mid_session_memory",
        "no_context_needed",
    }
