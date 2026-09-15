from __future__ import annotations

from app.modules.session_context.models import ContextEvent


class NeedRetrieveGate:
    _TRIGGERS = (
        "earlier",
        "before",
        "previous",
        "last time",
        "remind",
        "remember",
        "what did we",
        "刚才",
        "之前",
        "前面",
    )

    def should_retrieve(self, current_input: str, recent_events: list[ContextEvent]) -> bool:
        _ = recent_events
        lowered = current_input.lower()
        return any(trigger in lowered for trigger in self._TRIGGERS)
