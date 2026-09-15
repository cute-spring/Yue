from __future__ import annotations

import re

from app.modules.session_context.longterm_candidates import filter_candidate_events
from app.modules.session_context.models import (
    ContextEvent,
    RecentWindowSnapshot,
    ResolutionCandidate,
    context_event_to_resolution_candidate,
)


_OPTION_PATTERNS = (
    (re.compile(r"(方案([一二三四五六七八九十]))"), "zh"),
    (re.compile(r"(方案\s*([1-9][0-9]*))"), "numeric"),
    (re.compile(r"\b(option)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b", re.IGNORECASE), "en"),
    (re.compile(r"\b(option)\s+([1-9][0-9]*)\b", re.IGNORECASE), "numeric"),
)
_ORDINAL_MAP = {
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


def _looks_like_code_or_command(content: str) -> bool:
    lowered = content.lower()
    stripped = content.strip()
    if "```" in content or lowered.startswith("$") or "powershell" in lowered or "bash" in lowered:
        return True
    if re.match(r"^[A-Za-z]+-[A-Za-z0-9]+(?:\s|$)", stripped):
        return True
    return any(
        token in lowered
        for token in ("select ", "curl ", "git ", "echo ", "python ", "python3 ", "export-csv", "|")
    )


def _looks_like_document_reference(content: str) -> bool:
    lowered = content.lower()
    return (
        "http://" in lowered
        or "https://" in lowered
        or ".md" in lowered
        or "docs/" in lowered
        or "document" in lowered
        or "文档" in content
        or "链接" in content
    )


def _looks_like_decision(content: str) -> bool:
    lowered = content.lower()
    return any(
        token in lowered
        for token in ("we'll use", "we will use", "decided", "decision", "use this", "go with option")
    ) or any(token in content for token in ("结论", "决定", "按这个", "采用"))


def _normalize_summary(content: str, limit: int = 120) -> str:
    collapsed = " ".join(content.strip().split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _candidate(
    event: ContextEvent,
    *,
    suffix: str,
    content_type: str,
    summary: str,
    score: float,
    evidence: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> ResolutionCandidate:
    return ResolutionCandidate(
        candidate_id=f"recent_artifact:{suffix}:{event.event_id}",
        session_id=event.session_id,
        source="recent_artifact",
        content_type=content_type,
        summary=summary,
        content=event.content,
        score=score,
        source_turn_id=str(event.turn_id),
        source_event_ids=[event.event_id],
        evidence=evidence or [summary],
        metadata=metadata or {},
    )


def _extract_option_candidates(event: ContextEvent) -> list[ResolutionCandidate]:
    out: list[ResolutionCandidate] = []
    for pattern, locale in _OPTION_PATTERNS:
        for match in pattern.finditer(event.content):
            if locale == "zh":
                ordinal_text = match.group(2)
            elif locale == "numeric":
                ordinal_text = match.group(2)
            else:
                ordinal_text = match.group(2).lower()
            ordinal = int(ordinal_text) if locale == "numeric" else _ORDINAL_MAP.get(ordinal_text)
            snippet = _normalize_summary(event.content)
            out.append(
                _candidate(
                    event,
                    suffix=f"option-{ordinal or ordinal_text}",
                    content_type="numbered_option",
                    summary=snippet,
                    score=0.9,
                    evidence=[match.group(0), snippet],
                    metadata={"ordinal": ordinal, "ordinal_text": ordinal_text},
                )
            )
    return out


class RecentWindowManager:
    def build_snapshot(
        self,
        session_id: str,
        recent_events: list[ContextEvent],
        token_budget: int | None = None,
        host_artifacts: list[ResolutionCandidate] | None = None,
    ) -> RecentWindowSnapshot:
        session_events = [event for event in recent_events if event.session_id == session_id]
        visible_events = filter_candidate_events(session_events)
        return RecentWindowSnapshot(
            session_id=session_id,
            events=session_events,
            token_budget=token_budget,
            visible_event_ids=[event.event_id for event in visible_events],
            host_artifacts=list(host_artifacts or []),
            metadata={"event_count": len(session_events), "visible_event_count": len(visible_events)},
        )


class RecentArtifactExtractor:
    def extract(self, snapshot: RecentWindowSnapshot) -> list[ResolutionCandidate]:
        visible_events = filter_candidate_events(snapshot.events)
        candidates: list[ResolutionCandidate] = list(snapshot.host_artifacts)
        seen: set[tuple[str, str, str]] = {
            (candidate.source, candidate.content_type, candidate.candidate_id) for candidate in candidates
        }

        for event in visible_events:
            raw_candidate = context_event_to_resolution_candidate(event, score=0.55)
            key = (raw_candidate.source, raw_candidate.content_type, raw_candidate.candidate_id)
            if key not in seen:
                candidates.append(raw_candidate)
                seen.add(key)

            derived: list[ResolutionCandidate] = []
            derived.extend(_extract_option_candidates(event))

            if event.event_type == "tool_result":
                derived.append(
                    _candidate(
                        event,
                        suffix="tool",
                        content_type="tool_result",
                        summary=_normalize_summary(event.content),
                        score=0.95,
                        evidence=[event.source or "tool_result", _normalize_summary(event.content)],
                        metadata={"source": event.source, "source_ref": event.source_ref},
                    )
                )
            if _looks_like_code_or_command(event.content):
                derived.append(
                    _candidate(
                        event,
                        suffix="command",
                        content_type="command" if event.event_type != "assistant_message" else "code_block",
                        summary=_normalize_summary(event.content),
                        score=0.92,
                    )
                )
            if _looks_like_document_reference(event.content):
                derived.append(
                    _candidate(
                        event,
                        suffix="document",
                        content_type="document_reference",
                        summary=_normalize_summary(event.content),
                        score=0.78,
                    )
                )
            if _looks_like_decision(event.content):
                derived.append(
                    _candidate(
                        event,
                        suffix="decision",
                        content_type="decision",
                        summary=_normalize_summary(event.content),
                        score=0.8,
                    )
                )

            for candidate in derived:
                derived_key = (candidate.source, candidate.content_type, candidate.candidate_id)
                if derived_key in seen:
                    continue
                candidates.append(candidate)
                seen.add(derived_key)

        return candidates
