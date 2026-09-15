from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from ..models import MemoryChunk, RetrievedChunk


def _ensure_path(db_path: str | Path) -> str:
    return str(db_path)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(_ensure_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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

        CREATE VIRTUAL TABLE IF NOT EXISTS session_memory_chunks_fts
        USING fts5(
          chunk_id UNINDEXED,
          session_id UNINDEXED,
          retrieval_text,
          content
        );
        """
    )


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_CJK_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
_QUESTION_MARKER = "[QUESTION]"
_OPTION_QUERY_PATTERNS = (
    re.compile(r"第\s*([1-9][0-9]*)\s*个方案"),
    re.compile(r"第\s*([一二三四五六七八九十])\s*个方案"),
    re.compile(r"方案\s*([一二三四五六七八九十])"),
    re.compile(r"方案\s*([A-Z])"),
    re.compile(r"方案\s*([1-9][0-9]*)"),
    re.compile(r"\boption\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b", re.IGNORECASE),
    re.compile(r"\boption\s+([1-9][0-9]*)\b", re.IGNORECASE),
)
_ORDINAL_MAP = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7,
    "H": 8,
    "I": 9,
    "J": 10,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in _TOKEN_RE.findall(text)]
    for run in _CJK_RUN_PATTERN.findall(text):
        if len(run) == 1:
            tokens.append(run)
            continue
        tokens.extend(run[idx : idx + 2] for idx in range(len(run) - 1))
    return tokens


def _split_query(query: str) -> tuple[list[str], list[str]]:
    context_parts: list[str] = []
    question_text = ""
    for part in query.split(" | "):
        if part.startswith(_QUESTION_MARKER):
            question_text = part[len(_QUESTION_MARKER) :].strip()
            break
        context_parts.append(part)
    context_text = " ".join(context_parts)
    return _tokenize(context_text), _tokenize(question_text)


def _extract_target_option_ordinal(query: str) -> int | None:
    _, question_text = _split_query(query)
    ordinals: set[int] = set()
    question_raw = ""
    for part in query.split(" | "):
        if part.startswith(_QUESTION_MARKER):
            question_raw = part[len(_QUESTION_MARKER) :].strip()
            break
    if not question_raw:
        question_raw = " ".join(question_text)
    for pattern in _OPTION_QUERY_PATTERNS:
        for match in pattern.finditer(question_raw):
            value = match.group(1)
            if value.isdigit():
                ordinals.add(int(value))
            else:
                ordinal = _ORDINAL_MAP.get(value.upper() if len(value) == 1 and value.isalpha() else value.lower())
                if ordinal is not None:
                    ordinals.add(ordinal)
    if len(ordinals) == 1:
        return next(iter(ordinals))
    return None


class SQLiteFTSIndex:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = _ensure_path(db_path)
        with _connect(self.db_path) as conn:
            _create_schema(conn)

    def add_chunk(self, chunk: MemoryChunk) -> None:
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
            conn.execute(
                "DELETE FROM session_memory_chunks_fts WHERE chunk_id = ? AND session_id = ?",
                (payload["chunk_id"], payload["session_id"]),
            )
            conn.execute(
                """
                INSERT INTO session_memory_chunks_fts (chunk_id, session_id, retrieval_text, content)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload["chunk_id"],
                    payload["session_id"],
                    payload["retrieval_text"],
                    payload["content"],
                ),
            )
            conn.commit()

    def search(self, session_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        if top_k <= 0 or not query.strip():
            return []
        target_option_ordinal = _extract_target_option_ordinal(query)
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT c.*
                FROM session_memory_chunks_fts f
                JOIN session_memory_chunks c
                  ON c.session_id = f.session_id AND c.chunk_id = f.chunk_id
                WHERE f.session_id = ?
                """,
                (session_id,),
            ).fetchall()
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            score = self._score(
                query,
                row["retrieval_text"],
                row["content"],
                row["chunk_type"],
                row["priority"],
                row["metadata_json"],
                target_option_ordinal,
            )
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], -item[1]["priority"], item[1]["chunk_id"]))
        return [
            RetrievedChunk(
                chunk=self._row_to_chunk(row),
                score=float(score),
                rank=rank,
                retrieval_source="fts",
            )
            for rank, (score, row) in enumerate(scored[:top_k], start=1)
        ]

    def delete_session(self, session_id: str) -> None:
        with _connect(self.db_path) as conn:
            conn.execute("DELETE FROM session_memory_chunks_fts WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM session_memory_chunks WHERE session_id = ?", (session_id,))
            conn.commit()

    def _score(
        self,
        query: str,
        retrieval_text: str,
        content: str,
        chunk_type: str,
        priority: int,
        metadata_json: str | None,
        target_option_ordinal: int | None,
    ) -> float:
        context_tokens, question_tokens = _split_query(query)
        chunk_text = f"{retrieval_text} {content}"
        chunk_tokens = set(_tokenize(chunk_text))
        question_overlap = sum(1 for token in set(question_tokens) if token in chunk_tokens)
        context_overlap = sum(1 for token in set(context_tokens) if token in chunk_tokens)
        if question_overlap == 0 and context_overlap == 0:
            return 0.0
        question_matches = sum(1 for token in question_tokens if token in chunk_tokens)
        context_matches = sum(1 for token in context_tokens if token in chunk_tokens)
        boost = priority / 100.0
        if chunk_type == "tool_result":
            boost += 0.25
        if any(token in {"permission", "permissions", "role", "roles", "admin", "administrator"} for token in context_tokens + question_tokens):
            if any(token in chunk_tokens for token in {"permission", "permissions", "role", "roles", "admin", "administrator"}):
                boost += 1.5
            if "guest" in chunk_tokens:
                boost -= 0.25
        if target_option_ordinal is not None:
            metadata = json.loads(metadata_json) if metadata_json else {}
            chunk_ordinal = metadata.get("ordinal")
            if chunk_type == "numbered_option":
                if chunk_ordinal == target_option_ordinal:
                    boost += 300.0
                else:
                    boost -= 40.0
            elif chunk_type == "dialogue_pair":
                boost -= 60.0
        return question_overlap * 5 + question_matches + context_overlap * 2 + context_matches + boost

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
