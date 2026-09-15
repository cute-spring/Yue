from __future__ import annotations

from app.modules.session_context.indexing.base import RetrievalIndex
from app.modules.session_context.models import ContextEvent, MemoryChunk, RetrievedChunk

from .query_builder import build_query
from .ranker import rank_chunks


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


class ContextRetriever:
    def __init__(self, chunks: list[MemoryChunk] | None = None, index: RetrievalIndex | None = None) -> None:
        self._chunks = chunks or []
        self._index = index

    def retrieve(
        self,
        session_id: str,
        current_input: str,
        recent_events: list[ContextEvent],
        top_k: int = 5,
        budget_tokens: int = 300,
    ) -> list[RetrievedChunk]:
        query = build_query(current_input=current_input, recent_events=recent_events)
        if self._index is not None:
            hits = self._index.search(session_id=session_id, query=query, top_k=top_k)
            return self._apply_budget(hits, budget_tokens)

        session_chunks = [chunk for chunk in self._chunks if chunk.session_id == session_id]
        ranked = rank_chunks(query, session_chunks)

        out: list[RetrievedChunk] = []
        used_tokens = 0
        rank = 1
        for chunk, score in ranked:
            if len(out) >= top_k:
                break
            next_cost = _estimate_tokens(chunk.content)
            if used_tokens + next_cost > budget_tokens:
                continue
            out.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    rank=rank,
                    retrieval_source="in_memory",
                )
            )
            used_tokens += next_cost
            rank += 1
        return out

    def _apply_budget(self, hits: list[RetrievedChunk], budget_tokens: int) -> list[RetrievedChunk]:
        kept: list[RetrievedChunk] = []
        used = 0
        for hit in hits:
            cost = _estimate_tokens(hit.chunk.content)
            if used + cost > budget_tokens:
                continue
            kept.append(hit)
            used += cost
        return kept
