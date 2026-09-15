from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Protocol, Sequence

from .models import (
    ContextEvent,
    ContextResolutionConfig,
    PromptContextBlock,
    ResolutionCandidate,
    SessionContextPlan,
)
from .session_context.manager import SessionContextManager

_COMMON_EVENT_TYPE_ALIASES = {
    "user": "user_message",
    "human": "user_message",
    "assistant": "assistant_message",
    "ai": "assistant_message",
    "tool": "tool_call",
    "tool_use": "tool_call",
    "tool_output": "tool_result",
    "function_call": "tool_call",
    "function_result": "tool_result",
}
_DEFAULT_PROMPT_SECTION_BY_BLOCK_NAME = {
    "safety_statement": "safety",
    "current_tool_results": "current_tool_results",
    "recent_conversation": "recent_context",
    "recent_structured_artifacts": "recent_artifacts",
    "mid_term_tool_results": "mid_session_memory",
    "mid_term_conversation_memory": "mid_session_memory",
}


class HostEventAdapter(Protocol):
    def build_recent_events(
        self,
        *,
        session_id: str,
        host_records: Sequence[Any],
    ) -> list[ContextEvent]: ...


def normalize_context_event_type(event_type: str) -> str:
    normalized = " ".join(event_type.strip().lower().replace("-", "_").split())
    normalized = normalized.replace(" ", "_")
    if not normalized:
        raise ValueError("event_type must be a non-empty string")
    return _COMMON_EVENT_TYPE_ALIASES.get(normalized, normalized)


def validate_context_event_required_fields(event: ContextEvent) -> ContextEvent:
    if not isinstance(event, ContextEvent):
        raise ValueError("event must be a ContextEvent")
    if not event.event_id.strip():
        raise ValueError("event_id must be a non-empty string")
    if not event.session_id.strip():
        raise ValueError("session_id must be a non-empty string")
    if not isinstance(event.turn_id, int):
        raise ValueError("turn_id must be an integer")
    if event.turn_id < 0:
        raise ValueError("turn_id must be non-negative")
    if event.event_type != normalize_context_event_type(event.event_type):
        raise ValueError(f"event_type must be normalized: {event.event_type!r}")
    if not event.content.strip():
        raise ValueError("content must be a non-empty string")
    return event


def validate_ordered_context_events(
    session_id: str,
    events: Sequence[ContextEvent],
) -> list[ContextEvent]:
    validated: list[ContextEvent] = []
    previous_turn_id: int | None = None

    for event in events:
        validate_context_event_required_fields(event)
        if event.session_id != session_id:
            raise ValueError(
                f"Event {event.event_id!r} belongs to session {event.session_id!r}, expected {session_id!r}"
            )
        if previous_turn_id is not None and event.turn_id < previous_turn_id:
            raise ValueError("events must be ordered by non-decreasing turn_id")
        validated.append(event)
        previous_turn_id = event.turn_id
    return validated


def normalize_context_events(
    session_id: str,
    events: Sequence[ContextEvent],
) -> list[ContextEvent]:
    normalized = [
        ContextEvent(
            event_id=event.event_id,
            session_id=event.session_id,
            turn_id=event.turn_id,
            event_type=normalize_context_event_type(event.event_type),
            content=event.content,
            source=event.source,
            source_ref=event.source_ref,
            metadata=dict(event.metadata),
            created_at=event.created_at,
        )
        for event in events
    ]
    return validate_ordered_context_events(session_id, normalized)


