import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_mcp_manager():
    with patch("app.api.mcp.mcp_manager") as mock:
        # Patch the CONFIG_PATH that was imported in app.api.mcp
        with patch("app.api.mcp.CONFIG_PATH", "/tmp/mcp_config.json"):
            mock.config_path = "/tmp/mcp_config.json"
            yield mock

def test_list_configs(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "server1"}]
    response = client.get("/api/mcp/")
    assert response.status_code == 200
    assert response.json() == [{"name": "server1"}]

@pytest.mark.asyncio
async def test_list_tools(client, mock_mcp_manager):
    mock_mcp_manager.get_available_tools = AsyncMock(return_value=[{"name": "tool1"}])
    response = client.get("/api/mcp/tools")
    assert response.status_code == 200
    assert response.json() == [{"name": "tool1"}]

def test_get_status(client, mock_mcp_manager):
    mock_mcp_manager.get_status.return_value = {"server1": "connected"}
    response = client.get("/api/mcp/status")
    assert response.status_code == 200
    assert response.json() == {"server1": "connected"}

def test_update_configs_success(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = []
    m = mock_open()
    with patch("app.api.mcp.open", m):
        new_config = {
            "name": "new_server",
            "command": "node",
            "args": ["server.js"],
            "transport": "stdio"
        }
        response = client.post("/api/mcp/", json=[new_config])
        assert response.status_code == 200
        # Check if json.dump was called
        m.assert_called_with(mock_mcp_manager.config_path, 'w')

def test_update_configs_invalid(client, mock_mcp_manager):
    response = client.post("/api/mcp/", json=[{"name": "missing_command"}])
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_reload_mcp(client, mock_mcp_manager):
    mock_mcp_manager.cleanup = AsyncMock()
    mock_mcp_manager.initialize = AsyncMock()
    response = client.post("/api/mcp/reload")
    assert response.status_code == 200
    assert response.json() == {"status": "reloaded"}
    mock_mcp_manager.cleanup.assert_called_once()
    mock_mcp_manager.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_delete_config_success(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "target"}, {"name": "other"}]
    m = mock_open()
    with patch("app.api.mcp.open", m):
        mock_mcp_manager.cleanup = AsyncMock()
        mock_mcp_manager.initialize = AsyncMock()
        response = client.delete("/api/mcp/target")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        m.assert_called_with(mock_mcp_manager.config_path, 'w')

def test_delete_config_not_found(client, mock_mcp_manager):
    mock_mcp_manager.load_config.return_value = [{"name": "other"}]
    response = client.delete("/api/mcp/non_existent")
    assert response.status_code == 404
