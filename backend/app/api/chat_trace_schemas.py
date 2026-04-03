from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


TraceViewMode = Literal["summary", "raw"]
TraceRecordStatus = Literal["started", "success", "error", "cancelled"]
TraceFieldExposure = Literal["safe", "raw_only"]


class TraceFieldPolicy(BaseModel):
    field_name: str
    exposure: TraceFieldExposure
    reason: Optional[str] = None


class RequestHistoryItem(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] | str
    content_type: Literal["text", "image", "json", "mixed"] | str = "text"
    content_summary: Optional[str] = None
    image_count: int = 0
    truncated: bool = False


class RequestAttachmentItem(BaseModel):
    kind: Literal["image", "file", "other"] | str
    name: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    redacted: bool = False


class RequestSnapshotRecord(BaseModel):
    chat_id: str
    assistant_turn_id: str
    request_id: str
    run_id: str
    created_at: datetime
    provider: Optional[str] = None
    model: Optional[str] = None
    agent_id: Optional[str] = None
    requested_skill: Optional[str] = None
    deep_thinking_enabled: bool = False
    system_prompt: Optional[str] = None
    user_message: str = ""
    message_history: list[RequestHistoryItem] = Field(default_factory=list)
    attachments: list[RequestAttachmentItem] = Field(default_factory=list)
    tool_context: dict[str, Any] = Field(default_factory=dict)
    skill_context: dict[str, Any] = Field(default_factory=dict)
    runtime_flags: dict[str, Any] = Field(default_factory=dict)
    redaction: dict[str, Any] = Field(default_factory=dict)
    truncation: dict[str, Any] = Field(default_factory=dict)


class ToolTraceRecord(BaseModel):
    chat_id: str
    run_id: str
    assistant_turn_id: str
    trace_id: str
    parent_trace_id: Optional[str] = None
    tool_name: str
    tool_type: Optional[str] = None
    call_id: Optional[str] = None
    call_index: int = 0
    status: TraceRecordStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    input_arguments: Any = None
    output_result: Any = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    chain_depth: int = 0
    raw_event_id: Optional[str] = None


class ChatTraceBundle(BaseModel):
    mode: TraceViewMode = "summary"
    chat_id: str
    run_id: str
    assistant_turn_id: str
    snapshot: RequestSnapshotRecord
    tool_traces: list[ToolTraceRecord] = Field(default_factory=list)
    field_policies: list[TraceFieldPolicy] = Field(default_factory=list)


DEFAULT_TRACE_FIELD_POLICIES: tuple[TraceFieldPolicy, ...] = (
    TraceFieldPolicy(field_name="system_prompt", exposure="raw_only", reason="May contain internal prompt blocks."),
    TraceFieldPolicy(field_name="input_arguments", exposure="raw_only", reason="Tool arguments may include sensitive values."),
    TraceFieldPolicy(field_name="output_result", exposure="raw_only", reason="Tool outputs may contain sensitive values."),
    TraceFieldPolicy(field_name="error_stack", exposure="raw_only", reason="Stacks may expose internal implementation details."),
)


def build_default_trace_field_policies() -> list[TraceFieldPolicy]:
    return [policy.model_copy(deep=True) for policy in DEFAULT_TRACE_FIELD_POLICIES]

