import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_agent_refactor_regression_master_sub_agent_query(client):
    """
    Mandatory regression test case for agent refactoring.
    
    This test verifies that the system correctly handles a chat stream request
    targeting the 'builtin-local-docs' agent with a specific query about master-sub agents.
    
    Payload source: User provided fetch case (2026-03-01)
    """
    # 1. Payload configuration
    payload = {
        "message": "有什么讲到关于主子agent的内容？",
        "agent_id": "builtin-local-docs",
        "chat_id": "e355cd56-873c-4bba-a70a-9a4ae62685fb",
        "provider": "deepseek",
        "model": "deepseek-reasoner"
    }
    
    # 2. Mocking complex backend dependencies
    # We mock Agent initialization and chat service to isolate the API plumbing test
    with patch("app.api.chat.Agent") as mock_agent_cls, \
         patch("app.api.chat.chat_service") as mock_chat_service, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model") as mock_get_model:
        
        # Setup mocks
        mock_chat_service.create_chat.return_value = MagicMock(id=payload["chat_id"])
        mock_chat_service.get_chat.return_value = None
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        # Mock Agent instance and its run_stream method
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance
        
        mock_result = MagicMock()
        async def mock_stream_gen():
            # Minimal mock stream response
            yield "data: " + json.dumps({"content": "Verified: master-sub agent info found."}) + "\n\n"
            
        mock_result.stream_text.return_value = mock_stream_gen()
        mock_agent_instance.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent_instance.run_stream.return_value.__aexit__ = AsyncMock()

        # 3. Execution: Call the API
        response = client.post("/api/chat/stream", json=payload)
        
        # 4. Assertions
        # Verify HTTP status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify Agent was initialized
        mock_agent_cls.assert_called_once()
        args, kwargs = mock_agent_cls.call_args
        
        # args[0] should be the model from get_model
        mock_get_model.assert_called_once_with(payload["provider"], payload["model"])
        
        # Verify system prompt was passed
        assert "system_prompt" in kwargs
        
        # Verify the user message reached the agent execution layer
        mock_agent_instance.run_stream.assert_called_once_with(payload["message"])
        
        # Verify the streaming response format
        lines = [line for line in response.iter_lines() if line]
        assert any(b"Verified: master-sub agent info found." in line for line in lines)

if __name__ == "__main__":
    # For quick manual execution
    import sys
    import os
    # Add backend to sys.path if needed
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    pytest.main([__file__])
