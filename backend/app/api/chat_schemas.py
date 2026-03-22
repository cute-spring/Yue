from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    images: list[str] | None = None
    agent_id: str | None = None
    requested_skill: str | None = None
    chat_id: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    deep_thinking_enabled: bool = False


class TruncateRequest(BaseModel):
    keep_count: int


class SummaryGenerateRequest(BaseModel):
    force: bool = False
