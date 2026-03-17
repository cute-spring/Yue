import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.chat_service import Message


@pytest.fixture
def client():
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


@pytest.fixture
def mock_chat_service():
    with patch("app.api.chat.chat_service") as mock:
        mock.get_session_skill.return_value = (None, None)
        yield mock


@pytest.mark.asyncio
async def test_multimodal_history_replay_keeps_images(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.load_image_to_base64", return_value="data:image/png;base64,QUJDRA==") as mock_load, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat = MagicMock()
        mock_chat.messages = [
            Message(role="user", content="history", images=["/files/old.png"], timestamp=datetime.now()),
        ]
        mock_chat_service.get_chat.return_value = mock_chat

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def mock_stream():
            yield "ok"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "new", "chat_id": "chat-id"})
        assert response.status_code == 200
        assert any("ok" in line for line in response.iter_lines())
        mock_load.assert_called_once_with("/files/old.png")


@pytest.mark.asyncio
async def test_multimodal_missing_history_image_falls_back_without_crash(client, mock_chat_service):
    with patch("app.api.chat.agent_store"), \
         patch("app.api.chat.tool_registry") as mock_registry, \
         patch("app.api.chat.get_model"), \
         patch("app.api.chat.load_image_to_base64", return_value="/files/missing.png") as mock_load, \
         patch("app.api.chat.Agent") as mock_agent_cls:
        mock_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])
        mock_chat_service.create_chat.return_value = MagicMock(id="chat-id")
        mock_chat = MagicMock()
        mock_chat.messages = [
            Message(role="user", content="history", images=["/files/missing.png"], timestamp=datetime.now()),
        ]
        mock_chat_service.get_chat.return_value = mock_chat

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_result = MagicMock()

        async def mock_stream():
            yield "ok"

        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/chat/stream", json={"message": "new", "chat_id": "chat-id"})
        assert response.status_code == 200

        payloads = []
        for line in response.iter_lines():
            if isinstance(line, str) and line.startswith("data: "):
                try:
                    payloads.append(json.loads(line[6:]))
                except Exception:
                    pass
        assert any("meta" in p for p in payloads)
        mock_load.assert_called_once_with("/files/missing.png")
