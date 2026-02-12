import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from datetime import datetime

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_chat_service():
    with patch("app.api.chat.chat_service") as mock:
        yield mock

@pytest.mark.asyncio
async def test_chat_stream_metrics_presence(client, mock_chat_service):
    """
    Verify that the chat stream includes the new metrics:
    - ttft (Time To First Token)
    - total_duration
    - prompt_tokens
    - completion_tokens
    - total_tokens
    - tps (Tokens Per Second)
    """
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="test-chat-metrics")
        mock_chat_service.get_chat.return_value = None
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Mock run_stream result
        mock_result = MagicMock()
        
        # Mocking an async generator for stream_text
        async def mock_stream():
            yield "Hello"
            yield " world"

        mock_result.stream_text.return_value = mock_stream()
        
        # Mock usage data (Pydantic AI result.usage())
        mock_usage = MagicMock()
        mock_usage.request_tokens = 10
        mock_usage.response_tokens = 20
        mock_usage.total_tokens = 30
        mock_result.usage.return_value = mock_usage
        
        # Mock context manager
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_result)
        mock_cm.__aexit__ = AsyncMock()
        mock_agent.run_stream.return_value = mock_cm
        
        response = client.post("/api/chat/stream", json={"message": "test metrics"})
        assert response.status_code == 200
        
        # Collect streaming output
        lines = []
        for line in response.iter_lines():
            if isinstance(line, bytes):
                lines.append(line.decode("utf-8"))
            else:
                lines.append(line)
        
        data_lines = [line[6:] for line in lines if line.startswith("data: ")] # Remove "data: " prefix
        
        json_responses = []
        for line in data_lines:
            try:
                json_responses.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        
        # Verify presence of metrics
        has_ttft = any("ttft" in r for r in json_responses)
        has_total_duration = any("total_duration" in r for r in json_responses)
        has_tokens = any("prompt_tokens" in r for r in json_responses)
        has_tps = any("tps" in r for r in json_responses)
        
        assert has_ttft, "Stream should contain TTFT"
        assert has_total_duration, "Stream should contain total_duration"
        assert has_tokens, "Stream should contain token usage data"
        assert has_tps, "Stream should contain TPS data"
        
        # Verify token values
        usage_resp = next(r for r in json_responses if "prompt_tokens" in r)
        assert usage_resp["prompt_tokens"] == 10
        assert usage_resp["completion_tokens"] == 20
        assert usage_resp["total_tokens"] == 30
        assert usage_resp["tps"] > 0

def test_syntax_check_f_strings():
    """
    Explicitly test that the code in chat.py doesn't contain the dangerous multiline f-string pattern.
    """
    import os
    chat_api_path = os.path.join(os.path.dirname(__file__), "../app/api/chat.py")
    with open(chat_api_path, 'r') as f:
        content = f.read()
        
    # Look for the pattern: yield f"data: {json.dumps({
    # which caused the SyntaxError because of the newline after {
    import re
    # This regex looks for 'yield f' followed by '{' and then a newline before a '}'
    dangerous_pattern = r'yield\s+f".*?\{\s*\n'
    match = re.search(dangerous_pattern, content, re.MULTILINE)
    
    assert match is None, f"Found dangerous multiline f-string pattern in chat.py: {match.group() if match else ''}"

if __name__ == "__main__":
    pytest.main([__file__])
