from __future__ import annotations

from app.modules.session_context.models import (
    ContextEvent,
    ContextResolutionConfig,
    SessionContextPlan,
    retrieved_chunk_to_resolution_candidate,
)
from app.modules.session_context.retrieval.retriever import ContextRetriever

from .composition import PromptContextComposer
from .recent import RecentArtifactExtractor, RecentWindowManager
from .resolution import ContextResolutionEngine, ContextSourceRouter


def _candidate_telemetry(candidate: object) -> dict[str, object]:
    if not hasattr(candidate, "candidate_id"):
        return {}
    return {
        "candidate_id": getattr(candidate, "candidate_id", None),
        "source": getattr(candidate, "source", None),
        "content_type": getattr(candidate, "content_type", None),
        "source_turn_id": getattr(candidate, "source_turn_id", None),
        "score": getattr(candidate, "score", None),
    }


class SessionContextManager:
    def __init__(
        self,
        recent_window_manager: RecentWindowManager | None = None,
        recent_artifact_extractor: RecentArtifactExtractor | None = None,
        context_resolution_engine: ContextResolutionEngine | None = None,
        context_retriever: ContextRetriever | None = None,
        context_source_router: ContextSourceRouter | None = None,
        prompt_context_composer: PromptContextComposer | None = None,
    ) -> None:
        self._recent_window_manager = recent_window_manager or RecentWindowManager()
        self._recent_artifact_extractor = recent_artifact_extractor or RecentArtifactExtractor()
        self._context_resolution_engine = context_resolution_engine or ContextResolutionEngine()
        self._context_retriever = context_retriever or ContextRetriever()
        self._context_source_router = context_source_router or ContextSourceRouter()
        self._prompt_context_composer = prompt_context_composer or PromptContextComposer()

    def resolve(
        self,
        session_id: str,
        current_input: str,
        recent_events: list[ContextEvent],
        config: ContextResolutionConfig,
        current_tool_results: list[str | ContextEvent] | None = None,
    ) -> SessionContextPlan:
        snapshot = self._recent_window_manager.build_snapshot(
            session_id=session_id,
            recent_events=recent_events,
            token_budget=config.recent_window_token_budget,
        )
        recent_candidates = (
            self._recent_artifact_extractor.extract(snapshot)
            if config.include_recent_structured_artifacts
            else []
        )
        decision = self._context_resolution_engine.decide(current_input, snapshot, recent_candidates, config)

        retrieval_query = decision.rewritten_query or current_input
        retrieval_blocked_by_policy = (
            decision.should_retrieve and not config.boundary_policy.allows_manager_mid_session_retrieval()
        )
        retrieved_chunks = (
            self._context_retriever.retrieve(
                session_id=session_id,
                current_input=retrieval_query,
                recent_events=recent_events,
                top_k=config.top_k,
                budget_tokens=config.retrieval_token_budget,
            )
            if decision.should_retrieve and not retrieval_blocked_by_policy
            else []
        )
        retrieved_candidates = [retrieved_chunk_to_resolution_candidate(hit) for hit in retrieved_chunks]
        selected_candidates = self._context_source_router.select_candidates(
            decision=decision,
            recent_candidates=recent_candidates,
            retrieved_candidates=retrieved_candidates,
        )
        prompt_blocks = self._prompt_context_composer.compose(
            current_input=current_input,
            snapshot=snapshot,
            decision=decision,
            selected_candidates=selected_candidates,
            retrieved_chunks=retrieved_chunks,
            current_tool_results=current_tool_results or [],
            token_budget=(config.recent_window_token_budget or 800),
            selected_evidence_only=config.selected_evidence_only,
            include_full_recent_conversation=config.include_full_recent_conversation,
            include_current_tool_results=config.include_current_tool_results,
        )
        selected_candidate_telemetry = [_candidate_telemetry(candidate) for candidate in selected_candidates]
        return SessionContextPlan(
            decision=decision,
            recent_window=snapshot,
            recent_candidates=recent_candidates,
            retrieved_candidates=retrieved_candidates,
            selected_candidates=selected_candidates,
            retrieved_chunks=retrieved_chunks,
            prompt_blocks=prompt_blocks,
            telemetry={
                "recent_candidate_count": len(recent_candidates),
                "retrieved_candidate_count": len(retrieved_candidates),
                "retrieved_chunk_count": len(retrieved_chunks),
                "selected_candidate_count": len(selected_candidates),
                "prompt_block_count": len(prompt_blocks),
                "action": decision.action.value,
                "reason": decision.reason.value,
                "confidence": decision.confidence,
                "matched_signals": list(decision.matched_signals),
                "should_retrieve": decision.should_retrieve,
                "mid_session_retrieval_blocked_by_policy": retrieval_blocked_by_policy,
                "should_rewrite": decision.should_rewrite,
                "retrieval_query": retrieval_query if decision.should_retrieve else None,
                "rewritten_query": decision.rewritten_query,
                "used_rewritten_query": bool(
                    decision.rewritten_query and decision.rewritten_query != current_input
                ),
                "retrieval_boundary_policy": config.boundary_policy.to_dict(),
                "selected_candidate_ids": [candidate.candidate_id for candidate in selected_candidates],
                "selected_candidate_sources": [candidate.source for candidate in selected_candidates],
                "selected_candidate_content_types": [
                    candidate.content_type for candidate in selected_candidates
                ],
                "selected_candidates": selected_candidate_telemetry,
                "retrieved_chunk_ids": [hit.chunk.chunk_id for hit in retrieved_chunks],
                "prompt_block_names": [block.name for block in prompt_blocks],
                "semantic_model_invoked": bool(decision.debug.get("semantic_invoked", False)),
                "semantic_debug": dict(decision.debug),
                "implicit_reference_detected": bool(
                    decision.debug.get("implicit_reference_detected", False)
                ),
                "implicit_reference_signals": list(
                    decision.debug.get("implicit_reference_signals", [])
                ),
                "reference_signal_strength": decision.debug.get("reference_signal_strength", "none"),
                "explicit_reference_signals": list(
                    decision.debug.get("explicit_reference_signals", [])
                ),
                "ambiguity_debug": dict(decision.debug.get("ambiguity_debug", {})),
            },
        )

    def export_prompt_context(self, plan: SessionContextPlan):
        rendered_text = "\n\n".join(
            f"[{block.name}]\n{block.content}" for block in plan.prompt_blocks
        )
        return self._prompt_context_composer.export(
            plan.prompt_blocks,
            selected_candidates=plan.selected_candidates,
            rendered_text=rendered_text,
        )
