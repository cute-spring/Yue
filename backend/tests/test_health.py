import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime_seconds" in data
    assert "mcp" in data
    assert "llm" in data
    assert "system" in data

@pytest.mark.asyncio
async def test_health_monitor_reconnect():
    from app.services.health_monitor import HealthMonitor
    from app.mcp.manager import mcp_manager
    
    monitor = HealthMonitor(interval_seconds=1)
    
    mock_config = [{"name": "test-server", "enabled": True, "command": "node"}]
    with patch.object(mcp_manager, "load_config", return_value=mock_config), \
         patch.object(mcp_manager, "sessions", {}), \
         patch.object(mcp_manager, "connect_to_server", new_callable=AsyncMock) as mock_connect:
        
        await monitor._perform_checks()
        # Should call connect_to_server because it's enabled but not in sessions
        assert mock_connect.called

def test_health_endpoint_reports_degraded_when_mcp_offline(client):
    mocked_health = {
        "timestamp": 1234567890.0,
        "mcp_initializing": False,
        "mcp_servers": [
            {"name": "legacy-mcp", "status": "offline", "version": "unknown", "error": "Connection timeout"}
        ],
        "llm_providers": [
            {"provider": "openai", "configured": True, "status": "online"}
        ],
    }
    with patch("app.api.health.health_monitor.get_health_data", return_value=mocked_health), \
         patch("app.api.health.psutil.Process") as mock_process:
        mock_process.return_value.memory_info.return_value.rss = 1024 * 1024 * 100
        mock_process.return_value.cpu_percent.return_value = 0.0
        response = client.get("/api/health/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["mcp"]["status"] == "error"
    assert payload["mcp"]["servers"][0]["name"] == "legacy-mcp"
