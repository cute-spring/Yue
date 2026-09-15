from __future__ import annotations

from app.modules.session_context.models import ContextEvent, LongTermCandidate, MemoryChunk
from app.modules.session_context.stores.base import ContextEventStore as ContextEventStoreBase
from app.modules.session_context.stores.base import LongTermCandidateStore as LongTermCandidateStoreBase
from app.modules.session_context.stores.base import MemoryChunkStore as MemoryChunkStoreBase


class ContextEventStore(ContextEventStoreBase):
    def __init__(self) -> None:
        self._events_by_session: dict[str, list[ContextEvent]] = {}

    def append_event(self, event: ContextEvent) -> None:
        events = self._events_by_session.setdefault(event.session_id, [])
        events.append(event)

    def list_events(self, session_id: str) -> list[ContextEvent]:
        return list(self._events_by_session.get(session_id, []))

    def get_recent_events(
        self, session_id: str, limit: int | None = None, limit_turns: int | None = None
    ) -> list[ContextEvent]:
        if limit is None:
            limit = limit_turns if limit_turns is not None else 0
        if limit <= 0:
            return []
        events = self._events_by_session.get(session_id, [])
        return list(events[-limit:])


class MemoryChunkStore(MemoryChunkStoreBase):
    def __init__(self) -> None:
        self._chunks_by_session: dict[str, dict[str, MemoryChunk]] = {}

    def upsert_chunk(self, chunk: MemoryChunk) -> None:
        chunks = self._chunks_by_session.setdefault(chunk.session_id, {})
        chunks[chunk.chunk_id] = chunk

    def list_chunks(self, session_id: str) -> list[MemoryChunk]:
        chunks = self._chunks_by_session.get(session_id, {})
        return list(chunks.values())

    def get_chunks_by_ids(self, session_id: str, chunk_ids: list[str]) -> list[MemoryChunk]:
        chunks = self._chunks_by_session.get(session_id, {})
        return [chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in chunks]


class LongTermCandidateStore(LongTermCandidateStoreBase):
    def __init__(self) -> None:
        self._candidates_by_session: dict[str, dict[str, LongTermCandidate]] = {}

    def upsert_candidate(self, candidate: LongTermCandidate) -> None:
        candidates = self._candidates_by_session.setdefault(candidate.source_session_id, {})
        candidates[candidate.candidate_id] = candidate

    def list_candidates(self, source_session_id: str) -> list[LongTermCandidate]:
        candidates = self._candidates_by_session.get(source_session_id, {})
        return sorted(
            candidates.values(),
            key=lambda candidate: (candidate.created_at, candidate.candidate_id),
        )


InMemoryContextEventStore = ContextEventStore
InMemoryMemoryChunkStore = MemoryChunkStore
InMemoryLongTermCandidateStore = LongTermCandidateStore
