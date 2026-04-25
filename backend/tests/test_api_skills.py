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


def test_api_skills_module_does_not_expose_runtime_singletons():
    # Stage 4-Lite closeout: API module should resolve runtime deps via context seam.
    assert not hasattr(skills_module, "skill_registry")
    assert not hasattr(skills_module, "skill_router")
    assert not hasattr(skills_module, "config_service")
    assert not hasattr(skills_module, "agent_store")


def test_api_reload_skills(client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "legacy")
    response = client.post("/api/skills/reload")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_api_reload_skills_layered_reload(client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "legacy")
    with patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_load_all = mock_context.return_value.skill_registry.load_all
        mock_context.return_value.skill_registry.list_skills.return_value = []
        response = client.post("/api/skills/reload?layer=user")
        assert response.status_code == 200
        mock_load_all.assert_called_once_with(layer="user")


def test_api_reload_skills_rejected_in_import_gate_mode(client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import-gate")
    response = client.post("/api/skills/reload")
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_reload_unavailable_in_import_gate_mode"


def test_api_reload_skills_import_gate_short_circuits_before_runtime_context(client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import-gate")
    with patch("app.api.skills.get_stage4_lite_runtime_context", side_effect=AssertionError("should not be called")):
        response = client.post("/api/skills/reload")
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_reload_unavailable_in_import_gate_mode"


def test_api_reload_skills_rejected_in_static_readonly_mode(client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "legacy")
    monkeypatch.setenv("YUE_SKILL_RUNTIME_STATIC_READONLY", "true")
    with patch("app.api.skills.get_stage4_lite_runtime_context", side_effect=AssertionError("should not be called")):
        response = client.post("/api/skills/reload")
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_reload_unavailable_in_static_readonly_mode"


@pytest.mark.parametrize(
    "runtime_mode, expected_status",
    [
        ("legacy", 200),
        ("import-gate", 409),
    ],
)
def test_api_reload_hybrid_mode_matrix(runtime_mode, expected_status, client, monkeypatch):
    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", runtime_mode)

    if runtime_mode == "legacy":
        with patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
            mock_context.return_value.skill_registry.load_all.return_value = None
            mock_context.return_value.skill_registry.list_skills.return_value = []
            response = client.post("/api/skills/reload")
            assert response.status_code == expected_status
            mock_context.return_value.skill_registry.load_all.assert_called_once_with(layer="all")
        return

    with patch("app.api.skills.get_stage4_lite_runtime_context", side_effect=AssertionError("should not be called")):
        response = client.post("/api/skills/reload")
    assert response.status_code == expected_status

def test_api_list_skills_source_layer(client):
    skill = SkillSpec(
        name="layered-skill",
        version="1.0.0",
        description="layered",
        capabilities=["layered"],
        entrypoint="system_prompt",
        source_layer="user",
        source_dir="/tmp/user-skills"
    )
    fake_registry = type("FakeRegistry", (), {})()
    fake_registry._skills = {"layered-skill": {"1.0.0": skill}}
    fake_registry._latest_versions = {"layered-skill": "1.0.0"}
    fake_registry.list_skills = lambda: [skill]
    with patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_context.return_value.skill_registry = fake_registry
        response = client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["source_layer"] == "user"
        assert data[0]["source_dir"] == "/tmp/user-skills"

def test_api_list_skill_summaries_source_layer(client):
    skill = SkillSpec(
        name="layered-skill",
        version="1.0.0",
        description="layered",
        capabilities=["layered"],
        entrypoint="system_prompt",
        source_layer="user",
        source_dir="/tmp/user-skills"
    )
    summary = type("Summary", (), {"name": "layered-skill", "description": "layered", "capabilities": ["layered"], "availability": True, "source_layer": "user", "source_dir": "/tmp/user-skills"})()
    fake_registry = type("FakeRegistry", (), {})()
    fake_registry._skills = {"layered-skill": {"1.0.0": skill}}
    fake_registry._latest_versions = {"layered-skill": "1.0.0"}
    fake_registry.list_summaries = lambda: [summary]
    with patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_context.return_value.skill_registry = fake_registry
        response = client.get("/api/skills/summary")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["source_layer"] == "user"
        assert data[0]["source_dir"] == "/tmp/user-skills"

def test_api_tool_select_runtime_skill_not_found(client):
    payload = {
        "agent_id": "non-existent",
        "task": "test"
    }
    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 404

def test_api_tool_select_runtime_skill_no_agent_skills(client):
    # builtin-architect usually has no visible_skills by default
    payload = {
        "agent_id": "builtin-architect",
        "task": "test"
    }
    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        assert response.json()["selected_skill"] is None
        assert response.json()["fallback_used"] is True

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

    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }), \
        patch("app.api.skills._get_agent", return_value=fake_agent), \
        patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_context.return_value.skill_router.route.return_value = fake_skill
        mock_context.return_value.skill_router.route_with_contract.return_value = {"fallback_used": False}
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["selected_skill"] == {"name": "planner", "version": "1.0.0"}
        assert data["reason_code"] == "skill_selected"
        assert data["fallback_used"] is False
        assert set(data.keys()) == {"selected_skill", "reason_code", "fallback_used"}

def test_api_tool_select_runtime_skill_fallback_contract(client):
    payload = {
        "agent_id": "skill-agent",
        "task": "write a greeting",
        "mode": "hybrid",
    }
    fake_agent = AgentConfig(
        id="skill-agent",
        name="Skill Agent",
        system_prompt="agent",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read", "builtin:exec"],
        skill_mode="auto",
        visible_skills=["planner:1.0.0"]
    )

    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }), \
        patch("app.api.skills._get_agent", return_value=fake_agent):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["selected_skill"] is None
        assert data["reason_code"] == "no_matching_skill"
        assert data["fallback_used"] is True
        assert set(data.keys()) == {"selected_skill", "reason_code", "fallback_used"}


def test_api_tool_select_runtime_skill_default_contract_excludes_debug_fields(client):
    payload = {
        "agent_id": "builtin-architect",
        "task": "test",
    }
    debug_fields = {
        "selected",
        "candidates",
        "scores",
        "reason",
        "stage_trace",
        "selection_mode",
        "effective_tools",
    }
    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert debug_fields.isdisjoint(data.keys())


def test_api_tool_select_runtime_skill_includes_debug_fields_when_flag_enabled(client):
    payload = {
        "agent_id": "builtin-architect",
        "task": "test",
    }
    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
        "skill_runtime_debug_contract_enabled": True,
    }):
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "selection_mode" in data
        assert "effective_tools" in data

def test_api_tool_select_runtime_skill_preserves_agent_tools_when_allowed_tools_is_none(client):
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

    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }), \
        patch("app.api.skills._get_agent", return_value=fake_agent), \
        patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_context.return_value.skill_router.route.return_value = fake_skill
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["selected_skill"] == {"name": "planner", "version": "1.0.0"}
        assert data["reason_code"] == "skill_selected"
        assert data["fallback_used"] is False

def test_api_tool_select_runtime_skill_blocks_all_tools_when_allowed_tools_is_empty_list(client):
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

    with patch("app.api.skills._feature_flags", return_value={
        "skill_runtime_enabled": True,
    }), \
        patch("app.api.skills._get_agent", return_value=fake_agent), \
        patch("app.api.skills.get_stage4_lite_runtime_context") as mock_context:
        mock_context.return_value.skill_router.route.return_value = fake_skill
        response = client.post("/api/skills/tool/select_runtime_skill", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["selected_skill"] == {"name": "planner", "version": "1.0.0"}
        assert data["reason_code"] == "skill_selected"
        assert data["fallback_used"] is False
