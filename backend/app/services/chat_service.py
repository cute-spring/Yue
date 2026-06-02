from .chat_service_actions import ChatServiceActionsMixin
from .chat_service_models import (
    ActionEvent,
    ActionObservability,
    ActionState,
    ChatSession,
    Message,
    SkillEffectivenessEvent,
    ToolCall,
)
from .chat_service_schema import ChatServiceSchemaMixin
from .chat_service_sessions import ChatServiceSessionsMixin


class ChatService(
    ChatServiceSchemaMixin,
    ChatServiceSessionsMixin,
    ChatServiceActionsMixin,
):
    def __init__(self):
        self._ensure_db()
        self._migrate_from_json()


chat_service = ChatService()

__all__ = [
    "ActionEvent",
    "ActionObservability",
    "ActionState",
    "ChatService",
    "ChatSession",
    "Message",
    "SkillEffectivenessEvent",
    "ToolCall",
    "chat_service",
]
