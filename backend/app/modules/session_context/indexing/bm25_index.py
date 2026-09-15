from __future__ import annotations

import re

from app.modules.session_context.indexing.base import RetrievalIndex
from app.modules.session_context.models import MemoryChunk, RetrievedChunk

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
_CJK_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
_QUESTION_MARKER = "[QUESTION]"


def _tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in _TOKEN_PATTERN.findall(text)]
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


class InMemoryBM25Index(RetrievalIndex):
    def __init__(self) -> None:
        self._chunks_by_session: dict[str, dict[str, MemoryChunk]] = {}

    def add_chunk(self, chunk: MemoryChunk) -> None:
        chunks = self._chunks_by_session.setdefault(chunk.session_id, {})
        chunks[chunk.chunk_id] = chunk

    def search(self, session_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []
        context_tokens, question_tokens = _split_query(query)
        if not context_tokens and not question_tokens:
            return []

        chunks = self._chunks_by_session.get(session_id, {})
        scored: list[tuple[MemoryChunk, float]] = []

        for chunk in chunks.values():
            text_tokens = _tokenize(chunk.retrieval_text)
            if not text_tokens:
                continue

            token_counts: dict[str, int] = {}
            for token in text_tokens:
                token_counts[token] = token_counts.get(token, 0) + 1

            question_matched_terms = sum(1 for token in set(question_tokens) if token_counts.get(token, 0) > 0)
            context_matched_terms = sum(1 for token in set(context_tokens) if token_counts.get(token, 0) > 0)
            if question_matched_terms == 0 and context_matched_terms == 0:
                continue
            question_total_matches = sum(token_counts.get(token, 0) for token in question_tokens)
            context_total_matches = sum(token_counts.get(token, 0) for token in context_tokens)

            score = float(question_matched_terms * 50 + question_total_matches * 10 + context_matched_terms * 5 + context_total_matches)
            scored.append((chunk, score))

        scored.sort(key=lambda item: (-item[1], item[0].chunk_id))
        top = scored[:top_k]
        return [
            RetrievedChunk(
                chunk=chunk,
                score=score,
                rank=index + 1,
                retrieval_source="keyword",
                reason="keyword overlap",
            )
            for index, (chunk, score) in enumerate(top)
        ]

    def delete_session(self, session_id: str) -> None:
        self._chunks_by_session.pop(session_id, None)


BM25Index = InMemoryBM25Index
