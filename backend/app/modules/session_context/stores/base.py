from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.session_context.models import ContextEvent, LongTermCandidate, MemoryChunk


class ContextEventStore(ABC):
    @abstractmethod
    def append_event(self, event: ContextEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, session_id: str) -> list[ContextEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_recent_events(self, session_id: str, limit: int) -> list[ContextEvent]:
        raise NotImplementedError


class MemoryChunkStore(ABC):
    @abstractmethod
    def upsert_chunk(self, chunk: MemoryChunk) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_chunks(self, session_id: str) -> list[MemoryChunk]:
        raise NotImplementedError

    @abstractmethod
    def get_chunks_by_ids(self, session_id: str, chunk_ids: list[str]) -> list[MemoryChunk]:
        raise NotImplementedError


class LongTermCandidateStore(ABC):
    @abstractmethod
    def upsert_candidate(self, candidate: LongTermCandidate) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_candidates(self, source_session_id: str) -> list[LongTermCandidate]:
        raise NotImplementedError
