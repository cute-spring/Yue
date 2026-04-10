import pytest
import os
import tempfile
import shutil
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.services.chat_service import ChatService
from app.models.chat import Session as SessionModel, Message as MessageModel
import app.services.chat_service as chat_service_module

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


def test_history_returns_utc_aware_timestamps(client, temp_chat_service):
    session = temp_chat_service.create_chat(agent_id="default")

    # Simulate legacy naive UTC timestamps near day boundary.
    with chat_service_module.SessionLocal() as db:
        row = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert row is not None
        row.created_at = datetime(2026, 4, 10, 17, 30, 0)  # naive UTC
        row.updated_at = datetime(2026, 4, 10, 17, 30, 0)  # naive UTC
        db.commit()

    response = client.get("/api/chat/history")
    assert response.status_code == 200
    sessions = response.json()
    target = next(s for s in sessions if s["id"] == session.id)

    # Contract: API returns timezone-aware UTC timestamps.
    assert target["updated_at"].endswith("+00:00") or target["updated_at"].endswith("Z")
    assert target["created_at"].endswith("+00:00") or target["created_at"].endswith("Z")


def test_timestamp_contract_history_get_chat_and_meta(client, temp_chat_service):
    session = temp_chat_service.create_chat(agent_id="default")
    temp_chat_service.add_message(session.id, "user", "contract test")

    with chat_service_module.SessionLocal() as db:
        row = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        msg = db.query(MessageModel).filter(MessageModel.session_id == session.id).first()
        assert row is not None
        assert msg is not None
        # Simulate legacy naive UTC values.
        row.created_at = datetime(2026, 4, 10, 16, 0, 0)
        row.updated_at = datetime(2026, 4, 10, 16, 30, 0)
        msg.timestamp = datetime(2026, 4, 10, 16, 15, 0)
        db.commit()

    def is_utc_aware(value: str) -> bool:
        return value.endswith("+00:00") or value.endswith("Z")

    history_res = client.get("/api/chat/history")
    assert history_res.status_code == 200
    history = history_res.json()
    target = next(s for s in history if s["id"] == session.id)
    assert is_utc_aware(target["created_at"])
    assert is_utc_aware(target["updated_at"])

    get_res = client.get(f"/api/chat/{session.id}")
    assert get_res.status_code == 200
    chat_payload = get_res.json()
    assert is_utc_aware(chat_payload["created_at"])
    assert is_utc_aware(chat_payload["updated_at"])
    assert len(chat_payload["messages"]) == 1
    assert is_utc_aware(chat_payload["messages"][0]["timestamp"])

    meta_res = client.get(f"/api/chat/{session.id}/meta")
    assert meta_res.status_code == 200
    meta_payload = meta_res.json()
    assert is_utc_aware(meta_payload["updated_at"])


def test_history_date_from_date_to_filters(client, temp_chat_service):
    inside = temp_chat_service.create_chat(agent_id="default")
    outside = temp_chat_service.create_chat(agent_id="default")

    with chat_service_module.SessionLocal() as db:
        in_row = db.query(SessionModel).filter(SessionModel.id == inside.id).first()
        out_row = db.query(SessionModel).filter(SessionModel.id == outside.id).first()
        assert in_row is not None
        assert out_row is not None
        in_row.title = "In Window"
        in_row.updated_at = datetime(2026, 4, 10, 12, 0, 0)
        out_row.title = "Out Window"
        out_row.updated_at = datetime(2026, 4, 8, 12, 0, 0)
        db.commit()

    response = client.get(
        "/api/chat/history",
        params={
            "date_from": "2026-04-10T00:00:00",
            "date_to": "2026-04-10T23:59:59",
        },
    )
    assert response.status_code == 200
    sessions = response.json()
    ids = {s["id"] for s in sessions}
    assert inside.id in ids
    assert outside.id not in ids


def test_history_tag_and_date_combo_filters(client, temp_chat_service):
    api_in = temp_chat_service.create_chat(agent_id="default")
    api_out = temp_chat_service.create_chat(agent_id="default")
    design_in = temp_chat_service.create_chat(agent_id="default")

    with chat_service_module.SessionLocal() as db:
        rows = {
            api_in.id: db.query(SessionModel).filter(SessionModel.id == api_in.id).first(),
            api_out.id: db.query(SessionModel).filter(SessionModel.id == api_out.id).first(),
            design_in.id: db.query(SessionModel).filter(SessionModel.id == design_in.id).first(),
        }
        assert all(v is not None for v in rows.values())
        rows[api_in.id].title = "API In Window"
        rows[api_in.id].tags_json = '["api","backend"]'
        rows[api_in.id].updated_at = datetime(2026, 4, 10, 10, 0, 0)

        rows[api_out.id].title = "API Out Window"
        rows[api_out.id].tags_json = '["api","backend"]'
        rows[api_out.id].updated_at = datetime(2026, 4, 8, 10, 0, 0)

        rows[design_in.id].title = "Design In Window"
        rows[design_in.id].tags_json = '["design","frontend"]'
        rows[design_in.id].updated_at = datetime(2026, 4, 10, 11, 0, 0)
        db.commit()

    response = client.get(
        "/api/chat/history",
        params={
            "tags": "api,backend",
            "tag_mode": "all",
            "date_from": "2026-04-10T00:00:00",
            "date_to": "2026-04-10T23:59:59",
        },
    )
    assert response.status_code == 200
    sessions = response.json()
    ids = {s["id"] for s in sessions}
    assert api_in.id in ids
    assert api_out.id not in ids
    assert design_in.id not in ids
