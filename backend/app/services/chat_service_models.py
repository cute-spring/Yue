import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

DATA_DIR = os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))
OLD_CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
logger = logging.getLogger(__name__)

TAG_MAX_COUNT = 8
TAG_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "we", "with", "you", "your",
}
TAG_SYNONYMS = {
    "authentication": "auth",
    "authorize": "auth",
    "authorization": "auth",
    "bug": "bugfix",
    "bugs": "bugfix",
    "fix": "bugfix",
    "fixes": "bugfix",
    "frontend": "ui-ux",
    "ui": "ui-ux",
    "ux": "ui-ux",
    "tests": "testing",
}


class Message(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    images: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    chart_artifacts: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    thought_duration: Optional[float] = None
    ttft: Optional[float] = None
    total_duration: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    continuation_of: Optional[str] = None
    continuation_root_id: Optional[str] = None
    continuation_status: Optional[str] = None
    content_type: Optional[str] = None
    supports_reasoning: Optional[bool] = None
    deep_thinking_enabled: Optional[bool] = None
    reasoning_enabled: Optional[bool] = None


class ToolCall(BaseModel):
    id: Optional[int] = None
    session_id: str
    message_id: Optional[int] = None
    call_id: str
    tool_name: str
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    event_id_started: Optional[str] = None
    event_id_finished: Optional[str] = None
    started_sequence: Optional[int] = None
    finished_sequence: Optional[int] = None
    started_ts: Optional[datetime] = None
    finished_ts: Optional[datetime] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None


class SkillEffectivenessEvent(BaseModel):
    id: Optional[int] = None
    session_id: str
    reason_code: str
    selection_source: str
    fallback_used: bool
    selected_skill_name: Optional[str] = None
    selected_skill_version: Optional[str] = None
    selected_skill_source_layer: Optional[str] = None
    override_hit: Optional[bool] = None
    visible_skill_count: Optional[int] = None
    available_skill_count: Optional[int] = None
    always_injected_count: Optional[int] = None
    summary_injected: Optional[bool] = None
    summary_prompt_enabled: Optional[bool] = None
    lazy_full_load_enabled: Optional[bool] = None
    selection_score: Optional[int] = None
    system_prompt_tokens_estimate: Optional[int] = None
    user_message_tokens_estimate: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ActionEvent(BaseModel):
    id: Optional[int] = None
    session_id: str
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    event_name: str
    event_id: Optional[str] = None
    sequence: Optional[int] = None
    ts: Optional[str] = None
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)


class ActionObservability(BaseModel):
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error_kind: Optional[str] = None
    retryable: Optional[bool] = None
    artifact_path: Optional[str] = None


class ActionState(BaseModel):
    id: Optional[int] = None
    session_id: str
    skill_name: str
    skill_version: Optional[str] = None
    action_id: str
    invocation_id: Optional[str] = None
    approval_token: Optional[str] = None
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    assistant_turn_id: Optional[str] = None
    lifecycle_phase: Optional[str] = None
    lifecycle_status: str
    status: Optional[str] = None
    observability: Optional[ActionObservability] = None
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    id: str
    workspace_id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    agent_id: Optional[str] = None
    active_skill_name: Optional[str] = None
    active_skill_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    messages: List[Message] = []
    created_at: datetime
    updated_at: datetime
