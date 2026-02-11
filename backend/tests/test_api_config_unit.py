import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_config_service():
    with patch("app.api.config.config_service") as mock:
        yield mock

def test_get_full_config(client, mock_config_service):
    mock_config_service.get_config.return_value = {"key": "value"}
    response = client.get("/api/config/")
    assert response.status_code == 200
    assert response.json() == {"key": "value"}

def test_get_llm_config_redacted(client, mock_config_service):
    mock_config_service.get_llm_config.return_value = {
        "openai_api_key": "secret-123",
        "provider": "openai",
        "azure_client_secret": "secret-456",
        "other_param": "visible"
    }
    response = client.get("/api/config/llm")
    assert response.status_code == 200
    data = response.json()
    assert data["openai_api_key"] == ""
    assert data["azure_client_secret"] == ""
    assert data["provider"] == "openai"
    assert data["other_param"] == "visible"

def test_update_llm_config(client, mock_config_service):
    mock_config_service.update_llm_config.return_value = {"status": "ok"}
    response = client.post("/api/config/llm", json={"provider": "ollama"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_config_service.update_llm_config.assert_called_once_with({"provider": "ollama"})

def test_get_preferences(client, mock_config_service):
    mock_config_service.get_preferences.return_value = {"theme": "dark"}
    response = client.get("/api/config/preferences")
    assert response.status_code == 200
    assert response.json() == {"theme": "dark"}

def test_update_preferences(client, mock_config_service):
    mock_config_service.update_preferences.return_value = {"status": "ok"}
    response = client.post("/api/config/preferences", json={"theme": "light"})
    assert response.status_code == 200
    mock_config_service.update_preferences.assert_called_once_with({"theme": "light"})

def test_get_doc_access(client, mock_config_service):
    mock_config_service.get_doc_access.return_value = {"enabled": True}
    response = client.get("/api/config/doc_access")
    assert response.status_code == 200
    assert response.json() == {"enabled": True}

def test_update_doc_access(client, mock_config_service):
    mock_config_service.update_doc_access.return_value = {"status": "ok"}
    response = client.post("/api/config/doc_access", json={"enabled": False})
    assert response.status_code == 200
    mock_config_service.update_doc_access.assert_called_once_with({"enabled": False})
