from __future__ import annotations

from app.modules.session_context.models import ContextEvent

from .extractor import LongTermCandidateExtractor


def filter_candidate_events(
    events: list[ContextEvent],
    extractor: LongTermCandidateExtractor | None = None,
) -> list[ContextEvent]:
    active_extractor = extractor or LongTermCandidateExtractor()
    filtered: list[ContextEvent] = []
    for event in events:
        if active_extractor.extract_candidates(session_id=event.session_id, events=[event]):
            continue
        filtered.append(event)
    return filtered
