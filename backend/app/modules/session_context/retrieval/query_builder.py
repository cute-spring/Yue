from __future__ import annotations

from app.modules.session_context.longterm_candidates import filter_candidate_events
from app.modules.session_context.models import ContextEvent


def build_query(current_input: str, recent_events: list[ContextEvent], max_recent: int = 4) -> str:
    visible_recent_events = filter_candidate_events(recent_events)
    snippets = [event.content.strip() for event in visible_recent_events[-max_recent:] if event.content.strip()]
    snippets.append(f"[QUESTION] {current_input.strip()}")
    return " | ".join(part for part in snippets if part)
