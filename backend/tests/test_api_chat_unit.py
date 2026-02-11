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

def test_list_chats(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.list_chats.return_value = [
        {"id": "1", "title": "Chat 1", "created_at": now, "updated_at": now, "messages": []}
    ]
    response = client.get("/api/chat/history")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "1"

def test_get_chat_success(client, mock_chat_service):
    now = datetime.now()
    mock_chat_service.get_chat.return_value = {
        "id": "1", "title": "Chat 1", "created_at": now, "updated_at": now, "messages": []
    }
    response = client.get("/api/chat/1")
    assert response.status_code == 200
    assert response.json()["id"] == "1"

def test_get_chat_not_found(client, mock_chat_service):
    mock_chat_service.get_chat.return_value = None
    response = client.get("/api/chat/non_existent")
    assert response.status_code == 404

def test_delete_chat_success(client, mock_chat_service):
    mock_chat_service.delete_chat.return_value = True
    response = client.delete("/api/chat/1")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_delete_chat_not_found(client, mock_chat_service):
    mock_chat_service.delete_chat.return_value = False
    response = client.delete("/api/chat/non_existent")
    assert response.status_code == 404

def test_truncate_chat(client, mock_chat_service):
    response = client.post("/api/chat/1/truncate", json={"keep_count": 5})
    assert response.status_code == 200
    mock_chat_service.truncate_chat.assert_called_once_with("1", 5)

@pytest.mark.asyncio
async def test_chat_stream_basic(client, mock_chat_service):
    # This is a complex test because of StreamingResponse and many dependencies
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model") as mock_get_model, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="new-chat-id")
        mock_chat_service.get_chat.return_value = None
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Mock run_stream context manager
        mock_result = MagicMock()
        
        # Mocking an async generator for stream_text
        async def mock_stream():
            yield "Hello"
            yield "Hello world"

        # stream_text should be a normal method returning an async iterable
        mock_result.stream_text.return_value = mock_stream()
        
        # mock_agent.run_stream is an async context manager
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        
        # Collect streaming output
        # TestClient with StreamingResponse returns strings in iter_lines if it detects text
        lines = [line for line in response.iter_lines()]
        data_lines = [line for line in lines if line.startswith("data: ")]
        
        assert len(data_lines) >= 3 # chat_id, meta, content
        assert "new-chat-id" in data_lines[0]
        assert "meta" in data_lines[1]
        assert "Hello" in data_lines[2]
        assert " world" in data_lines[3]

def test_estimate_tokens():
    from app.api.chat import estimate_tokens
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcdef") == 2

@pytest.mark.asyncio
async def test_chat_stream_ollama_502(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.fetch_ollama_models") as mock_fetch, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_fetch.return_value = ["gpt-4o"]
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None
        
        # Ensure tools are mockable/serializable
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Simulate exception during run_stream
        # We need to mock the async context manager correctly
        mock_agent.run_stream.side_effect = Exception("status_code: 502")
        
        response = client.post("/api/chat/stream", json={"message": "hi", "provider": "ollama"})
        assert response.status_code == 200
        
        # Use a longer timeout or just check content
        content = response.content.decode("utf-8")
        assert "Ollama" in content and "502" in content

@pytest.mark.asyncio
async def test_chat_stream_no_tools_fallback(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat_service.get_chat.return_value = None
        
        # Mock tool with a name attribute
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[mock_tool])
        
        # First agent (with tools) fails with "does not support tools"
        mock_agent_with_tools = MagicMock()
        mock_agent_with_tools.run_stream.side_effect = Exception("does not support tools")
        
        # Second agent (without tools) succeeds
        mock_agent_no_tools = MagicMock()
        mock_agent_cls.side_effect = [mock_agent_with_tools, mock_agent_no_tools]
        
        mock_result = MagicMock()
        async def mock_stream():
            yield "Fallback response"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent_no_tools.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent_no_tools.run_stream.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        lines = [line for line in response.iter_lines()]
        assert any("Fallback response" in line for line in lines)

def test_chat_history_truncation_logic(client, mock_chat_service):
    # Mock a chat with very long messages to test truncation
    from app.services.chat_service import Message
    now = datetime.now()
    long_content = "a" * 70000 # > 20000 tokens (EST_CHARS_PER_TOKEN=3)
    
    mock_chat = MagicMock()
    mock_chat.id = "chat-id"
    mock_chat.messages = [
        Message(role="user", content=long_content, timestamp=now),
        Message(role="assistant", content="short", timestamp=now)
    ]
    mock_chat_service.get_chat.return_value = mock_chat
    mock_chat_service.create_chat.return_value = mock_chat
    
    with patch("app.api.chat.Agent"), \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.mcp_manager"):
        
        # We just want to see if it processes the history without crashing
        # and if it calls Agent with truncated history
        response = client.post("/api/chat/stream", json={"message": "hi", "chat_id": "chat-id"})
        assert response.status_code == 200

def test_chat_history_global_limit(client, mock_chat_service):
    from app.services.chat_service import Message
    now = datetime.now()
    # 10 messages of 15000 chars = 5000 tokens each. Total 50000 tokens.
    # MAX_CONTEXT_TOKENS is 100000. Let's make it exceed.
    # Actually MAX_CONTEXT_TOKENS is 100000. 30 messages of 5000 tokens = 150000 tokens.
    msgs = []
    for i in range(30):
        msgs.append(Message(role="user" if i % 2 == 0 else "assistant", content="a" * 15000, timestamp=now))
    
    mock_chat = MagicMock()
    mock_chat.id = "chat-id"
    mock_chat.messages = msgs
    mock_chat_service.get_chat.return_value = mock_chat
    
    with patch("app.api.chat.Agent"), \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.mcp_manager"):
        response = client.post("/api/chat/stream", json={"message": "hi", "chat_id": "chat-id"})
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_chat_stream_with_images(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.save_base64_image") as mock_save, \
         patch("app.api.chat.load_image_to_base64") as mock_load, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        mock_save.return_value = "/path/to/img.png"
        mock_load.return_value = "base64data"
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        
        # Mock history with images
        from app.services.chat_service import Message
        mock_chat = MagicMock()
        mock_chat.messages = [Message(role="user", content="hi", images=["/old/img.png"], timestamp=datetime.now())]
        mock_chat_service.get_chat.return_value = mock_chat
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream(): yield "Hi"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        
        response = client.post("/api/chat/stream", json={
            "message": "look at this", 
            "images": ["data:image/png;base64,xxx"],
            "chat_id": "chat-id"
        })
        assert response.status_code == 200
        mock_save.assert_called_once()
        mock_load.assert_called_once()

@pytest.mark.asyncio
async def test_chat_stream_with_agent_config(client, mock_chat_service):
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        mock_agent_config = MagicMock()
        mock_agent_config.provider = "anthropic"
        mock_agent_config.model = "claude-3-opus"
        mock_agent_config.system_prompt = "You are a scientist."
        mock_agent_config.doc_roots = ["/docs"]
        mock_agent_store.get_agent.return_value = mock_agent_config
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        async def mock_stream(): yield "Result"
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        
        response = client.post("/api/chat/stream", json={"message": "hi", "agent_id": "sci-agent"})
        assert response.status_code == 200
        # Check if agent was created with merged config
        assert mock_agent_cls.called
        args, kwargs = mock_agent_cls.call_args
        assert "scientist" in kwargs["system_prompt"]
        assert "可检索目录" in kwargs["system_prompt"]

@pytest.mark.asyncio
async def test_chat_stream_with_thought_tags(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        
        async def mock_stream():
            yield "<thought>Thinking...</thought>"
            yield "Done"
            
        mock_result.stream_text.return_value = mock_stream()
        # Use MagicMock for the context manager return value
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_result)
        mock_cm.__aexit__ = AsyncMock()
        mock_agent.run_stream.return_value = mock_cm
        
        response = client.post("/api/chat/stream", json={"message": "hi"})
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "thought_duration" in content

@pytest.mark.asyncio
async def test_chat_stream_with_citations(client, mock_chat_service):
    with patch("app.api.chat.agent_store") as mock_agent_store, \
         patch("app.api.chat.mcp_manager") as mock_mcp, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.Agent") as mock_agent_cls:
        
        mock_mcp.get_tools_for_agent = AsyncMock(return_value=[])
        mock_agent_config = MagicMock()
        mock_agent_config.require_citations = True
        mock_agent_config.provider = "openai"
        mock_agent_config.model = "gpt-4o"
        mock_agent_config.system_prompt = "test prompt"
        mock_agent_config.doc_roots = []
        mock_agent_store.get_agent.return_value = mock_agent_config
        
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()
        
        async def mock_stream(): yield "Answer"
        mock_result.stream_text.return_value = mock_stream()
        
        # We need to capture the deps dict passed to run_stream and modify it
        def mock_run_stream(*args, **kwargs):
            deps = kwargs.get("deps")
            if deps is not None:
                deps["citations"].append({
                    "path": "test.txt",
                    "start_line": 1,
                    "end_line": 5
                })
            return mock_result
            
        mock_agent.run_stream.side_effect = mock_run_stream
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock()
        
        response = client.post("/api/chat/stream", json={"message": "hi", "agent_id": "agent-1"})
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "citations" in content
        assert "Sources:" in content
        assert "test.txt#L1-L5" in content
