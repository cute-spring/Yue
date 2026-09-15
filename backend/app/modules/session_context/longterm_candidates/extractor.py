from __future__ import annotations

from app.modules.session_context.models import ContextEvent, LongTermCandidate


class LongTermCandidateExtractor:
    def __init__(
        self,
        trigger_phrases: tuple[str, ...] = ("以后", "下次", "默认", "请记住", "记住", "一直", "优先"),
        filter_phrases: tuple[str, ...] = ("这次", "临时", "先假设", "暂时", "今天", "测试", "不确定"),
    ) -> None:
        self._trigger_phrases = trigger_phrases
        self._filter_phrases = filter_phrases

    def extract_candidates(
        self,
        session_id: str,
        events: list[ContextEvent],
    ) -> list[LongTermCandidate]:
        candidates: list[LongTermCandidate] = []
        for event in events:
            if event.session_id != session_id or event.event_type != "user_message":
                continue
            if not self._should_extract(event.content):
                continue
            candidates.append(
                LongTermCandidate(
                    candidate_id=f"cand-{session_id}-{event.event_id}",
                    subject_scope="user",
                    subject_id=None,
                    candidate_type="preference",
                    content=event.content,
                    confidence=0.8,
                    source_session_id=session_id,
                    source_event_ids=[event.event_id],
                    status="candidate",
                )
            )
        return candidates

    def _should_extract(self, content: str) -> bool:
        return any(phrase in content for phrase in self._trigger_phrases) and not any(
            phrase in content for phrase in self._filter_phrases
        )
