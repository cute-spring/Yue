import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic_ai import UsageLimits

from app.services.chat_streaming import StreamState


@dataclass
class StreamRunContext:
    chat_id: str
    request: Any
    history: List[Any]
    validated_images: List[str]
    feature_flags: Dict[str, Any]
    run_id: str
    request_id: str
    assistant_turn_id: str
    event_v2_enabled: bool
    turn_binding_enabled: bool
    reasoning_display_gated_enabled: bool
    provider: Optional[str]
    model_name: Optional[str]
    system_prompt: Optional[str]
    stream_state: StreamState = field(default_factory=StreamState)
    tool_event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    agent_config: Any = None
    deps: Any = None
    model_settings: Dict[str, Any] = field(default_factory=dict)
    parser: Any = None
    usage_limits: Optional[UsageLimits] = None
    result: Any = None


@dataclass
class StreamRunMetrics:
    thought_duration: Optional[float] = None
    ttft: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: Optional[str] = None
    total_duration: Optional[float] = None
    stream_error_message: Optional[str] = None
    current_exception: Optional[BaseException] = None
    supports_reasoning: bool = False
    reasoning_enabled: bool = False
