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
