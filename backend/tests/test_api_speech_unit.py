from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_synthesize_openai_success(client):
    with patch("app.api.speech.speech_service") as mock_speech_service:
        mock_speech_service.synthesize_openai = AsyncMock(return_value=b"fake-mp3")
        response = client.post(
            "/api/speech/synthesize",
            json={"text": "hello world", "engine": "openai", "voice": "alloy", "model": "gpt-4o-mini-tts", "format": "mp3"},
        )
        assert response.status_code == 200
        assert response.content == b"fake-mp3"
        assert response.headers["content-type"].startswith("audio/mpeg")


def test_synthesize_invalid_engine(client):
    response = client.post("/api/speech/synthesize", json={"text": "hello", "engine": "unknown"})
    assert response.status_code == 422


def test_synthesize_openai_missing_key_returns_400(client):
    with patch("app.api.speech.speech_service") as mock_speech_service:
        mock_speech_service.synthesize_openai = AsyncMock(side_effect=ValueError("OPENAI_API_KEY is not configured"))
        response = client.post("/api/speech/synthesize", json={"text": "hello", "engine": "openai"})
        assert response.status_code == 400


def test_issue_stt_token_success(client):
    with patch("app.api.speech.agent_store") as mock_agent_store, patch("app.api.speech.speech_service") as mock_speech_service:
        mock_agent_store.get_agent.return_value = type(
            "Agent",
            (),
            {
                "voice_input_enabled": True,
                "voice_input_provider": "azure",
                "voice_azure_config": {"region": "eastus", "api_key": "secret", "endpoint_id": "endpoint-1"},
            },
        )()
        mock_speech_service.issue_azure_stt_token = AsyncMock(return_value="token-123")

        response = client.get("/api/speech/stt/token", params={"agent_id": "agent-1"})
        assert response.status_code == 200
        assert response.json()["token"] == "token-123"
        assert response.json()["region"] == "eastus"
        assert response.json()["endpoint_id"] == "endpoint-1"


def test_issue_stt_token_requires_azure_provider(client):
    with patch("app.api.speech.agent_store") as mock_agent_store:
        mock_agent_store.get_agent.return_value = type(
            "Agent",
            (),
            {
                "voice_input_enabled": True,
                "voice_input_provider": "browser",
                "voice_azure_config": None,
            },
        )()
        response = client.get("/api/speech/stt/token", params={"agent_id": "agent-1"})
        assert response.status_code == 400


def test_test_stt_config_success(client):
    with patch("app.api.speech.speech_service") as mock_speech_service:
        mock_speech_service.issue_azure_stt_token = AsyncMock(return_value="token-123")
        response = client.post(
            "/api/speech/stt/test",
            json={"provider": "azure", "region": "eastus", "api_key": "secret", "endpoint_id": "endpoint-1"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["region"] == "eastus"


def test_test_stt_config_validation_error(client):
    response = client.post(
        "/api/speech/stt/test",
        json={"provider": "azure", "region": "", "api_key": ""},
    )
    assert response.status_code == 422
