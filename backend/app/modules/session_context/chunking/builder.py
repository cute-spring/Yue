from __future__ import annotations

import re
from typing import Iterable

from app.modules.session_context.models import ContextEvent, MemoryChunk

from .normalizers import ToolResultNormalizer


_OPTION_PATTERNS = (
    (re.compile(r"(方案([A-Z]))"), "latin"),
    (re.compile(r"(方案([一二三四五六七八九十]))"), "zh"),
    (re.compile(r"(方案\s*([1-9][0-9]*))"), "numeric"),
    (re.compile(r"\b(option)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b", re.IGNORECASE), "en"),
    (re.compile(r"\b(option)\s+([1-9][0-9]*)\b", re.IGNORECASE), "numeric"),
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
_LATIN_ORDINAL_TEXT = {
    1: "A",
    2: "B",
    3: "C",
    4: "D",
    5: "E",
    6: "F",
    7: "G",
    8: "H",
    9: "I",
    10: "J",
}
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class ChunkBuilder:
    def __init__(self) -> None:
        self._normalizer = ToolResultNormalizer()

    def build(self, events: Iterable[ContextEvent]) -> list[MemoryChunk]:
        event_list = list(events)
        chunks: list[MemoryChunk] = []
        chunks.extend(self._build_dialogue_pairs(event_list))

        for event in event_list:
            chunks.extend(self._build_numbered_option_chunks(event))
            if event.event_type == "tool_result":
                payload = event.metadata if event.metadata else event.content
                norm = self._normalizer.normalize(payload, source=event.source, source_ref=event.source_ref)
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"chunk-{event.event_id}",
                        session_id=event.session_id,
                        chunk_type="tool_result",
                        content=norm["normalized_content"] or event.content,
                        retrieval_text=norm["normalized_content"] or event.content,
                        source_event_ids=[event.event_id],
                        start_turn_id=event.turn_id,
                        end_turn_id=event.turn_id,
                        priority=85,
                        ttl_seconds=norm.get("ttl_seconds"),
                        metadata={
                            "source": norm.get("source"),
                            "source_ref": norm.get("source_ref"),
                            "key_fields": norm.get("key_fields", {}),
                        },
                    )
                )
            elif event.event_type in {"command", "code"} or self._looks_like_code_or_command(event.content):
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"chunk-{event.event_id}",
                        session_id=event.session_id,
                        chunk_type="code_or_command",
                        content=event.content,
                        retrieval_text=event.content,
                        source_event_ids=[event.event_id],
                        start_turn_id=event.turn_id,
                        end_turn_id=event.turn_id,
                        priority=70,
                    )
                )
            elif event.event_type == "procedure" or self._looks_like_procedure(event.content):
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"chunk-{event.event_id}",
                        session_id=event.session_id,
                        chunk_type="procedure",
                        content=event.content,
                        retrieval_text=event.content,
                        source_event_ids=[event.event_id],
                        start_turn_id=event.turn_id,
                        end_turn_id=event.turn_id,
                        priority=75,
                    )
                )
        return chunks

    def build_chunks(self, events: Iterable[ContextEvent]) -> list[MemoryChunk]:
        return self.build(events)

    def _build_dialogue_pairs(self, events: list[ContextEvent]) -> list[MemoryChunk]:
        chunks: list[MemoryChunk] = []
        for idx in range(len(events) - 1):
            first = events[idx]
            second = events[idx + 1]
            if first.event_type == "user_message" and second.event_type == "assistant_message":
                if first.session_id != second.session_id:
                    continue
                content = f"User: {first.content}\nAssistant: {second.content}"
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"chunk-{first.event_id}-{second.event_id}",
                        session_id=first.session_id,
                        chunk_type="dialogue_pair",
                        content=content,
                        retrieval_text=content,
                        source_event_ids=[first.event_id, second.event_id],
                        start_turn_id=first.turn_id,
                        end_turn_id=second.turn_id,
                        priority=80,
                    )
                )
        return chunks

    def _looks_like_code_or_command(self, content: str) -> bool:
        lowered = content.lower()
        if "```" in content or lowered.startswith("$") or "bash" in lowered or "echo " in lowered:
            return True
        stripped = content.strip()
        if _CJK_RE.search(stripped):
            return False
        return bool(re.match(r"^[A-Za-z]+-[A-Za-z0-9]+(?:\s|$)", stripped))

    def _looks_like_procedure(self, content: str) -> bool:
        stripped = content.strip()
        return stripped.startswith("1.") or stripped.startswith("1)")

    def _build_numbered_option_chunks(self, event: ContextEvent) -> list[MemoryChunk]:
        if event.event_type not in {"user_message", "assistant_message"}:
            return []

        chunks: list[MemoryChunk] = []
        seen: set[tuple[int, str]] = set()
        for pattern, locale in _OPTION_PATTERNS:
            matches = list(pattern.finditer(event.content))
            if not matches:
                continue
            for index, match in enumerate(matches):
                ordinal_text = match.group(2)
                if locale == "en":
                    ordinal_text = ordinal_text.lower()
                ordinal = int(ordinal_text) if locale == "numeric" else _ORDINAL_MAP.get(ordinal_text)
                if ordinal is None:
                    continue
                span_key = (match.start(1), match.group(1))
                if span_key in seen:
                    continue
                seen.add(span_key)
                snippet = self._extract_option_snippet(event.content, matches, index)
                retrieval_text = self._build_option_retrieval_text(snippet, ordinal)
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"chunk-{event.event_id}-option-{ordinal}",
                        session_id=event.session_id,
                        chunk_type="numbered_option",
                        content=snippet,
                        retrieval_text=retrieval_text,
                        source_event_ids=[event.event_id],
                        start_turn_id=event.turn_id,
                        end_turn_id=event.turn_id,
                        priority=90,
                        metadata={
                            "ordinal": ordinal,
                            "ordinal_text": ordinal_text,
                        },
                    )
                )
        return chunks

    def _extract_option_snippet(
        self,
        content: str,
        matches: list[re.Match[str]],
        index: int,
    ) -> str:
        start = matches[index].start(1)
        end = matches[index + 1].start(1) if index + 1 < len(matches) else len(content)
        snippet = content[start:end].strip()
        return snippet.rstrip("，,；;。 ")

    def _build_option_retrieval_text(self, snippet: str, ordinal: int) -> str:
        labels = [f"第{ordinal}个方案", f"方案{ordinal}", f"option {ordinal}"]
        latin = _LATIN_ORDINAL_TEXT.get(ordinal)
        if latin:
            labels.append(f"方案{latin}")
        return " ".join([*labels, snippet])
