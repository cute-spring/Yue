import pytest
import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.services.chat_service import ChatService

@pytest.fixture
def temp_chat_service():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    test_engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with patch("app.services.chat_service.engine", test_engine), \
         patch("app.services.chat_service.SessionLocal", TestingSessionLocal), \
         patch("app.services.chat_service.DATA_DIR", temp_dir):
        service = ChatService()
        yield service

    test_engine.dispose()
    shutil.rmtree(temp_dir)

@pytest.fixture
def client(temp_chat_service):
    try:
        with patch("app.api.chat.chat_service", temp_chat_service):
            return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")

@pytest.mark.asyncio
async def test_chat_integration_flow(client, temp_chat_service):
    # Mock Agent in app.api.chat
    with patch("app.api.chat.Agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Mock run_stream
        mock_result = MagicMock()
        
        # We need an async context manager for run_stream
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return mock_result
            async def __aexit__(self, exc_type, exc, tb):
                pass
        
        mock_agent.run_stream.return_value = AsyncContextManagerMock()
        
        # Mock stream_text generator
        async def mock_stream_text():
            yield "Hello"
            yield "Hello world"
            
        mock_result.stream_text.return_value = mock_stream_text()
        
        # 1. Send chat request
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "Hi",
                "model": "gpt-4",
                "agent_id": "default"
            }
        )
        assert response.status_code == 200
        
        # 2. Read streaming response
        lines = [line for line in response.iter_lines() if line]
        assert len(lines) > 0
        # First line should be chat_id
        assert "chat_id" in lines[0]
        # Later lines should contain "Hello" and "world"
        assert any("Hello" in line for line in lines)
        assert any("world" in line for line in lines)
        
        # 3. Verify DB record
        chats = temp_chat_service.list_chats()
        assert len(chats) > 0
        assert chats[0].messages[0].content == "Hi"

@pytest.mark.asyncio
async def test_chat_history_and_deletion(client, temp_chat_service):
    # 1. Create a session via chat_service directly or via API
    # Since we are testing integration, let's use the chat_service to seed data
    session = temp_chat_service.create_chat(agent_id="default")
    session_id = session.id
    
    temp_chat_service.add_message(session_id, "user", "Hello")
    temp_chat_service.add_message(session_id, "assistant", "Hi there")
    
    # 2. Get history
    response = client.get(f"/api/chat/{session_id}")
    assert response.status_code == 200
    history = response.json()
    assert history["id"] == session_id
    assert len(history["messages"]) == 2
    
    # 3. List sessions
    response = client.get("/api/chat/history")
    assert response.status_code == 200
    sessions = response.json()
    assert any(s["id"] == session_id for s in sessions)
    
    # 4. Delete session
    response = client.delete(f"/api/chat/{session_id}")
    assert response.status_code == 200
    
    # 5. Verify deletion
    response = client.get(f"/api/chat/{session_id}")
    assert response.status_code == 404
