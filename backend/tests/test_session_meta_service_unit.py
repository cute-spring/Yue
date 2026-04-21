import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.chat_service import Message, ChatSession
from app.services.session_meta_service import SessionMetaService


def _build_chat(messages):
    now = datetime.now()
    return ChatSession(
        id="chat-1",
        title="New Chat",
        summary=None,
        messages=messages,
        created_at=now,
        updated_at=now
    )


@pytest.mark.asyncio
async def test_generate_session_meta_title():
    service = SessionMetaService()
    chat = _build_chat([
        Message(role="user", content="帮我做一个智能标题方案"),
        Message(role="assistant", content="我先给出轻量方案")
    ])
    with patch("app.services.session_meta_service.config_service") as mock_config, \
         patch("app.services.session_meta_service.chat_service") as mock_chat, \
         patch("app.services.session_meta_service.get_model") as mock_get_model, \
         patch("app.services.session_meta_service.Agent") as mock_agent_cls:
        mock_config.get_llm_config.return_value = {
            "meta_enabled": True,
            "meta_provider": "openai",
            "meta_model": "gpt-4o-mini",
            "meta_timeout_ms": 1000,
            "meta_max_tokens": 48,
        }
        mock_chat.get_chat.return_value = chat
        mock_get_model.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def stream():
            yield "智能标题"

        mock_result.stream_text.return_value = stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock(return_value=None)

        title = await service.generate_session_meta("chat-1", task="title")
        assert title == "智能标题"


@pytest.mark.asyncio
async def test_generate_session_meta_returns_none_when_disabled():
    service = SessionMetaService()
    with patch("app.services.session_meta_service.config_service") as mock_config:
        mock_config.get_llm_config.return_value = {"meta_enabled": False}
        summary = await service.generate_session_meta("chat-1", task="summary")
        assert summary is None

@pytest.mark.asyncio
async def test_generate_session_meta_uses_runtime_provider_override():
    service = SessionMetaService()
    chat = _build_chat([
        Message(role="user", content="请帮我设计测试"),
        Message(role="assistant", content="这是回答")
    ])
    with patch("app.services.session_meta_service.config_service") as mock_config, \
         patch("app.services.session_meta_service.chat_service") as mock_chat, \
         patch("app.services.session_meta_service.get_model") as mock_get_model, \
         patch("app.services.session_meta_service.Agent") as mock_agent_cls:
        mock_config.get_llm_config.return_value = {
            "meta_enabled": True,
            "meta_provider": None,
            "meta_model": None,
            "meta_timeout_ms": 1000,
            "meta_max_tokens": 48,
        }
        mock_chat.get_chat.return_value = chat
        mock_get_model.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def stream():
            yield "运行时标题"

        mock_result.stream_text.return_value = stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock(return_value=None)

        title = await service.generate_session_meta(
            "chat-1",
            task="title",
            provider_override="openai",
            model_override="gpt-4o"
        )
        assert title == "运行时标题"
        mock_get_model.assert_called_once_with("openai", "gpt-4o")