@dataclass(eq=True)
class ExportedPromptBlock:
    name: str
    section: str
    content: str
    priority: int
    token_count: int
    source_chunk_ids: list[str] = field(default_factory=list)
    selected_candidate_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.section, str) or not self.section.strip():
            raise ValueError("section must be a non-empty string")
        if not isinstance(self.content, str):
            raise ValueError("content must be a string")
        if not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")
        if not isinstance(self.token_count, int):
            raise ValueError("token_count must be an integer")
        if not all(isinstance(item, str) for item in self.source_chunk_ids):
            raise ValueError("source_chunk_ids must contain only strings")
        if not all(isinstance(item, str) for item in self.selected_candidate_ids):
            raise ValueError("selected_candidate_ids must contain only strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "section": self.section,
            "content": self.content,
            "priority": self.priority,
            "token_count": self.token_count,
            "source_chunk_ids": list(self.source_chunk_ids),
            "selected_candidate_ids": list(self.selected_candidate_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExportedPromptBlock":
        required = ("name", "section", "content", "priority", "token_count")
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            name=str(data["name"]),
            section=str(data["section"]),
            content=str(data["content"]),
            priority=int(data["priority"]),
            token_count=int(data["token_count"]),
            source_chunk_ids=list(data.get("source_chunk_ids", [])),
            selected_candidate_ids=list(data.get("selected_candidate_ids", [])),
        )


@dataclass(eq=True)
class ExportedPromptContext:
    blocks: list[ExportedPromptBlock]
    prompt_blocks: list[PromptContextBlock]
    rendered_text: str | None = None
    source_chunk_ids: list[str] = field(default_factory=list)
    selected_candidate_ids: list[str] = field(default_factory=list)
    block_names: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not all(isinstance(block, ExportedPromptBlock) for block in self.blocks):
            raise ValueError("blocks must contain only ExportedPromptBlock instances")
        if not all(isinstance(block, PromptContextBlock) for block in self.prompt_blocks):
            raise ValueError("prompt_blocks must contain only PromptContextBlock instances")
        if self.rendered_text is not None and not isinstance(self.rendered_text, str):
            raise ValueError("rendered_text must be a string or None")
        for field_name in ("source_chunk_ids", "selected_candidate_ids", "block_names", "sections"):
            value = getattr(self, field_name)
            if not all(isinstance(item, str) for item in value):
                raise ValueError(f"{field_name} must contain only strings")

    @classmethod
    def from_prompt_blocks(
        cls,
        prompt_blocks: Sequence[PromptContextBlock],
        *,
        selected_candidates: Sequence[ResolutionCandidate] = (),
        rendered_text: str | None = None,
        section_by_block_name: Mapping[str, str] | None = None,
    ) -> "ExportedPromptContext":
        selected_candidate_ids = [candidate.candidate_id for candidate in selected_candidates]
        selected_candidate_ids_by_chunk_id: dict[str, list[str]] = {}
        selected_candidate_ids_by_source: dict[str, list[str]] = {}
        for candidate in selected_candidates:
            chunk_id = candidate.metadata.get("chunk_id")
            if isinstance(chunk_id, str):
                selected_candidate_ids_by_chunk_id.setdefault(chunk_id, []).append(candidate.candidate_id)
            selected_candidate_ids_by_source.setdefault(candidate.source, []).append(candidate.candidate_id)

        exported_blocks: list[ExportedPromptBlock] = []
        source_chunk_ids: list[str] = []
        sections: list[str] = []
        block_names: list[str] = []
        for block in prompt_blocks:
            block_names.append(block.name)
            section = (
                section_by_block_name.get(block.name, block.name)
                if section_by_block_name is not None
                else block.name
            )
            if section not in sections:
                sections.append(section)

            block_selected_candidate_ids: list[str] = []
            for chunk_id in block.source_chunk_ids:
                source_chunk_ids.append(chunk_id)
                for candidate_id in selected_candidate_ids_by_chunk_id.get(chunk_id, []):
                    if candidate_id not in block_selected_candidate_ids:
                        block_selected_candidate_ids.append(candidate_id)
            if block.name == "recent_structured_artifacts":
                for candidate_id in selected_candidate_ids_by_source.get("recent_artifact", []):
                    if candidate_id not in block_selected_candidate_ids:
                        block_selected_candidate_ids.append(candidate_id)

            exported_blocks.append(
                ExportedPromptBlock(
                    name=block.name,
                    section=section,
                    content=block.content,
                    priority=block.priority,
                    token_count=block.token_count,
                    source_chunk_ids=list(block.source_chunk_ids),
                    selected_candidate_ids=block_selected_candidate_ids,
                )
            )

        deduped_source_chunk_ids: list[str] = []
        for chunk_id in source_chunk_ids:
            if chunk_id not in deduped_source_chunk_ids:
                deduped_source_chunk_ids.append(chunk_id)

        return cls(
            blocks=exported_blocks,
            prompt_blocks=list(prompt_blocks),
            rendered_text=rendered_text,
            source_chunk_ids=deduped_source_chunk_ids,
            selected_candidate_ids=selected_candidate_ids,
            block_names=block_names,
            sections=sections,
        )

    def blocks_by_section(self) -> dict[str, list[ExportedPromptBlock]]:
        grouped: dict[str, list[ExportedPromptBlock]] = {}
        for block in self.blocks:
            grouped.setdefault(block.section, []).append(block)
        return grouped

    def section_text(self, section: str, *, separator: str = "\n\n") -> str:
        return separator.join(block.content for block in self.blocks if block.section == section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocks": [block.to_dict() for block in self.blocks],
            "prompt_blocks": [block.to_dict() for block in self.prompt_blocks],
            "rendered_text": self.rendered_text,
            "source_chunk_ids": list(self.source_chunk_ids),
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "block_names": list(self.block_names),
            "sections": list(self.sections),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExportedPromptContext":
        required = ("blocks", "prompt_blocks")
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            blocks=[ExportedPromptBlock.from_dict(item) for item in data["blocks"]],
            prompt_blocks=[PromptContextBlock.from_dict(item) for item in data["prompt_blocks"]],
            rendered_text=data.get("rendered_text"),
            source_chunk_ids=list(data.get("source_chunk_ids", [])),
            selected_candidate_ids=list(data.get("selected_candidate_ids", [])),
            block_names=list(data.get("block_names", [])),
            sections=list(data.get("sections", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "ExportedPromptContext":
        return cls.from_dict(json.loads(value))


@dataclass(frozen=True)
class SessionRetrievalBoundaryPolicy:
    allow_mid_session_retrieval: bool = True
    allow_cross_session_retrieval: bool = False
    allow_external_knowledge_retrieval: bool = False
    allow_host_managed_retrieval_routing: bool = True
    package_owned_scopes: tuple[str, ...] = (
        "recent session context routing",
        "mid-session retrieval",
        "selected evidence composition",
    )
    host_owned_scopes: tuple[str, ...] = (
        "cross-session memory",
        "external knowledge retrieval",
        "internet or document search",
        "business routing across multiple retrieval systems",
    )

    def allows_manager_mid_session_retrieval(self) -> bool:
        return self.allow_mid_session_retrieval

    def package_scope_summary(self) -> str:
        return ", ".join(self.package_owned_scopes)

    def host_scope_summary(self) -> str:
        return ", ".join(self.host_owned_scopes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_mid_session_retrieval": self.allow_mid_session_retrieval,
            "allow_cross_session_retrieval": self.allow_cross_session_retrieval,
            "allow_external_knowledge_retrieval": self.allow_external_knowledge_retrieval,
            "allow_host_managed_retrieval_routing": self.allow_host_managed_retrieval_routing,
            "package_owned_scopes": list(self.package_owned_scopes),
            "host_owned_scopes": list(self.host_owned_scopes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SessionRetrievalBoundaryPolicy":
        return cls(
            allow_mid_session_retrieval=bool(data.get("allow_mid_session_retrieval", True)),
            allow_cross_session_retrieval=bool(data.get("allow_cross_session_retrieval", False)),
            allow_external_knowledge_retrieval=bool(
                data.get("allow_external_knowledge_retrieval", False)
            ),
            allow_host_managed_retrieval_routing=bool(
                data.get("allow_host_managed_retrieval_routing", True)
            ),
            package_owned_scopes=tuple(data.get("package_owned_scopes", cls().package_owned_scopes)),
            host_owned_scopes=tuple(data.get("host_owned_scopes", cls().host_owned_scopes)),
        )


@dataclass(frozen=True)
class SessionContextReplayCase:
    case_id: str
    session_id: str
    current_input: str
    recent_events: tuple[ContextEvent, ...]
    config: ContextResolutionConfig
    current_tool_results: tuple[str | ContextEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.config.session_id != self.session_id:
            raise ValueError("config.session_id must match replay case session_id")
        validate_ordered_context_events(self.session_id, self.recent_events)

    @classmethod
    def from_host_records(
        cls,
        *,
        case_id: str,
        session_id: str,
        current_input: str,
        host_records: Sequence[Any],
        adapter: HostEventAdapter,
        config: ContextResolutionConfig,
        current_tool_results: Sequence[str | ContextEvent] = (),
    ) -> "SessionContextReplayCase":
        recent_events = adapter.build_recent_events(
            session_id=session_id,
            host_records=host_records,
        )
        return cls(
            case_id=case_id,
            session_id=session_id,
            current_input=current_input,
            recent_events=tuple(recent_events),
            config=config,
            current_tool_results=tuple(current_tool_results),
        )

    def run(self, manager: SessionContextManager) -> SessionContextPlan:
        return manager.resolve(
            session_id=self.session_id,
            current_input=self.current_input,
            recent_events=list(self.recent_events),
            config=self.config,
            current_tool_results=list(self.current_tool_results),
        )


def default_prompt_export_sections() -> dict[str, str]:
    return dict(_DEFAULT_PROMPT_SECTION_BY_BLOCK_NAME)


def export_prompt_context(
    prompt_blocks: Sequence[PromptContextBlock],
    *,
    selected_candidates: Sequence[ResolutionCandidate] = (),
    rendered_text: str | None = None,
    section_by_block_name: Mapping[str, str] | None = None,
) -> ExportedPromptContext:
    return ExportedPromptContext.from_prompt_blocks(
        prompt_blocks,
        selected_candidates=selected_candidates,
        rendered_text=rendered_text,
        section_by_block_name=section_by_block_name or _DEFAULT_PROMPT_SECTION_BY_BLOCK_NAME,
    )
