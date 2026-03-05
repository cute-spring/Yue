import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.agent_store import AgentConfig

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_legacy_agent_behavior_baseline(client):
    """
    Phase 0 Baseline: Verify that a standard agent (skill_mode=off) 
    continues to function without any skill-related interference.
    """
    payload = {
        "message": "Hello, who are you?",
        "agent_id": "builtin-architect",
        "chat_id": "baseline-chat-id",
        "provider": "openai",
        "model": "gpt-4o"
    }
    
    # Mocking dependencies to isolate the test to the chat flow
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service, \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model") as mock_get_model:
        
        # Setup AgentConfig (Legacy)
        mock_agent = AgentConfig(
            id="builtin-architect",
            name="System Architect",
            system_prompt="You are an architect.",
            provider="openai",
            model="gpt-4o",
            enabled_tools=[]
        )
        mock_agent_store.get_agent.return_value = mock_agent
        mock_chat_service.create_chat.return_value = MagicMock(id=payload["chat_id"])
        mock_chat_service.get_chat.return_value = None
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        
        # Mock Agent instance and its run_stream method
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance
        
        mock_result = MagicMock()
        async def mock_stream_gen():
            yield "data: " + json.dumps({"content": "I am a system architect."}) + "\n\n"
            
        mock_result.stream_text.return_value = mock_stream_gen()
        mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

        # Execution
        response = client.post("/api/chat/stream", json=payload)
        
        # Assertions
        assert response.status_code == 200
        
        # Ensure Agent was initialized with the correct system prompt
        mock_agent_cls.assert_called_once()
        _, kwargs = mock_agent_cls.call_args
        # The system prompt might be enhanced by PromptBuilder, so we check if our base prompt is in it
        assert "You are an architect." in kwargs["system_prompt"]
        
        # Verify no skill-related logic was triggered (this is the key for Phase 0)
        # Since we haven't implemented skill logic yet, this is naturally true.
        # But we'll use this test to ensure it stays true after Phase A/B.
        
        lines = [line for line in response.iter_lines() if line]
        assert any("I am a system architect." in line for line in lines)

if __name__ == "__main__":
    pytest.main([__file__])
