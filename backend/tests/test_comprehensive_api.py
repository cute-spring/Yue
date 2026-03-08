import pytest
import unittest
import requests
import json
import os
import time
from app.services.llm.registry import register_provider, unregister_provider
from app.services.llm.base import SimpleProvider
from pydantic_ai.models.test import TestModel

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8003")

def _backend_available() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/api/mcp/status", timeout=1)
        return r.status_code >= 200
    except Exception:
        return False

if not _backend_available():
    raise unittest.SkipTest("Backend not running")

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

def test_skills_availability_api():
    if os.environ.get("RUN_HTTP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_HTTP_INTEGRATION_TESTS=1 to enable HTTP integration tests.")
    r = requests.get(f"{BASE_URL}/api/skills")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "availability" in data[0]
        assert "missing_requirements" in data[0]

    r = requests.get(f"{BASE_URL}/api/skills/summary")
    assert r.status_code == 200
    summary = r.json()
    assert isinstance(summary, list)
    if summary:
        assert "name" in summary[0]
        assert "description" in summary[0]
        assert "availability" in summary[0]
        assert "source_path" in summary[0]

def test_skills_select_infers_requested_skill_from_message():
    if os.environ.get("RUN_HTTP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_HTTP_INTEGRATION_TESTS=1 to enable HTTP integration tests.")
    create_payload = {
        "name": "Skill Select Integration Agent",
        "system_prompt": "integration agent",
        "provider": "openai",
        "model": "gpt-4o",
        "enabled_tools": [],
        "skill_mode": "auto",
        "visible_skills": ["backend-api-debugger:1.0.0", "release-test-planner:1.0.0"],
    }
    r = requests.post(f"{BASE_URL}/api/agents", json=create_payload, timeout=30)
    assert r.status_code == 200, r.text
    agent = r.json()
    agent_id = agent["id"]
    try:
        select_payload = {
            "agent_id": agent_id,
            "task": "请使用 backend-api-debugger 来排查这个 500 错误",
            "mode": "auto",
        }
        sr = requests.post(f"{BASE_URL}/api/skills/select", json=select_payload, timeout=30)
        assert sr.status_code == 200, sr.text
        selected = sr.json()
        assert selected["reason_code"] == "skill_selected"
        assert selected["selected_skill"]["name"] == "backend-api-debugger"
    finally:
        requests.delete(f"{BASE_URL}/api/agents/{agent_id}", timeout=30)

def test_chat_stream_emits_skill_effectiveness_event_http():
    if os.environ.get("RUN_HTTP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_HTTP_INTEGRATION_TESTS=1 to enable HTTP integration tests.")
    create_payload = {
        "name": "Skill Stream Integration Agent",
        "system_prompt": "integration agent",
        "provider": "openai",
        "model": "gpt-4o",
        "enabled_tools": [],
        "skill_mode": "auto",
        "visible_skills": ["pdf-insight-extractor:1.0.0", "release-test-planner:1.0.0"],
    }
    r = requests.post(f"{BASE_URL}/api/agents", json=create_payload, timeout=30)
    assert r.status_code == 200, r.text
    agent = r.json()
    agent_id = agent["id"]
    try:
        payload = {
            "agent_id": agent_id,
            "message": "请使用 pdf-insight-extractor 提取 PDF 要点",
        }
        with requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True, timeout=60) as sr:
            assert sr.status_code == 200, sr.text
            effect_event = None
            for line in sr.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                try:
                    body = json.loads(line[6:])
                except Exception:
                    continue
                if body.get("event") == "skill_effectiveness":
                    effect_event = body
                    break
            assert effect_event is not None
            assert effect_event["reason_code"] in {"skill_selected", "no_matching_skill"}
            assert "system_prompt_tokens_estimate" in effect_event
    finally:
        requests.delete(f"{BASE_URL}/api/agents/{agent_id}", timeout=30)

def test_chat_skill_effectiveness_report_api():
    if os.environ.get("RUN_HTTP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_HTTP_INTEGRATION_TESTS=1 to enable HTTP integration tests.")
    r = requests.get(f"{BASE_URL}/api/chat/skill-effectiveness/report", params={"hours": 24}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "total_runs" in data
    assert "skill_hit_rate" in data
    assert "fallback_rate" in data
    assert "avg_system_prompt_tokens" in data

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
