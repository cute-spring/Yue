from __future__ import annotations

import re
from typing import Protocol

from app.modules.session_context.models import (
    ContextResolutionAction,
    ContextResolutionConfig,
    ContextResolutionDecision,
    ContextResolutionReason,
    RecentWindowSnapshot,
    ResolutionCandidate,
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


_FORMAT_TERMS = ("csv", "json", "表格", "表格版", "格式", "版本")
_COMMAND_HINT_TERMS = ("命令", "command", "powershell", "sql", "脚本", "code", "批量", "导出")
_TOOL_HINT_TERMS = ("权限", "结果", "role", "tool", "lookup", "查一下", "查", "查询")
_DOCUMENT_HINT_TERMS = ("文档", "document", "link", "链接")
_IMPLICIT_STRONG_PHRASES = (
    "批量版本",
    "按同样方式",
    "也这样做",
    "同样方式",
    "同样结构",
    "同样格式",
    "csv 版本",
    "json 格式",
    "表格版",
    "另一个也",
)
_IMPLICIT_ACTION_TERMS = (
    "导出",
    "改成",
    "套用",
    "继续处理",
    "处理",
    "改写",
    "生成同样",
    "查一下",
    "查",
    "查询",
)


def _detect_implicit_reference_signals(current_input: str) -> list[str]:
    lowered = _normalize(current_input)
    signals: list[str] = []

    if _contains_any(lowered, _IMPLICIT_STRONG_PHRASES):
        signals.append("implicit:strong_phrase")
    if "也" in current_input:
        signals.append("implicit:also")
    if "同样" in current_input:
        signals.append("implicit:same_way")
    if _contains_any(lowered, _FORMAT_TERMS):
        signals.append("implicit:format_carryover")
    if _contains_any(lowered, _IMPLICIT_ACTION_TERMS):
        signals.append("implicit:action_carryover")
    if re.search(r"\b[A-Z][A-Za-z0-9_-]*\b", current_input) and _contains_any(lowered, ("呢", "也", "处理", "查", "导出")):
        signals.append("implicit:entity_carryover")

    deduped: list[str] = []
    for signal in signals:
        if signal not in deduped:
            deduped.append(signal)
    return deduped


def _implicit_reference_detected(
    current_input: str,
    explicit_signals: list[str],
    implicit_signals: list[str],
) -> bool:
    if explicit_signals:
        return False
    if "implicit:strong_phrase" in implicit_signals:
        return True
    if "implicit:entity_carryover" in implicit_signals and "呢" in current_input:
        return True
    return len(implicit_signals) >= 2


def _reference_signal_strength(explicit_signals: list[str], implicit_signals: list[str]) -> str:
    if explicit_signals:
        return "explicit"
    if "implicit:strong_phrase" in implicit_signals:
        return "implicit_strong"
    if implicit_signals:
        return "implicit"
    return "none"


def _build_debug(
    *,
    explicit_signals: list[str],
    implicit_signals: list[str],
    implicit_detected: bool,
    recent_candidates: list[ResolutionCandidate],
    ambiguity_debug: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "explicit_reference_signals": list(explicit_signals),
        "implicit_reference_detected": implicit_detected,
        "implicit_reference_signals": list(implicit_signals),
        "reference_signal_strength": _reference_signal_strength(explicit_signals, implicit_signals),
        "ambiguity_debug": dict(ambiguity_debug or {}),
        "recent_candidate_ids": [candidate.candidate_id for candidate in recent_candidates],
    }


def _extract_ordinal(text: str) -> int | None:
    patterns = (
        (r"第\s*([一二三四五六七八九十])", {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}),
        (r"第\s*([1-9][0-9]*)", None),
        (r"方案\s*([1-9][0-9]*)", None),
        (r"\boption\s+([1-9][0-9]*)\b", None),
        (r"\b(first|second|third|fourth|fifth)\b", {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}),
    )
    for pattern, mapping in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if mapping is None:
                return int(match.group(1))
            return mapping.get(match.group(1).lower() if match.group(1).isascii() else match.group(1))
    return None


class SemanticAdjudicator(Protocol):
    def adjudicate(
        self,
        current_input: str,
        plausible_candidates: list[ResolutionCandidate],
        config: ContextResolutionConfig,
    ) -> ContextResolutionDecision | None: ...


class HeuristicSemanticAdjudicator:
    def adjudicate(
        self,
        current_input: str,
        plausible_candidates: list[ResolutionCandidate],
        config: ContextResolutionConfig,
    ) -> ContextResolutionDecision | None:
        lowered = _normalize(current_input)
        if "后一个" in lowered:
            semantic_target = plausible_candidates[-1]
            return ContextResolutionDecision(
                action=(
                    ContextResolutionAction.USE_RECENT_ARTIFACT
                    if semantic_target.source == "recent_artifact"
                    else ContextResolutionAction.USE_RECENT_CONTEXT
                ),
                reason=_reason_for_target(current_input, semantic_target),
                confidence=min(0.9, max(0.6, float(semantic_target.score))),
                matched_signals=[],
                resolved_target=semantic_target,
                candidate_count=len(plausible_candidates),
                should_retrieve=False,
                should_rewrite=True,
                rewritten_query=_build_rewrite(current_input, semantic_target),
                needs_semantic_model=True,
                debug={
                    "semantic_mode": "heuristic_adjudication",
                    "semantic_adjudicator": self.__class__.__name__,
                    "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible_candidates],
                },
            )
        if "前一个" in lowered and len(plausible_candidates) >= 2:
            semantic_target = plausible_candidates[-2]
            return ContextResolutionDecision(
                action=(
                    ContextResolutionAction.USE_RECENT_ARTIFACT
                    if semantic_target.source == "recent_artifact"
                    else ContextResolutionAction.USE_RECENT_CONTEXT
                ),
                reason=_reason_for_target(current_input, semantic_target),
                confidence=min(0.9, max(0.6, float(semantic_target.score))),
                matched_signals=[],
                resolved_target=semantic_target,
                candidate_count=len(plausible_candidates),
                should_retrieve=False,
                should_rewrite=True,
                rewritten_query=_build_rewrite(current_input, semantic_target),
                needs_semantic_model=True,
                debug={
                    "semantic_mode": "heuristic_adjudication",
                    "semantic_adjudicator": self.__class__.__name__,
                    "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible_candidates],
                },
            )

        typed_pools = (
            ("命令", "command", "powershell", "sql", "脚本", "code"),
            ("权限", "结果", "链接", "tool", "role", "lookup"),
            ("文档", "document", "link", "链接"),
        )
        for pool in typed_pools:
            if any(term in lowered for term in pool):
                typed = _resolve_recent_target(current_input, plausible_candidates)
                if typed is not None:
                    return ContextResolutionDecision(
                        action=(
                            ContextResolutionAction.USE_RECENT_ARTIFACT
                            if typed.source == "recent_artifact"
                            else ContextResolutionAction.USE_RECENT_CONTEXT
                        ),
                        reason=_reason_for_target(current_input, typed),
                        confidence=min(0.9, max(0.6, float(typed.score))),
                        matched_signals=[],
                        resolved_target=typed,
                        candidate_count=len(plausible_candidates),
                        should_retrieve=False,
                        should_rewrite=True,
                        rewritten_query=_build_rewrite(current_input, typed),
                        needs_semantic_model=True,
                        debug={
                            "semantic_mode": "heuristic_adjudication",
                            "semantic_adjudicator": self.__class__.__name__,
                            "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible_candidates],
                        },
                    )
        _ = config
        return None


def _reason_for_target(current_input: str, target: ResolutionCandidate) -> ContextResolutionReason:
    lowered = _normalize(current_input)
    if target.content_type in {"command", "code_block"}:
        return ContextResolutionReason.CODE_OR_COMMAND_REFERENCE
    if target.content_type == "tool_result":
        return ContextResolutionReason.TOOL_RESULT_REFERENCE
    if target.content_type == "document_reference":
        return ContextResolutionReason.DOCUMENT_REFERENCE
    if target.content_type == "numbered_option":
        return ContextResolutionReason.ORDINAL_REFERENCE
    if any(term in lowered for term in ("改成", "modify", "change")):
        return ContextResolutionReason.MODIFY_PRIOR_OUTPUT
    if any(term in lowered for term in ("继续", "continue")):
        return ContextResolutionReason.CONTINUATION_REFERENCE
    return ContextResolutionReason.RECENT_CONTEXT_SUFFICIENT


def _build_rewrite(current_input: str, target: ResolutionCandidate) -> str | None:
    if target.content_type == "numbered_option" and target.metadata.get("ordinal") is not None:
        return f"Refer to option {target.metadata['ordinal']} from the recent session context: {current_input}"
    if target.content_type in {"command", "code_block"}:
        return f"Use the recent command or code artifact as the target of this request: {current_input}"
    if target.content_type == "tool_result":
        return f"Use the recent tool result as the target of this request: {current_input}"
    return None


def _resolve_recent_target(
    current_input: str,
    recent_candidates: list[ResolutionCandidate],
    *,
    allow_implicit: bool = False,
    implicit_signals: list[str] | None = None,
) -> ResolutionCandidate | None:
    lowered = _normalize(current_input)
    ordinal = _extract_ordinal(current_input)
    implicit_signals = implicit_signals or []
    domain_specific_request = any(
        term in lowered
        for term in (
            *_COMMAND_HINT_TERMS,
            *_TOOL_HINT_TERMS,
            *_DOCUMENT_HINT_TERMS,
        )
    )

    if ordinal is not None:
        ordinal_matches = [
            candidate
            for candidate in recent_candidates
            if candidate.metadata.get("ordinal") == ordinal
        ]
        if ordinal_matches:
            return sorted(ordinal_matches, key=lambda candidate: candidate.score, reverse=True)[0]
        # If the user explicitly refers to an ordinal target but we cannot ground
        # that ordinal in recent structured artifacts, prefer escalation to
        # mid-session retrieval over guessing from a plain recent message.
        return None

    typed_candidates: list[ResolutionCandidate] = []
    if _contains_any(lowered, _COMMAND_HINT_TERMS) or (
        allow_implicit and any(signal in implicit_signals for signal in ("implicit:format_carryover", "implicit:action_carryover"))
    ):
        typed_candidates = [
            candidate
            for candidate in recent_candidates
            if candidate.content_type in {"command", "code_block"} or "command" in candidate.content_type
        ]
    elif _contains_any(lowered, _TOOL_HINT_TERMS) or (
        allow_implicit and (
            "implicit:entity_carryover" in implicit_signals or ("implicit:also" in implicit_signals and "implicit:action_carryover" in implicit_signals)
        )
    ):
        typed_candidates = [
            candidate
            for candidate in recent_candidates
            if candidate.content_type == "tool_result"
        ]
    elif _contains_any(lowered, _DOCUMENT_HINT_TERMS):
        typed_candidates = [
            candidate for candidate in recent_candidates if candidate.content_type == "document_reference"
        ]

    if typed_candidates:
        return sorted(typed_candidates, key=lambda candidate: candidate.score, reverse=True)[0]

    if not domain_specific_request and any(
        term in lowered for term in ("继续", "那个", "这个", "it", "that", "this", "按刚才", "改成")
    ):
        recent_artifacts = [candidate for candidate in recent_candidates if candidate.source == "recent_artifact"]
        if recent_artifacts:
            return sorted(recent_artifacts, key=lambda candidate: candidate.score, reverse=True)[0]
        grounded_recent_candidates = [
            candidate
            for candidate in recent_candidates
            if candidate.content_type not in {"assistant_message", "user_message", "tool_call"}
        ]
        if grounded_recent_candidates:
            return sorted(
                grounded_recent_candidates,
                key=lambda candidate: int(candidate.source_turn_id or "0"),
                reverse=True,
            )[0]

    if allow_implicit:
        recent_artifacts = [candidate for candidate in recent_candidates if candidate.source == "recent_artifact"]
        strong_artifacts = [
            candidate
            for candidate in recent_artifacts
            if candidate.content_type in {"tool_result", "document_reference", "decision", "command", "code_block"}
        ]
        if len(strong_artifacts) == 1:
            return strong_artifacts[0]
        if len(strong_artifacts) > 1 and ("implicit:strong_phrase" in implicit_signals or "implicit:same_way" in implicit_signals):
            return None

    return None


def _build_retrieval_rewrite(current_input: str) -> str:
    lowered = _normalize(current_input)
    hints: list[str] = []
    if any(term in lowered for term in ("链接", "link", "document", "文档")):
        hints.extend(["link", "document"])
    if any(term in lowered for term in ("命令", "command", "脚本", "sql", "code")):
        hints.extend(["command", "script"])
    if any(term in lowered for term in ("权限", "结果", "role", "tool")):
        hints.extend(["roles", "result"])
    if any(term in lowered for term in ("方案", "option", "第二", "first", "second")):
        hints.extend(["option", "plan"])
    joined_hints = " ".join(hints)
    if not joined_hints:
        return current_input
    return f"{joined_hints} {current_input}"


class ContextResolutionEngine:
    _GREETING_TERMS = ("你好", "hello", "hi", "hey")
    _DEICTIC_TERMS = ("那个", "这个", "it", "that", "this", "另一个", "后一个", "前一个", "上面的")
    _REFERENCE_TERMS = (
        "earlier",
        "before",
        "previous",
        "last time",
        "remember",
        "what did we",
        "刚才",
        "之前",
        "前面",
        "上面",
        "那个",
        "这个",
        "继续",
        "继续按",
        "按刚才",
        "后一个",
        "前一个",
    )

    def __init__(self, semantic_adjudicator: SemanticAdjudicator | None = None) -> None:
        self._semantic_adjudicator = semantic_adjudicator or HeuristicSemanticAdjudicator()

    def decide(
        self,
        current_input: str,
        snapshot: RecentWindowSnapshot,
        recent_candidates: list[ResolutionCandidate],
        config: ContextResolutionConfig,
    ) -> ContextResolutionDecision:
        lowered = _normalize(current_input)
        explicit_signals = [term for term in self._REFERENCE_TERMS if term in lowered]
        implicit_signals = _detect_implicit_reference_signals(current_input)
        implicit_detected = _implicit_reference_detected(current_input, explicit_signals, implicit_signals)
        matched_signals = list(explicit_signals or implicit_signals)
        base_debug = _build_debug(
            explicit_signals=explicit_signals,
            implicit_signals=implicit_signals,
            implicit_detected=implicit_detected,
            recent_candidates=recent_candidates,
        )

        if not explicit_signals and not implicit_detected:
            if any(term in lowered for term in self._GREETING_TERMS):
                return ContextResolutionDecision(
                    action=ContextResolutionAction.NO_CONTEXT_NEEDED,
                    reason=ContextResolutionReason.GREETING_OR_SMALLTALK,
                    confidence=0.95,
                    matched_signals=[],
                    debug=base_debug,
                )
            return ContextResolutionDecision(
                action=ContextResolutionAction.NO_CONTEXT_NEEDED,
                reason=ContextResolutionReason.NO_REFERENCE_SIGNAL,
                confidence=0.85,
                matched_signals=[],
                debug=base_debug,
            )

        if config.enable_semantic_adjudication:
            semantic_decision = self._maybe_run_semantic_adjudication(
                current_input,
                recent_candidates,
                config,
                matched_signals,
                implicit_detected=implicit_detected,
                base_debug=base_debug,
            )
            if semantic_decision is not None:
                return semantic_decision

        target = _resolve_recent_target(
            current_input,
            recent_candidates,
            allow_implicit=implicit_detected,
            implicit_signals=implicit_signals,
        )
        if target is not None:
            reason = _reason_for_target(current_input, target)
            action = (
                ContextResolutionAction.USE_RECENT_ARTIFACT
                if target.source == "recent_artifact"
                else ContextResolutionAction.USE_RECENT_CONTEXT
            )
            return ContextResolutionDecision(
                action=action,
                reason=reason,
                confidence=min(0.96, max(0.72, float(target.score))),
                matched_signals=matched_signals,
                resolved_target=target,
                candidate_count=1,
                should_retrieve=False,
                should_rewrite=action == ContextResolutionAction.USE_RECENT_ARTIFACT,
                rewritten_query=_build_rewrite(current_input, target),
                debug=base_debug,
            )

        ambiguity_debug = {
            "recent_candidate_ids": [candidate.candidate_id for candidate in recent_candidates],
            "implicit_reference_detected": implicit_detected,
        }
        return ContextResolutionDecision(
            action=ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY,
            reason=ContextResolutionReason.RECENT_CONTEXT_INSUFFICIENT,
            confidence=0.7,
            matched_signals=matched_signals,
            candidate_count=len(recent_candidates),
            should_retrieve=True,
            should_rewrite=True,
            rewritten_query=_build_retrieval_rewrite(current_input),
            debug=_build_debug(
                explicit_signals=explicit_signals,
                implicit_signals=implicit_signals,
                implicit_detected=implicit_detected,
                recent_candidates=recent_candidates,
                ambiguity_debug=ambiguity_debug,
            ),
        )

    def _maybe_run_semantic_adjudication(
        self,
        current_input: str,
        recent_candidates: list[ResolutionCandidate],
        config: ContextResolutionConfig,
        matched_signals: list[str],
        *,
        implicit_detected: bool,
        base_debug: dict[str, object],
    ) -> ContextResolutionDecision | None:
        lowered = _normalize(current_input)
        if not any(term in lowered for term in self._DEICTIC_TERMS) and not implicit_detected:
            return None

        plausible = self._plausible_recent_targets(recent_candidates)
        if len(plausible) < 2:
            return None

        semantic_decision = self._semantic_adjudicator.adjudicate(current_input, plausible, config)
        if semantic_decision is not None:
            semantic_decision.matched_signals = list(matched_signals)
            semantic_decision.candidate_count = semantic_decision.candidate_count or len(plausible)
            semantic_decision.needs_semantic_model = True
            semantic_debug = {**base_debug, **dict(semantic_decision.debug)}
            semantic_debug.setdefault("semantic_invoked", True)
            semantic_debug.setdefault("semantic_adjudicator", self._semantic_adjudicator.__class__.__name__)
            semantic_debug.setdefault("plausible_candidate_ids", [candidate.candidate_id for candidate in plausible])
            semantic_debug.setdefault("semantic_fallback_used", False)
            semantic_debug["ambiguity_debug"] = {
                "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible],
                "semantic_fallback_used": False,
            }
            semantic_decision.debug = semantic_debug
            return semantic_decision

        return self._deterministic_semantic_fallback(
            plausible,
            config,
            matched_signals,
            base_debug=base_debug,
        )

    def _deterministic_semantic_fallback(
        self,
        plausible: list[ResolutionCandidate],
        config: ContextResolutionConfig,
        matched_signals: list[str],
        *,
        base_debug: dict[str, object],
    ) -> ContextResolutionDecision:
        debug = {
            **base_debug,
            "semantic_mode": "deterministic_fallback",
            "semantic_invoked": True,
            "semantic_adjudicator": self._semantic_adjudicator.__class__.__name__,
            "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible],
            "semantic_fallback_used": True,
            "ambiguity_debug": {
                "plausible_candidate_ids": [candidate.candidate_id for candidate in plausible],
                "semantic_fallback_used": True,
            },
        }
        if config.prefer_recall_when_uncertain:
            debug["fallback_action"] = ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY.value
            debug["ambiguity_debug"]["fallback_action"] = ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY.value
            return ContextResolutionDecision(
                action=ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY,
                reason=ContextResolutionReason.LOW_CONFIDENCE_AMBIGUITY,
                confidence=0.55,
                matched_signals=list(matched_signals),
                candidate_count=len(plausible),
                should_retrieve=True,
                should_rewrite=False,
                needs_semantic_model=True,
                debug=debug,
            )

        debug["fallback_action"] = ContextResolutionAction.ASK_CLARIFYING_QUESTION.value
        debug["ambiguity_debug"]["fallback_action"] = ContextResolutionAction.ASK_CLARIFYING_QUESTION.value
        return ContextResolutionDecision(
            action=ContextResolutionAction.ASK_CLARIFYING_QUESTION,
            reason=ContextResolutionReason.MULTIPLE_CANDIDATES,
            confidence=0.5,
            matched_signals=list(matched_signals),
            candidate_count=len(plausible),
            should_retrieve=False,
            should_rewrite=False,
            needs_semantic_model=True,
            debug=debug,
        )

    def _plausible_recent_targets(
        self,
        recent_candidates: list[ResolutionCandidate],
    ) -> list[ResolutionCandidate]:
        candidates = [
            candidate
            for candidate in recent_candidates
            if candidate.source in {"recent_artifact", "recent_window"}
            and candidate.content_type not in {"assistant_message", "user_message", "tool_call"}
        ]
        if candidates:
            return sorted(candidates, key=lambda candidate: (int(candidate.source_turn_id or "0"), candidate.score))
        return sorted(
            recent_candidates,
            key=lambda candidate: (int(candidate.source_turn_id or "0"), candidate.score),
        )


class ContextSourceRouter:
    def select_candidates(
        self,
        decision: ContextResolutionDecision,
        recent_candidates: list[ResolutionCandidate],
        retrieved_candidates: list[ResolutionCandidate],
    ) -> list[ResolutionCandidate]:
        if decision.action == ContextResolutionAction.NO_CONTEXT_NEEDED:
            return []

        selected: list[ResolutionCandidate] = []
        if decision.resolved_target is not None:
            selected.append(decision.resolved_target)

        if decision.action == ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY:
            pool = sorted(retrieved_candidates, key=lambda candidate: candidate.score, reverse=True)
            numbered_option_pool = [
                candidate for candidate in pool if candidate.content_type == "numbered_option"
            ]
            if numbered_option_pool:
                selected.extend(numbered_option_pool[:1])
            else:
                selected.extend(pool[:3])
        elif decision.action == ContextResolutionAction.USE_RECENT_ARTIFACT:
            pool = [
                candidate
                for candidate in recent_candidates
                if candidate.source == "recent_artifact"
                and (decision.resolved_target is None or candidate.candidate_id != decision.resolved_target.candidate_id)
            ]
            selected.extend(sorted(pool, key=lambda candidate: candidate.score, reverse=True)[:2])
        elif decision.action == ContextResolutionAction.USE_RECENT_CONTEXT:
            pool = [
                candidate
                for candidate in recent_candidates
                if candidate.source == "recent_window"
                and (decision.resolved_target is None or candidate.candidate_id != decision.resolved_target.candidate_id)
            ]
            selected.extend(sorted(pool, key=lambda candidate: candidate.score, reverse=True)[:2])

        deduped: list[ResolutionCandidate] = []
        seen: set[str] = set()
        for candidate in selected:
            if candidate.candidate_id in seen:
                continue
            deduped.append(candidate)
            seen.add(candidate.candidate_id)
        return deduped
