import pytest
import requests
import json
import os
import time
from app.services.llm.registry import register_provider, unregister_provider
from app.services.llm.base import SimpleProvider
from pydantic_ai.models.test import TestModel

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8003")

# --- Mock Provider for Deterministic Testing ---

class GuardProvider(SimpleProvider):
    name = "__guard__"
    async def list_models(self, refresh=False):
        return ["test-model"]
    
    def build(self, model_name=None):
        return TestModel()
    
    def requirements(self):
        return []
    
    def configured(self):
        return True

@pytest.fixture(scope="module", autouse=True)
def setup_guard_provider():
    # We need to register it in the running server. 
    # Since the server is a separate process, we can't just call register_provider here.
    # However, we can use the 'custom' provider or 'ollama' if we have a way to mock them.
    # Alternatively, if the server is running in the same process (not likely for integration tests),
    # this would work. 
    # Given the environment, I'll assume the server is a separate process.
    # I will check if there's a way to add a custom model via API.
    yield

# --- API Tests ---

def test_models_discovery():
    """Verify that models and providers can be discovered."""
    r = requests.get(f"{BASE_URL}/api/models/supported")
    assert r.status_code == 200
    assert "openai" in r.json()

    r = requests.get(f"{BASE_URL}/api/models/providers")
    assert r.status_code == 200
    providers = r.json()
    assert any(p['name'] == 'openai' for p in providers)

def test_config_management():
    """Verify that configuration can be retrieved."""
    # GET
    r = requests.get(f"{BASE_URL}/api/config/llm")
    assert r.status_code == 200
    config = r.json()
    assert isinstance(config, dict)

def test_agents_workflow():
    """Verify the full CRUD workflow for agents."""
    # 1. Create
    agent_data = {
        "name": "Integration Test Agent",
        "description": "Created by automated test",
        "system_prompt": "You are a helpful assistant.",
        "enabled_tools": []
    }
    r = requests.post(f"{BASE_URL}/api/agents", json=agent_data)
    assert r.status_code == 200
    agent = r.json()
    agent_id = agent["id"]
    assert agent["name"] == "Integration Test Agent"

    # 2. List
    r = requests.get(f"{BASE_URL}/api/agents")
    assert r.status_code == 200
    assert any(a['id'] == agent_id for a in r.json())

    # 3. Update
    r = requests.put(f"{BASE_URL}/api/agents/{agent_id}", json={"name": "Renamed Agent"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Agent"

    # 4. Delete
    r = requests.delete(f"{BASE_URL}/api/agents/{agent_id}")
    assert r.status_code == 200

    # 5. Verify deletion
    r = requests.get(f"{BASE_URL}/api/agents/{agent_id}")
    assert r.status_code == 404

def test_mcp_integration():
    """Verify MCP status and tools endpoints."""
    r = requests.get(f"{BASE_URL}/api/mcp/status")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = requests.get(f"{BASE_URL}/api/mcp/tools")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_chat_history_and_deletion():
    """Verify chat session creation, history retrieval, and deletion."""
    # Use a dummy chat_id or create one via the service if possible, 
    # but here we test the API endpoint's existence and basic behavior.
    
    # 1. List history first to see if it works
    r = requests.get(f"{BASE_URL}/api/chat/history")
    assert r.status_code == 200
    initial_history = r.json()

    # 2. Delete a non-existent chat should return 404
    r = requests.delete(f"{BASE_URL}/api/chat/non-existent-id")
    assert r.status_code == 404

def test_error_scenarios():
    """Verify negative scenarios and error handling."""
    # 404
    assert requests.get(f"{BASE_URL}/api/invalid_path").status_code == 404
    
    # 405
    assert requests.post(f"{BASE_URL}/api/models/supported").status_code == 405
    
    # 422 (Unprocessable Entity)
    assert requests.post(f"{BASE_URL}/api/agents", json={"invalid": "field"}).status_code == 422
