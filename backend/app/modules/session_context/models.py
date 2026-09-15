from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from typing import Any, TypeVar


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Expected ISO datetime string or datetime, got {type(value)!r}")


def _datetime_to_iso(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise TypeError(f"Expected datetime, got {type(value)!r}")
    return value.isoformat()


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_list(name: str, value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _coerce_enum(enum_cls: type[Enum], value: Any) -> Enum:
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {enum_cls.__name__}: {value!r}") from exc


T = TypeVar("T")


@dataclass(eq=True)
class ContextEvent:
    event_id: str
    session_id: str
    turn_id: int
    event_type: str
    content: str
    source: str | None = None
    source_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.event_id = _require_string("event_id", self.event_id)
        self.session_id = _require_string("session_id", self.session_id)
        self.event_type = _require_string("event_type", self.event_type)
        self.content = _require_string("content", self.content)
        if not isinstance(self.turn_id, int):
            raise ValueError("turn_id must be an integer")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")
        self.created_at = _parse_datetime(self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "event_type": self.event_type,
            "content": self.content,
            "source": self.source,
            "source_ref": self.source_ref,
            "metadata": self.metadata,
            "created_at": _datetime_to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["event_id", "session_id", "turn_id", "event_type", "content"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            turn_id=data["turn_id"],
            event_type=data["event_type"],
            content=data["content"],
            source=data.get("source"),
            source_ref=data.get("source_ref"),
            metadata=dict(data.get("metadata", {})),
            created_at=_parse_datetime(data.get("created_at", datetime.utcnow())),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class MemoryChunk:
    chunk_id: str
    session_id: str
    chunk_type: str
    content: str
    retrieval_text: str
    source_event_ids: list[str]
    start_turn_id: int
    end_turn_id: int
    priority: int
    memory_scope: str = "session"
    memory_type: str = "mid_term"
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.chunk_id = _require_string("chunk_id", self.chunk_id)
        self.session_id = _require_string("session_id", self.session_id)
        self.memory_scope = _require_string("memory_scope", self.memory_scope)
        self.memory_type = _require_string("memory_type", self.memory_type)
        self.chunk_type = _require_string("chunk_type", self.chunk_type)
        self.content = _require_string("content", self.content)
        self.retrieval_text = _require_string("retrieval_text", self.retrieval_text)
        if not isinstance(self.source_event_ids, list):
            raise ValueError("source_event_ids must be a list")
        if not isinstance(self.start_turn_id, int) or not isinstance(self.end_turn_id, int):
            raise ValueError("start_turn_id and end_turn_id must be integers")
        if not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")
        if self.ttl_seconds is not None and not isinstance(self.ttl_seconds, int):
            raise ValueError("ttl_seconds must be an integer or None")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")
        self.created_at = _parse_datetime(self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "memory_scope": self.memory_scope,
            "memory_type": self.memory_type,
            "chunk_type": self.chunk_type,
            "content": self.content,
            "retrieval_text": self.retrieval_text,
            "source_event_ids": list(self.source_event_ids),
            "start_turn_id": self.start_turn_id,
            "end_turn_id": self.end_turn_id,
            "priority": self.priority,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
            "created_at": _datetime_to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = [
            "chunk_id",
            "session_id",
            "chunk_type",
            "content",
            "retrieval_text",
            "source_event_ids",
            "start_turn_id",
            "end_turn_id",
            "priority",
        ]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            chunk_id=data["chunk_id"],
            session_id=data["session_id"],
            memory_scope=data.get("memory_scope", "session"),
            memory_type=data.get("memory_type", "mid_term"),
            chunk_type=data["chunk_type"],
            content=data["content"],
            retrieval_text=data["retrieval_text"],
            source_event_ids=list(data["source_event_ids"]),
            start_turn_id=data["start_turn_id"],
            end_turn_id=data["end_turn_id"],
            priority=data["priority"],
            ttl_seconds=data.get("ttl_seconds"),
            metadata=dict(data.get("metadata", {})),
            created_at=_parse_datetime(data.get("created_at", datetime.utcnow())),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class RetrievedChunk:
    chunk: MemoryChunk
    score: float
    rank: int
    retrieval_source: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.chunk, MemoryChunk):
            raise ValueError("chunk must be a MemoryChunk")
        if not isinstance(self.score, (float, int)):
            raise ValueError("score must be a number")
        if not isinstance(self.rank, int):
            raise ValueError("rank must be an integer")
        self.retrieval_source = _require_string("retrieval_source", self.retrieval_source)
        if self.reason is not None and not isinstance(self.reason, str):
            raise ValueError("reason must be a string or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": float(self.score),
            "rank": self.rank,
            "retrieval_source": self.retrieval_source,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["chunk", "score", "rank", "retrieval_source"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            chunk=MemoryChunk.from_dict(data["chunk"]),
            score=float(data["score"]),
            rank=data["rank"],
            retrieval_source=data["retrieval_source"],
            reason=data.get("reason"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class PromptContextBlock:
    name: str
    content: str
    priority: int
    token_count: int
    source_chunk_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = _require_string("name", self.name)
        self.content = _require_string("content", self.content)
        if not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")
        if not isinstance(self.token_count, int):
            raise ValueError("token_count must be an integer")
        if not isinstance(self.source_chunk_ids, list):
            raise ValueError("source_chunk_ids must be a list")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "content": self.content,
            "priority": self.priority,
            "token_count": self.token_count,
            "source_chunk_ids": list(self.source_chunk_ids),
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["name", "content", "priority", "token_count"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            name=data["name"],
            content=data["content"],
            priority=data["priority"],
            token_count=data["token_count"],
            source_chunk_ids=list(data.get("source_chunk_ids", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class RecentWindowSnapshot:
    session_id: str
    events: list[ContextEvent]
    token_budget: int | None = None
    visible_event_ids: list[str] = field(default_factory=list)
    host_artifacts: list["ResolutionCandidate"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.session_id = _require_string("session_id", self.session_id)
        _require_list("events", self.events)
        if not all(isinstance(event, ContextEvent) for event in self.events):
            raise ValueError("events must contain only ContextEvent instances")
        if self.token_budget is not None and not isinstance(self.token_budget, int):
            raise ValueError("token_budget must be an integer or None")
        _require_list("visible_event_ids", self.visible_event_ids)
        if not all(isinstance(event_id, str) for event_id in self.visible_event_ids):
            raise ValueError("visible_event_ids must contain only strings")
        _require_list("host_artifacts", self.host_artifacts)
        if not all(isinstance(candidate, ResolutionCandidate) for candidate in self.host_artifacts):
            raise ValueError("host_artifacts must contain only ResolutionCandidate instances")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "events": [event.to_dict() for event in self.events],
            "token_budget": self.token_budget,
            "visible_event_ids": list(self.visible_event_ids),
            "host_artifacts": [candidate.to_dict() for candidate in self.host_artifacts],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["session_id", "events"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            session_id=data["session_id"],
            events=[ContextEvent.from_dict(event) for event in data["events"]],
            token_budget=data.get("token_budget"),
            visible_event_ids=list(data.get("visible_event_ids", [])),
            host_artifacts=[
                ResolutionCandidate.from_dict(candidate) for candidate in data.get("host_artifacts", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class ResolutionCandidate:
    candidate_id: str
    session_id: str
    source: str
    content_type: str
    summary: str
    content: str
    score: float
    source_turn_id: str | None = None
    source_event_ids: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.candidate_id = _require_string("candidate_id", self.candidate_id)
        self.session_id = _require_string("session_id", self.session_id)
        self.source = _require_string("source", self.source)
        self.content_type = _require_string("content_type", self.content_type)
        self.summary = _require_string("summary", self.summary)
        self.content = _require_string("content", self.content)
        if not isinstance(self.score, (float, int)):
            raise ValueError("score must be a number")
        if self.source_turn_id is not None and not isinstance(self.source_turn_id, str):
            raise ValueError("source_turn_id must be a string or None")
        _require_list("source_event_ids", self.source_event_ids)
        if not all(isinstance(event_id, str) for event_id in self.source_event_ids):
            raise ValueError("source_event_ids must contain only strings")
        _require_list("evidence", self.evidence)
        if not all(isinstance(item, str) for item in self.evidence):
            raise ValueError("evidence must contain only strings")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "session_id": self.session_id,
            "source": self.source,
            "content_type": self.content_type,
            "summary": self.summary,
            "content": self.content,
            "score": float(self.score),
            "source_turn_id": self.source_turn_id,
            "source_event_ids": list(self.source_event_ids),
            "evidence": list(self.evidence),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["candidate_id", "session_id", "source", "content_type", "summary", "content", "score"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            candidate_id=data["candidate_id"],
            session_id=data["session_id"],
            source=data["source"],
            content_type=data["content_type"],
            summary=data["summary"],
            content=data["content"],
            score=float(data["score"]),
            source_turn_id=data.get("source_turn_id"),
            source_event_ids=list(data.get("source_event_ids", [])),
            evidence=list(data.get("evidence", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


class ContextResolutionAction(str, Enum):
    NO_CONTEXT_NEEDED = "no_context_needed"
    USE_RECENT_CONTEXT = "use_recent_context"
    USE_RECENT_ARTIFACT = "use_recent_artifact"
    RETRIEVE_MID_SESSION_MEMORY = "retrieve_mid_session_memory"
    SEMANTIC_CHECK_REQUIRED = "semantic_check_required"
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"


class ContextResolutionReason(str, Enum):
    NO_REFERENCE_SIGNAL = "no_reference_signal"
    GREETING_OR_SMALLTALK = "greeting_or_smalltalk"
    NEW_TOPIC = "new_topic"
    EXPLICIT_REFERENCE = "explicit_reference"
    DEICTIC_REFERENCE = "deictic_reference"
    ORDINAL_REFERENCE = "ordinal_reference"
    CONTINUATION_REFERENCE = "continuation_reference"
    MODIFY_PRIOR_OUTPUT = "modify_prior_output"
    COMPARE_PRIOR_OPTIONS = "compare_prior_options"
    TOOL_RESULT_REFERENCE = "tool_result_reference"
    CODE_OR_COMMAND_REFERENCE = "code_or_command_reference"
    DOCUMENT_REFERENCE = "document_reference"
    RECENT_CONTEXT_SUFFICIENT = "recent_context_sufficient"
    RECENT_CONTEXT_INSUFFICIENT = "recent_context_insufficient"
    MULTIPLE_CANDIDATES = "multiple_candidates"
    LOW_CONFIDENCE_AMBIGUITY = "low_confidence_ambiguity"


@dataclass(eq=True)
class ContextResolutionDecision:
    action: ContextResolutionAction
    reason: ContextResolutionReason
    confidence: float
    matched_signals: list[str]
    resolved_target: ResolutionCandidate | None = None
    candidate_count: int = 0
    should_retrieve: bool = False
    should_rewrite: bool = False
    rewritten_query: str | None = None
    needs_semantic_model: bool = False
    debug: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.action = _coerce_enum(ContextResolutionAction, self.action)
        self.reason = _coerce_enum(ContextResolutionReason, self.reason)
        if not isinstance(self.confidence, (float, int)):
            raise ValueError("confidence must be a number")
        _require_list("matched_signals", self.matched_signals)
        if not all(isinstance(signal, str) for signal in self.matched_signals):
            raise ValueError("matched_signals must contain only strings")
        if self.resolved_target is not None and not isinstance(self.resolved_target, ResolutionCandidate):
            raise ValueError("resolved_target must be a ResolutionCandidate or None")
        if not isinstance(self.candidate_count, int):
            raise ValueError("candidate_count must be an integer")
        if not isinstance(self.should_retrieve, bool):
            raise ValueError("should_retrieve must be a bool")
        if not isinstance(self.should_rewrite, bool):
            raise ValueError("should_rewrite must be a bool")
        if self.rewritten_query is not None and not isinstance(self.rewritten_query, str):
            raise ValueError("rewritten_query must be a string or None")
        if not isinstance(self.needs_semantic_model, bool):
            raise ValueError("needs_semantic_model must be a bool")
        if not isinstance(self.debug, dict):
            raise ValueError("debug must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason.value,
            "confidence": float(self.confidence),
            "matched_signals": list(self.matched_signals),
            "resolved_target": self.resolved_target.to_dict() if self.resolved_target else None,
            "candidate_count": self.candidate_count,
            "should_retrieve": self.should_retrieve,
            "should_rewrite": self.should_rewrite,
            "rewritten_query": self.rewritten_query,
            "needs_semantic_model": self.needs_semantic_model,
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = ["action", "reason", "confidence", "matched_signals"]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        resolved_target = data.get("resolved_target")
        return cls(
            action=ContextResolutionAction(data["action"]),
            reason=ContextResolutionReason(data["reason"]),
            confidence=float(data["confidence"]),
            matched_signals=list(data["matched_signals"]),
            resolved_target=ResolutionCandidate.from_dict(resolved_target) if resolved_target else None,
            candidate_count=data.get("candidate_count", 0),
            should_retrieve=data.get("should_retrieve", False),
            should_rewrite=data.get("should_rewrite", False),
            rewritten_query=data.get("rewritten_query"),
            needs_semantic_model=data.get("needs_semantic_model", False),
            debug=dict(data.get("debug", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class ContextResolutionConfig:
    session_id: str
    recent_window_token_budget: int | None = None
    retrieval_token_budget: int = 300
    top_k: int = 5
    enable_semantic_adjudication: bool = False
    prefer_recall_when_uncertain: bool = True
    include_recent_structured_artifacts: bool = True
    max_recent_candidates: int = 24
    max_selected_candidates: int = 8
    selected_evidence_only: bool = False
    include_full_recent_conversation: bool = True
    include_current_tool_results: bool = True
    boundary_policy: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from .host_integration import SessionRetrievalBoundaryPolicy

        self.session_id = _require_string("session_id", self.session_id)
        if self.recent_window_token_budget is not None and not isinstance(self.recent_window_token_budget, int):
            raise ValueError("recent_window_token_budget must be an integer or None")
        for field_name in (
            "retrieval_token_budget",
            "top_k",
            "max_recent_candidates",
            "max_selected_candidates",
        ):
            if not isinstance(getattr(self, field_name), int):
                raise ValueError(f"{field_name} must be an integer")
        for field_name in (
            "enable_semantic_adjudication",
            "prefer_recall_when_uncertain",
            "include_recent_structured_artifacts",
            "selected_evidence_only",
            "include_full_recent_conversation",
            "include_current_tool_results",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a bool")
        if self.boundary_policy is None:
            self.boundary_policy = SessionRetrievalBoundaryPolicy()
        if not isinstance(self.boundary_policy, SessionRetrievalBoundaryPolicy):
            raise ValueError("boundary_policy must be a SessionRetrievalBoundaryPolicy")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "recent_window_token_budget": self.recent_window_token_budget,
            "retrieval_token_budget": self.retrieval_token_budget,
            "top_k": self.top_k,
            "enable_semantic_adjudication": self.enable_semantic_adjudication,
            "prefer_recall_when_uncertain": self.prefer_recall_when_uncertain,
            "include_recent_structured_artifacts": self.include_recent_structured_artifacts,
            "max_recent_candidates": self.max_recent_candidates,
            "max_selected_candidates": self.max_selected_candidates,
            "selected_evidence_only": self.selected_evidence_only,
            "include_full_recent_conversation": self.include_full_recent_conversation,
            "include_current_tool_results": self.include_current_tool_results,
            "boundary_policy": self.boundary_policy.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        from .host_integration import SessionRetrievalBoundaryPolicy

        if "session_id" not in data:
            raise ValueError("Missing required fields: session_id")
        return cls(
            session_id=data["session_id"],
            recent_window_token_budget=data.get("recent_window_token_budget"),
            retrieval_token_budget=data.get("retrieval_token_budget", 300),
            top_k=data.get("top_k", 5),
            enable_semantic_adjudication=data.get("enable_semantic_adjudication", False),
            prefer_recall_when_uncertain=data.get("prefer_recall_when_uncertain", True),
            include_recent_structured_artifacts=data.get("include_recent_structured_artifacts", True),
            max_recent_candidates=data.get("max_recent_candidates", 24),
            max_selected_candidates=data.get("max_selected_candidates", 8),
            selected_evidence_only=data.get("selected_evidence_only", False),
            include_full_recent_conversation=data.get("include_full_recent_conversation", True),
            include_current_tool_results=data.get("include_current_tool_results", True),
            boundary_policy=SessionRetrievalBoundaryPolicy.from_dict(
                data.get("boundary_policy", {})
            ),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


@dataclass(eq=True)
class SessionContextPlan:
    decision: ContextResolutionDecision
    recent_window: RecentWindowSnapshot
    recent_candidates: list[ResolutionCandidate]
    retrieved_candidates: list[ResolutionCandidate]
    selected_candidates: list[ResolutionCandidate]
    retrieved_chunks: list[RetrievedChunk]
    prompt_blocks: list[PromptContextBlock]
    telemetry: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ContextResolutionDecision):
            raise ValueError("decision must be a ContextResolutionDecision")
        if not isinstance(self.recent_window, RecentWindowSnapshot):
            raise ValueError("recent_window must be a RecentWindowSnapshot")
        for field_name, item_type in (
            ("recent_candidates", ResolutionCandidate),
            ("retrieved_candidates", ResolutionCandidate),
            ("selected_candidates", ResolutionCandidate),
            ("retrieved_chunks", RetrievedChunk),
            ("prompt_blocks", PromptContextBlock),
        ):
            value = _require_list(field_name, getattr(self, field_name))
            if not all(isinstance(item, item_type) for item in value):
                raise ValueError(f"{field_name} must contain only {item_type.__name__} instances")
        if not isinstance(self.telemetry, dict):
            raise ValueError("telemetry must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "recent_window": self.recent_window.to_dict(),
            "recent_candidates": [candidate.to_dict() for candidate in self.recent_candidates],
            "retrieved_candidates": [candidate.to_dict() for candidate in self.retrieved_candidates],
            "selected_candidates": [candidate.to_dict() for candidate in self.selected_candidates],
            "retrieved_chunks": [chunk.to_dict() for chunk in self.retrieved_chunks],
            "prompt_blocks": [block.to_dict() for block in self.prompt_blocks],
            "telemetry": self.telemetry,
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = [
            "decision",
            "recent_window",
            "recent_candidates",
            "retrieved_candidates",
            "selected_candidates",
            "retrieved_chunks",
            "prompt_blocks",
        ]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            decision=ContextResolutionDecision.from_dict(data["decision"]),
            recent_window=RecentWindowSnapshot.from_dict(data["recent_window"]),
            recent_candidates=[
                ResolutionCandidate.from_dict(candidate) for candidate in data["recent_candidates"]
            ],
            retrieved_candidates=[
                ResolutionCandidate.from_dict(candidate) for candidate in data["retrieved_candidates"]
            ],
            selected_candidates=[
                ResolutionCandidate.from_dict(candidate) for candidate in data["selected_candidates"]
            ],
            retrieved_chunks=[RetrievedChunk.from_dict(chunk) for chunk in data["retrieved_chunks"]],
            prompt_blocks=[PromptContextBlock.from_dict(block) for block in data["prompt_blocks"]],
            telemetry=dict(data.get("telemetry", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))


def context_event_to_resolution_candidate(
    event: ContextEvent,
    *,
    source: str = "recent_window",
    score: float = 1.0,
) -> ResolutionCandidate:
    if not isinstance(event, ContextEvent):
        raise ValueError("event must be a ContextEvent")
    return ResolutionCandidate(
        candidate_id=f"{source}:{event.event_id}",
        session_id=event.session_id,
        source=source,
        content_type=event.event_type,
        summary=event.content,
        content=event.content,
        score=score,
        source_turn_id=str(event.turn_id),
        source_event_ids=[event.event_id],
        evidence=[event.content],
        metadata={
            "source": event.source,
            "source_ref": event.source_ref,
        },
    )


def memory_chunk_to_resolution_candidate(
    chunk: MemoryChunk,
    *,
    score: float = 1.0,
) -> ResolutionCandidate:
    if not isinstance(chunk, MemoryChunk):
        raise ValueError("chunk must be a MemoryChunk")
    return ResolutionCandidate(
        candidate_id=f"mid_session_memory:{chunk.chunk_id}",
        session_id=chunk.session_id,
        source="mid_session_memory",
        content_type=chunk.chunk_type,
        summary=chunk.retrieval_text,
        content=chunk.content,
        score=score,
        source_turn_id=str(chunk.start_turn_id),
        source_event_ids=list(chunk.source_event_ids),
        evidence=[chunk.retrieval_text],
        metadata={
            "chunk_id": chunk.chunk_id,
            "memory_scope": chunk.memory_scope,
            "memory_type": chunk.memory_type,
            "start_turn_id": chunk.start_turn_id,
            "end_turn_id": chunk.end_turn_id,
            "priority": chunk.priority,
            "ttl_seconds": chunk.ttl_seconds,
            **chunk.metadata,
        },
    )


def retrieved_chunk_to_resolution_candidate(retrieved: RetrievedChunk) -> ResolutionCandidate:
    if not isinstance(retrieved, RetrievedChunk):
        raise ValueError("retrieved must be a RetrievedChunk")
    candidate = memory_chunk_to_resolution_candidate(retrieved.chunk, score=float(retrieved.score))
    candidate.metadata.update(
        {
            "rank": retrieved.rank,
            "retrieval_source": retrieved.retrieval_source,
            "reason": retrieved.reason,
        }
    )
    return candidate


@dataclass(eq=True)
class LongTermCandidate:
    candidate_id: str
    subject_scope: str
    candidate_type: str
    content: str
    confidence: float
    source_session_id: str
    source_event_ids: list[str]
    subject_id: str | None = None
    status: str = "candidate"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.candidate_id = _require_string("candidate_id", self.candidate_id)
        self.subject_scope = _require_string("subject_scope", self.subject_scope)
        self.candidate_type = _require_string("candidate_type", self.candidate_type)
        self.content = _require_string("content", self.content)
        self.source_session_id = _require_string("source_session_id", self.source_session_id)
        self.status = _require_string("status", self.status)
        if not isinstance(self.confidence, (float, int)):
            raise ValueError("confidence must be a number")
        if not isinstance(self.source_event_ids, list):
            raise ValueError("source_event_ids must be a list")
        if self.subject_id is not None and not isinstance(self.subject_id, str):
            raise ValueError("subject_id must be a string or None")
        self.created_at = _parse_datetime(self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "subject_scope": self.subject_scope,
            "subject_id": self.subject_id,
            "candidate_type": self.candidate_type,
            "content": self.content,
            "confidence": float(self.confidence),
            "source_session_id": self.source_session_id,
            "source_event_ids": list(self.source_event_ids),
            "status": self.status,
            "created_at": _datetime_to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        required = [
            "candidate_id",
            "subject_scope",
            "candidate_type",
            "content",
            "confidence",
            "source_session_id",
            "source_event_ids",
        ]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            candidate_id=data["candidate_id"],
            subject_scope=data["subject_scope"],
            subject_id=data.get("subject_id"),
            candidate_type=data["candidate_type"],
            content=data["content"],
            confidence=float(data["confidence"]),
            source_session_id=data["source_session_id"],
            source_event_ids=list(data["source_event_ids"]),
            status=data.get("status", "candidate"),
            created_at=_parse_datetime(data.get("created_at", datetime.utcnow())),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: type[T], value: str) -> T:
        return cls.from_dict(json.loads(value))
