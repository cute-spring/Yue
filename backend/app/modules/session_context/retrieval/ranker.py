from __future__ import annotations

import re

from app.modules.session_context.models import MemoryChunk

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


def rank_chunks(query: str, chunks: list[MemoryChunk]) -> list[tuple[MemoryChunk, float]]:
    context_terms, question_terms = _split_query(query)
    query_terms = {term for term in context_terms + question_terms if term}
    scored: list[tuple[MemoryChunk, float]] = []
    for chunk in chunks:
        text_terms = set(_tokenize(chunk.retrieval_text))
        question_overlap = len(set(question_terms).intersection(text_terms))
        context_overlap = len(set(context_terms).intersection(text_terms))
        overlap = len(query_terms.intersection(text_terms))
        score = float(question_overlap * 50 + context_overlap * 5 + overlap * 10 + chunk.priority)
        scored.append((chunk, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
