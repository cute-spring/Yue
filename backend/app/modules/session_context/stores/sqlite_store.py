from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import ContextEvent, LongTermCandidate, MemoryChunk


def _ensure_path(db_path: str | Path) -> str:
    return str(db_path)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(_ensure_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS session_context_events (
          session_id TEXT NOT NULL,
          event_id TEXT NOT NULL,
          turn_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          source TEXT,
          source_ref TEXT,
          content TEXT NOT NULL,
          metadata_json TEXT,
          created_at TEXT NOT NULL,
          PRIMARY KEY (session_id, event_id)
        );

        CREATE INDEX IF NOT EXISTS idx_context_events_session_turn
        ON session_context_events(session_id, turn_id);

        CREATE TABLE IF NOT EXISTS session_memory_chunks (
          session_id TEXT NOT NULL,
          chunk_id TEXT NOT NULL,
          memory_scope TEXT NOT NULL,
          memory_type TEXT NOT NULL,
          chunk_type TEXT NOT NULL,
          content TEXT NOT NULL,
          retrieval_text TEXT NOT NULL,
          source_event_ids_json TEXT NOT NULL,
          start_turn_id INTEGER NOT NULL,
          end_turn_id INTEGER NOT NULL,
          priority INTEGER NOT NULL,
          ttl_seconds INTEGER,
          metadata_json TEXT,
          created_at TEXT NOT NULL,
          PRIMARY KEY (session_id, chunk_id)
        );

        CREATE INDEX IF NOT EXISTS idx_memory_chunks_session_type
        ON session_memory_chunks(session_id, memory_type, memory_scope);

        CREATE INDEX IF NOT EXISTS idx_memory_chunks_turns
        ON session_memory_chunks(session_id, start_turn_id, end_turn_id);

        CREATE TABLE IF NOT EXISTS long_term_candidates (
          candidate_id TEXT PRIMARY KEY,
          subject_scope TEXT NOT NULL,
          subject_id TEXT,
          candidate_type TEXT NOT NULL,
          content TEXT NOT NULL,
          confidence REAL NOT NULL,
          source_session_id TEXT NOT NULL,
          source_event_ids_json TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )


class SQLiteContextEventStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = _ensure_path(db_path)
        with _connect(self.db_path) as conn:
            _create_schema(conn)

    def append_event(self, event: ContextEvent) -> None:
        payload = event.to_dict()
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO session_context_events (
                    session_id, event_id, turn_id, event_type, source, source_ref,
                    content, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, event_id) DO UPDATE SET
                    turn_id=excluded.turn_id,
                    event_type=excluded.event_type,
                    source=excluded.source,
                    source_ref=excluded.source_ref,
                    content=excluded.content,
                    metadata_json=excluded.metadata_json,
                    created_at=excluded.created_at
                """,
                (
                    payload["session_id"],
                    payload["event_id"],
                    payload["turn_id"],
                    payload["event_type"],
                    payload["source"],
                    payload["source_ref"],
                    payload["content"],
                    json.dumps(payload["metadata"], ensure_ascii=False),
                    payload["created_at"],
                ),
            )
            conn.commit()

    def list_events(
        self,
        session_id: str,
        start_turn: int | None = None,
        end_turn: int | None = None,
    ) -> list[ContextEvent]:
        query = [
            "SELECT * FROM session_context_events WHERE session_id = ?",
        ]
        params: list[Any] = [session_id]
        if start_turn is not None:
            query.append("AND turn_id >= ?")
            params.append(start_turn)
        if end_turn is not None:
            query.append("AND turn_id <= ?")
            params.append(end_turn)
        query.append("ORDER BY turn_id ASC, created_at ASC, event_id ASC")
        sql = " ".join(query)
        with _connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_recent_events(self, session_id: str, limit_turns: int) -> list[ContextEvent]:
        if limit_turns <= 0:
            return []
        with _connect(self.db_path) as conn:
            turn_rows = conn.execute(
                """
                SELECT DISTINCT turn_id
                FROM session_context_events
                WHERE session_id = ?
                ORDER BY turn_id DESC
                LIMIT ?
                """,
                (session_id, limit_turns),
            ).fetchall()
        recent_turns = {row["turn_id"] for row in turn_rows}
        return [event for event in self.list_events(session_id) if event.turn_id in recent_turns]

    def _row_to_event(self, row: sqlite3.Row) -> ContextEvent:
        return ContextEvent(
            event_id=row["event_id"],
            session_id=row["session_id"],
            turn_id=row["turn_id"],
            event_type=row["event_type"],
            content=row["content"],
            source=row["source"],
            source_ref=row["source_ref"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=row["created_at"],
        )


class SQLiteMemoryChunkStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = _ensure_path(db_path)
        with _connect(self.db_path) as conn:
            _create_schema(conn)

    def upsert_chunk(self, chunk: MemoryChunk) -> None:
        payload = chunk.to_dict()
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO session_memory_chunks (
                    session_id, chunk_id, memory_scope, memory_type, chunk_type,
                    content, retrieval_text, source_event_ids_json, start_turn_id,
                    end_turn_id, priority, ttl_seconds, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, chunk_id) DO UPDATE SET
                    memory_scope=excluded.memory_scope,
                    memory_type=excluded.memory_type,
                    chunk_type=excluded.chunk_type,
                    content=excluded.content,
                    retrieval_text=excluded.retrieval_text,
                    source_event_ids_json=excluded.source_event_ids_json,
                    start_turn_id=excluded.start_turn_id,
                    end_turn_id=excluded.end_turn_id,
                    priority=excluded.priority,
                    ttl_seconds=excluded.ttl_seconds,
                    metadata_json=excluded.metadata_json,
                    created_at=excluded.created_at
                """,
                (
                    payload["session_id"],
                    payload["chunk_id"],
                    payload["memory_scope"],
                    payload["memory_type"],
                    payload["chunk_type"],
                    payload["content"],
                    payload["retrieval_text"],
                    json.dumps(payload["source_event_ids"], ensure_ascii=False),
                    payload["start_turn_id"],
                    payload["end_turn_id"],
                    payload["priority"],
                    payload["ttl_seconds"],
                    json.dumps(payload["metadata"], ensure_ascii=False),
                    payload["created_at"],
                ),
            )
            conn.commit()

    def list_chunks(self, session_id: str, memory_type: str = "mid_term") -> list[MemoryChunk]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM session_memory_chunks
                WHERE session_id = ? AND memory_type = ?
                ORDER BY priority DESC, end_turn_id ASC, chunk_id ASC
                """,
                (session_id, memory_type),
            ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def get_chunks_by_ids(self, session_id: str, chunk_ids: list[str]) -> list[MemoryChunk]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        sql = (
            "SELECT * FROM session_memory_chunks "
            f"WHERE session_id = ? AND chunk_id IN ({placeholders})"
        )
        with _connect(self.db_path) as conn:
            rows = conn.execute(sql, [session_id, *chunk_ids]).fetchall()
        by_id = {row["chunk_id"]: self._row_to_chunk(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    def _row_to_chunk(self, row: sqlite3.Row) -> MemoryChunk:
        return MemoryChunk(
            chunk_id=row["chunk_id"],
            session_id=row["session_id"],
            memory_scope=row["memory_scope"],
            memory_type=row["memory_type"],
            chunk_type=row["chunk_type"],
            content=row["content"],
            retrieval_text=row["retrieval_text"],
            source_event_ids=json.loads(row["source_event_ids_json"]),
            start_turn_id=row["start_turn_id"],
            end_turn_id=row["end_turn_id"],
            priority=row["priority"],
            ttl_seconds=row["ttl_seconds"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=row["created_at"],
        )


class SQLiteLongTermCandidateStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = _ensure_path(db_path)
        with _connect(self.db_path) as conn:
            _create_schema(conn)

    def upsert_candidate(self, candidate: LongTermCandidate) -> None:
        payload = candidate.to_dict()
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO long_term_candidates (
                    candidate_id, subject_scope, subject_id, candidate_type,
                    content, confidence, source_session_id, source_event_ids_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    subject_scope=excluded.subject_scope,
                    subject_id=excluded.subject_id,
                    candidate_type=excluded.candidate_type,
                    content=excluded.content,
                    confidence=excluded.confidence,
                    source_session_id=excluded.source_session_id,
                    source_event_ids_json=excluded.source_event_ids_json,
                    status=excluded.status,
                    created_at=excluded.created_at
                """,
                (
                    payload["candidate_id"],
                    payload["subject_scope"],
                    payload["subject_id"],
                    payload["candidate_type"],
                    payload["content"],
                    payload["confidence"],
                    payload["source_session_id"],
                    json.dumps(payload["source_event_ids"], ensure_ascii=False),
                    payload["status"],
                    payload["created_at"],
                ),
            )
            conn.commit()

    def list_candidates(self, source_session_id: str) -> list[LongTermCandidate]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM long_term_candidates
                WHERE source_session_id = ?
                ORDER BY created_at ASC, candidate_id ASC
                """,
                (source_session_id,),
            ).fetchall()
        return [self._row_to_candidate(row) for row in rows]

    def _row_to_candidate(self, row: sqlite3.Row) -> LongTermCandidate:
        return LongTermCandidate(
            candidate_id=row["candidate_id"],
            subject_scope=row["subject_scope"],
            subject_id=row["subject_id"],
            candidate_type=row["candidate_type"],
            content=row["content"],
            confidence=row["confidence"],
            source_session_id=row["source_session_id"],
            source_event_ids=json.loads(row["source_event_ids_json"]),
            status=row["status"],
            created_at=row["created_at"],
        )
