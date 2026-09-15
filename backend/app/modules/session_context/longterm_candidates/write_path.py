from __future__ import annotations

from app.modules.session_context.models import ContextEvent, LongTermCandidate
from app.modules.session_context.stores.base import ContextEventStore, LongTermCandidateStore

from .extractor import LongTermCandidateExtractor


def append_event_and_collect_long_term_candidates(
    event_store: ContextEventStore,
    candidate_store: LongTermCandidateStore,
    event: ContextEvent,
    extractor: LongTermCandidateExtractor | None = None,
) -> list[LongTermCandidate]:
    event_store.append_event(event)

    active_extractor = extractor or LongTermCandidateExtractor()
    candidates = active_extractor.extract_candidates(session_id=event.session_id, events=[event])
    for candidate in candidates:
        candidate_store.upsert_candidate(candidate)
    return candidates
