import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
import json

@pytest.fixture
def client():
    return TestClient(app)

def _read_stream_payloads(response):
    payloads = []
    for line in response.iter_lines():
        if not isinstance(line, str) or not line.startswith("data: "):
            continue
        try:
            payloads.append(json.loads(line[6:]))
        except Exception:
            continue
    return payloads

@pytest.mark.asyncio
async def test_reasoning_protocol_injection_only_when_reasoning_enabled(client):
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service, \
         patch("app.api.chat.config_service.get_model_capabilities") as mock_caps:
        mock_chat_service.create_chat.return_value = MagicMock(id="test-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_caps.return_value = ["reasoning"]
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream():
            yield "Hello"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        payload = {
            "message": "hi",
            "model": "gpt-4o",
            "provider": "openai",
            "deep_thinking_enabled": True
        }
        response = client.post("/api/chat/stream", json=payload)
        assert response.status_code == 200

        args, kwargs = mock_agent_cls.call_args
        system_prompt = kwargs.get("system_prompt", "")
        assert "### Reasoning Protocol" in system_prompt
        assert "[目标]" in system_prompt

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "supports_reasoning,deep_thinking_enabled,expected_reasoning_enabled",
    [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (True, True, True),
    ],
)
async def test_reasoning_decision_matrix_in_meta(client, supports_reasoning, deep_thinking_enabled, expected_reasoning_enabled):
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service, \
         patch("app.api.chat.config_service.get_model_capabilities") as mock_caps:
        mock_chat_service.create_chat.return_value = MagicMock(id="test-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_caps.return_value = ["reasoning"] if supports_reasoning else []
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream():
            yield "Hello"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        payload = {
            "message": "hi",
            "model": "test-model",
            "provider": "openai",
            "deep_thinking_enabled": deep_thinking_enabled
        }
        response = client.post("/api/chat/stream", json=payload)
        assert response.status_code == 200
        payloads = _read_stream_payloads(response)
        meta_event = next(item for item in payloads if isinstance(item, dict) and "meta" in item)
        meta = meta_event["meta"]
        assert meta["supports_reasoning"] is supports_reasoning
        assert meta["deep_thinking_enabled"] is deep_thinking_enabled
        assert meta["reasoning_enabled"] is expected_reasoning_enabled
