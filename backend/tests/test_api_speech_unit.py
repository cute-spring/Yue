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
