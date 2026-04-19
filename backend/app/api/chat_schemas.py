from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Attachment(BaseModel):
    id: str | None = None
    kind: str = "file"
    display_name: str | None = None
    storage_path: str | None = None
    url: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    extension: str | None = None
    source: str | None = None
    status: str | None = None


class ChatRequest(BaseModel):
    message: str
    images: list[str] | None = None
    attachments: list[Attachment] | None = None
    agent_id: str | None = None
    requested_skill: str | None = None
    requested_action: str | None = None
    requested_action_arguments: dict | None = None
    requested_action_approved: bool | None = None
    requested_action_approval_token: str | None = None
    chat_id: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    model_role: str | None = None
    deep_thinking_enabled: bool = False


class TruncateRequest(BaseModel):
    keep_count: int


class SummaryGenerateRequest(BaseModel):
    force: bool = False


class ActionStateResponse(BaseModel):
    id: int | None = None
    session_id: str
    skill_name: str
    skill_version: str | None = None
    action_id: str
    invocation_id: str | None = None
    approval_token: str | None = None
    request_id: str | None = None
    run_id: str | None = None
    assistant_turn_id: str | None = None
    lifecycle_phase: str | None = None
    lifecycle_status: str
    status: str | None = None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
