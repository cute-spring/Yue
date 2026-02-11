import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_model_factory():
    with patch("app.api.models.list_supported_providers") as mock_list_supported, \
         patch("app.api.models.list_providers") as mock_list_providers, \
         patch("app.api.models.get_model") as mock_get_model:
        yield {
            "list_supported": mock_list_supported,
            "list_providers": mock_list_providers,
            "get_model": mock_get_model
        }

@pytest.fixture
def mock_config_service():
    with patch("app.api.models.config_service") as mock:
        yield mock

def test_get_supported_providers(client, mock_model_factory):
    mock_model_factory["list_supported"].return_value = ["openai", "ollama"]
    response = client.get("/api/models/supported")
    assert response.status_code == 200
    assert response.json() == ["openai", "ollama"]

def test_get_providers(client, mock_model_factory):
    mock_model_factory["list_providers"].return_value = [{"name": "openai"}]
    response = client.get("/api/models/providers?refresh=true")
    assert response.status_code == 200
    assert response.json() == [{"name": "openai"}]
    mock_model_factory["list_providers"].assert_called_once_with(refresh=True)

@pytest.mark.asyncio
async def test_reload_env(client, mock_model_factory):
    with patch("app.api.models.load_dotenv") as mock_load:
        mock_model_factory["list_providers"].return_value = [{"name": "openai"}]
        response = client.post("/api/models/reload-env")
        assert response.status_code == 200
        assert response.json()["status"] == "env reloaded"
        mock_load.assert_called_once()

def test_test_provider_success(client, mock_model_factory):
    mock_model_factory["get_model"].return_value = MagicMock()
    response = client.post("/api/models/test/openai", json={"model": "gpt-4"})
    assert response.status_code == 200
    assert response.json() == {"provider": "openai", "ok": True}
    mock_model_factory["get_model"].assert_called_once_with("openai", "gpt-4")

def test_test_provider_unknown(client, mock_model_factory):
    response = client.post("/api/models/test/unknown_provider")
    assert response.status_code == 400
    assert "Unknown provider" in response.json()["detail"]

def test_test_provider_fail(client, mock_model_factory):
    mock_model_factory["get_model"].side_effect = Exception("Config error")
    response = client.post("/api/models/test/openai")
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Config error" in response.json()["error"]

def test_list_custom_models(client, mock_config_service):
    mock_config_service.list_custom_models.return_value = [
        {"name": "custom1", "api_key": "secret-123"}
    ]
    response = client.get("/api/models/custom")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "custom1"
    assert data[0]["api_key"] == ""

def test_create_custom_model(client, mock_config_service):
    mock_config_service.upsert_custom_model.return_value = [{"name": "new_model"}]
    response = client.post("/api/models/custom", json={"name": "new_model"})
    assert response.status_code == 200
    assert response.json() == [{"name": "new_model"}]

def test_update_custom_model(client, mock_config_service):
    mock_config_service.upsert_custom_model.return_value = [{"name": "updated"}]
    response = client.put("/api/models/custom/old_name", json={"config": "val"})
    assert response.status_code == 200
    mock_config_service.upsert_custom_model.assert_called_once_with({"config": "val", "name": "old_name"})

def test_delete_custom_model(client, mock_config_service):
    mock_config_service.delete_custom_model.return_value = []
    response = client.delete("/api/models/custom/target")
    assert response.status_code == 200
    mock_config_service.delete_custom_model.assert_called_once_with("target")

def test_test_custom_model(client, mock_model_factory):
    mock_model_factory["get_model"].return_value = MagicMock()
    response = client.post("/api/models/test/custom", json={"model": "m1"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
