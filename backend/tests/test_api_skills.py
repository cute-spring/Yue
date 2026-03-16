import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.api import skills as skills_module
from app.services.skill_service import SkillSpec, SkillConstraints
from app.services.agent_store import AgentConfig

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(skills_module.router, prefix="/api/skills")
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")

def test_api_list_skills(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "availability" in data[0]
        assert "missing_requirements" in data[0]

def test_api_list_skill_summaries(client):
    response = client.get("/api/skills/summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "name" in data[0]
        assert "description" in data[0]
        assert "availability" in data[0]

def test_api_reload_skills(client):
    response = client.post("/api/skills/reload")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_api_select_skill_not_found(client):
    payload = {
        "agent_id": "non-existent",
        "task": "test"
    }
    response = client.post("/api/skills/select", json=payload)
    assert response.status_code == 404

def test_api_select_skill_no_agent_skills(client):
    # builtin-architect usually has no visible_skills by default
    payload = {
        "agent_id": "builtin-architect",
        "task": "test"
    }
    response = client.post("/api/skills/select", json=payload)
    assert response.status_code == 200
    assert response.json()["selected_skill"] is None
    assert response.json()["fallback_used"] is True

def test_api_tool_select_runtime_skill_disabled(client):
    payload = {
        "agent_id": "builtin-architect",
        "task": "pick a skill",
        "mode": "hybrid"
    }
    with patch("app.api.skills.config_service.get_feature_flags", return_value={
        "skill_runtime_enabled": True,
        "skill_selector_tool_enabled": False,
        "skill_auto_mode_enabled": True
    }):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 403
        assert response.json()["detail"] == "skill_selector_disabled"

def test_api_tool_select_runtime_skill_success(client):
    payload = {
        "agent_id": "skill-agent",
        "task": "design a plan",
        "mode": "manual",
        "requested_skill": "planner:1.0.0"
    }
    fake_agent = AgentConfig(
        id="skill-agent",
        name="Skill Agent",
        system_prompt="agent",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read", "builtin:exec"],
        skill_mode="manual",
        visible_skills=["planner:1.0.0"]
    )
    fake_skill = SkillSpec(
        name="planner",
        version="1.0.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        constraints=SkillConstraints(allowed_tools=["builtin:docs_read"])
    )

    with patch("app.api.skills.config_service.get_feature_flags", return_value={
        "skill_runtime_enabled": True,
        "skill_selector_tool_enabled": True,
        "skill_auto_mode_enabled": True
    }), \
        patch("app.api.skills.agent_store.get_agent", return_value=fake_agent), \
        patch("app.api.skills.skill_router.route", return_value=fake_skill):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["selected_skill"] == {"name": "planner", "version": "1.0.0"}
        assert data["reason_code"] == "skill_selected"
        assert data["fallback_used"] is False
        assert data["effective_tools"] == ["builtin:docs_read"]

def test_api_select_skill_preserves_agent_tools_when_allowed_tools_is_none(client):
    payload = {
        "agent_id": "skill-agent",
        "task": "design a plan",
        "mode": "manual",
        "requested_skill": "planner:1.0.0"
    }
    fake_agent = AgentConfig(
        id="skill-agent",
        name="Skill Agent",
        system_prompt="agent",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read", "builtin:exec"],
        skill_mode="manual",
        visible_skills=["planner:1.0.0"]
    )
    fake_skill = SkillSpec(
        name="planner",
        version="1.0.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        constraints=None
    )

    with patch("app.api.skills.agent_store.get_agent", return_value=fake_agent), \
        patch("app.api.skills.skill_router.route", return_value=fake_skill):
        response = client.post("/api/skills/select", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert set(data["effective_tools"]) == {"builtin:docs_read", "builtin:exec"}

def test_api_select_skill_blocks_all_tools_when_allowed_tools_is_empty_list(client):
    payload = {
        "agent_id": "skill-agent",
        "task": "design a plan",
        "mode": "manual",
        "requested_skill": "planner:1.0.0"
    }
    fake_agent = AgentConfig(
        id="skill-agent",
        name="Skill Agent",
        system_prompt="agent",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read", "builtin:exec"],
        skill_mode="manual",
        visible_skills=["planner:1.0.0"]
    )
    fake_skill = SkillSpec(
        name="planner",
        version="1.0.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        constraints=SkillConstraints(allowed_tools=[])
    )

    with patch("app.api.skills.agent_store.get_agent", return_value=fake_agent), \
        patch("app.api.skills.skill_router.route", return_value=fake_skill):
        response = client.post("/api/skills/select", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["effective_tools"] == []
