import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app
from app.services.agent_store import AgentConfig
import json

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_agent_store():
    with patch("app.api.agents.agent_store") as mock:
        yield mock

@pytest.fixture
def mock_mcp_manager():
    with patch("app.api.agents.mcp_manager") as mock:
        yield mock

def test_list_agents(client, mock_agent_store):
    mock_agent_store.list_agents.return_value = [
        AgentConfig(id="1", name="Agent 1", system_prompt="Prompt 1")
    ]
    response = client.get("/api/agents/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "1"

def test_get_agent_success(client, mock_agent_store):
    mock_agent_store.get_agent.return_value = AgentConfig(id="1", name="Agent 1", system_prompt="Prompt 1")
    response = client.get("/api/agents/1")
    assert response.status_code == 200
    assert response.json()["id"] == "1"

def test_get_agent_not_found(client, mock_agent_store):
    mock_agent_store.get_agent.return_value = None
    response = client.get("/api/agents/999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_agent(client, mock_agent_store, mock_mcp_manager):
    mock_mcp_manager.get_available_tools = AsyncMock(return_value=[])
    agent_data = {"name": "New Agent", "system_prompt": "Test Prompt", "enabled_tools": []}
    mock_agent_store.create_agent.return_value = AgentConfig(id="new-id", **agent_data)
    
    response = client.post("/api/agents/", json=agent_data)
    assert response.status_code == 200
    assert response.json()["id"] == "new-id"

def test_delete_agent_success(client, mock_agent_store):
    mock_agent_store.delete_agent.return_value = True
    response = client.delete("/api/agents/1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_delete_agent_not_found(client, mock_agent_store):
    mock_agent_store.delete_agent.return_value = False
    response = client.delete("/api/agents/999")
    assert response.status_code == 404

# Testing utility functions via endpoints or directly
from app.api.agents import _normalize_enabled_tools, _extract_json_object, _classify_tool_risk

def test_normalize_enabled_tools():
    available = [{"name": "tool1", "id": "srv:tool1"}, {"name": "tool2", "id": "srv:tool2"}]
    # Case 1: Already normalized
    assert _normalize_enabled_tools(["srv:tool1"], available) == ["srv:tool1"]
    # Case 2: Short name, unique
    assert _normalize_enabled_tools(["tool1"], available) == ["srv:tool1"]
    # Case 3: Short name, not unique or not found
    assert _normalize_enabled_tools(["unknown"], available) == ["unknown"]

def test_extract_json_object():
    # Case 1: Pure JSON
    assert _extract_json_object('{"a": 1}') == {"a": 1}
    # Case 2: Markdown fenced
    assert _extract_json_object('Some text ```json\n{"a": 1}\n``` other text') == {"a": 1}
    # Case 3: Embedded JSON
    assert _extract_json_object('Here is the result: {"a": 1} Hope it helps.') == {"a": 1}
    # Case 4: Invalid
    with pytest.raises(ValueError):
        _extract_json_object('No json here')

def test_classify_tool_risk():
    assert _classify_tool_risk("srv:fetch", {"name": "fetch"}) == "network"
    assert _classify_tool_risk("builtin:docs_read", {}) == "read"
    assert _classify_tool_risk("srv:write_file", {}) == "write"
    assert _classify_tool_risk("unknown", {}) == "unknown"

@pytest.mark.asyncio
async def test_generate_agent_basic(client, mock_mcp_manager):
    mock_mcp_manager.get_available_tools = AsyncMock(return_value=[
        {"id": "srv:tool1", "name": "tool1", "description": "search something", "server": "srv"}
    ])
    
    with patch("app.api.agents.get_model") as mock_get_model, \
         patch("app.api.agents.Agent") as mock_agent_cls:
        
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        
        # Mock run_stream
        async def mock_stream():
            yield '{"name": "Generated Agent", "system_prompt": "You are a helper", "enabled_tools": ["tool1"], "tool_reasons": {"tool1": "needed"}}'
        
        mock_result = MagicMock()
        mock_result.stream_text.return_value = mock_stream()
        mock_agent.run_stream.return_value.__aenter__ = AsyncMock(return_value=mock_result)
        mock_agent.run_stream.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/agents/generate", json={"description": "Make me a helper agent"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Generated Agent"
        assert data["recommended_tools"] == ["srv:tool1"]
        assert "srv:tool1" in data["tool_reasons"]
        assert data["tool_risks"]["srv:tool1"] == "read" # tool1 has "read" risk by default if no other keywords
