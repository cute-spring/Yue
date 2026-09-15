from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.session_context.models import MemoryChunk, RetrievedChunk


class RetrievalIndex(ABC):
    @abstractmethod
    def add_chunk(self, chunk: MemoryChunk) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, session_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError
