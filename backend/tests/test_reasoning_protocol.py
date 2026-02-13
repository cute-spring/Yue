import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
import json

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_reasoning_protocol_injection_non_reasoning_model(client):
    """Test that non-reasoning models get the reasoning protocol injected."""
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service:
        
        # Setup mocks
        mock_chat_service.create_chat.return_value = MagicMock(id="test-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        mock_result = MagicMock()
        async def mock_stream():
            yield "Hello"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()
        
        # Request with a non-reasoning model
        payload = {
            "message": "hi",
            "model": "gpt-4o",
            "provider": "openai"
        }
        
        response = client.post("/api/chat/stream", json=payload)
        assert response.status_code == 200
        
        # Verify that Agent was called with the injected system prompt
        # The system prompt should contain the Reasoning Protocol
        args, kwargs = mock_agent_cls.call_args
        system_prompt = kwargs.get("system_prompt", "")
        
        assert "### Reasoning Protocol" in system_prompt
        assert "[目标]" in system_prompt
        assert "[已知条件]" in system_prompt
        assert "[计划]" in system_prompt
        assert "[反思]" in system_prompt

@pytest.mark.asyncio
async def test_reasoning_protocol_no_injection_for_reasoning_model(client):
    """Test that reasoning models do NOT get the reasoning protocol injected."""
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="test-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        mock_result = MagicMock()
        async def mock_stream():
            yield "Hello"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()
        
        # Request with a reasoning model
        payload = {
            "message": "hi",
            "model": "deepseek-reasoner",
            "provider": "deepseek"
        }
        
        response = client.post("/api/chat/stream", json=payload)
        assert response.status_code == 200
        
        args, kwargs = mock_agent_cls.call_args
        system_prompt = kwargs.get("system_prompt", "")
        
        assert "### Reasoning Protocol" not in system_prompt
