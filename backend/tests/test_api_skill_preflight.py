from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.skills.import_models import SkillPreflightRecord
from app.services.skills.import_service import SkillImportService
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec


def _record(
    *,
    skill_name: str,
    status: str,
    layer: str,
    issues: list[str] | None = None,
) -> SkillPreflightRecord:
    return SkillPreflightRecord(
        skill_name=skill_name,
        skill_version="1.0.0",
        skill_ref=f"{skill_name}:1.0.0",
        source_path=f"/tmp/{skill_name}",
        source_layer=layer,
        status=status,
        issues=issues or [],
        warnings=[],
        suggestions=[],
    )


def _write_skill_package(root, name: str):
    package_dir = root / name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {name}
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are {name}.
""",
        encoding="utf-8",
    )
    return package_dir


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.api import skill_preflight as skill_preflight_module

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    agent_store = _InMemoryAgentStore()
    import_service = SkillImportService(import_store=store, agent_store=agent_store)
    runtime_context = SimpleNamespace(
        skill_import_store=store,
        skill_import_service=import_service,
    )
    monkeypatch.setattr(skill_preflight_module, "get_stage4_lite_runtime_context", lambda: runtime_context)

    app = FastAPI()
    app.include_router(skill_preflight_module.router, prefix="/api/skill-preflight")
    try:
        return TestClient(app), store, agent_store
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def test_list_skill_preflight_with_filters(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records(
        [
            _record(skill_name="ok-skill", status="available", layer="workspace"),
            _record(skill_name="fix-skill", status="needs_fix", layer="user"),
            _record(skill_name="bad-skill", status="unavailable", layer="builtin"),
        ]
    )

    response = test_client.get("/api/skill-preflight?status=needs_fix")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["skill_ref"] == "fix-skill:1.0.0"

    response = test_client.get("/api/skill-preflight?source_layer=workspace")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["skill_ref"] == "ok-skill:1.0.0"


def test_get_skill_preflight_detail(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records([_record(skill_name="detail-skill", status="available", layer="workspace")])

    response = test_client.get("/api/skill-preflight/detail-skill:1.0.0")
    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["skill_ref"] == "detail-skill:1.0.0"
    assert payload["status"] == "available"
    assert payload["mountable"] is True
    assert payload["visible_in_default_agent"] is False
    assert "Ready" in payload["status_message"]


def test_get_skill_preflight_detail_with_actionable_status_for_needs_fix(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records(
        [
            _record(
                skill_name="broken-skill",
                status="needs_fix",
                layer="workspace",
                issues=["missing python binary"],
            )
        ]
    )

    response = test_client.get("/api/skill-preflight/broken-skill:1.0.0")
    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["mountable"] is False
    assert payload["status_message"] == "missing python binary"
    assert "Resolve listed issues" in payload["next_action"]


def test_get_skill_preflight_detail_404(client):
    test_client, _store, _agent_store = client

    response = test_client.get("/api/skill-preflight/not-found:1.0.0")
    assert response.status_code == 404
    assert response.json()["detail"] == "skill_preflight_not_found"


class _InMemoryAgentStore:
    def __init__(self):
        self._agents = {
            "builtin-action-lab": SimpleNamespace(visible_skills=[]),
            "custom-agent": SimpleNamespace(visible_skills=[]),
        }

    def get_agent(self, agent_id: str):
        return self._agents.get(agent_id)

    def update_agent(self, agent_id: str, updates):
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        for key, value in updates.items():
            setattr(agent, key, value)
        return agent


def test_mount_preflight_skill_success_and_idempotent(client):
    test_client, store, agent_store = client
    store.replace_preflight_records([_record(skill_name="mountable-skill", status="available", layer="workspace")])

    first = test_client.post("/api/skill-preflight/mountable-skill:1.0.0/mount", json={})
    assert first.status_code == 200
    assert first.json()["mount_status"] == "mounted"

    second = test_client.post("/api/skill-preflight/mountable-skill:1.0.0/mount", json={})
    assert second.status_code == 200
    assert second.json()["mount_status"] == "already_mounted"
    assert agent_store.get_agent("builtin-action-lab").visible_skills == ["mountable-skill:1.0.0"]


def test_mount_preflight_skill_rejects_non_available_status(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records([_record(skill_name="blocked-skill", status="needs_fix", layer="workspace")])

    response = test_client.post("/api/skill-preflight/blocked-skill:1.0.0/mount", json={})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "skill_preflight_not_mountable"
    assert "Resolve listed issues" in detail["next_action"]


def test_mount_preflight_skill_returns_404_for_missing_agent(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records([_record(skill_name="mountable-skill", status="available", layer="workspace")])

    response = test_client.post(
        "/api/skill-preflight/mountable-skill:1.0.0/mount",
        json={"agent_id": "missing-agent"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "agent_not_found"
    assert "create" in detail["next_action"].lower()


def test_skill_health_api_flow_end_to_end(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records(
        [
            _record(skill_name="ready-skill", status="available", layer="workspace"),
            _record(
                skill_name="needs-fix-skill",
                status="needs_fix",
                layer="workspace",
                issues=["missing cli dependency"],
            ),
            _record(skill_name="hidden-skill", status="unavailable", layer="user"),
        ]
    )

    list_response = test_client.get("/api/skill-preflight")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    by_ref = {item["skill_ref"]: item for item in items}
    assert by_ref["ready-skill:1.0.0"]["status"] == "available"
    assert by_ref["ready-skill:1.0.0"]["mountable"] is True
    assert by_ref["ready-skill:1.0.0"]["visible_in_default_agent"] is False
    assert by_ref["needs-fix-skill:1.0.0"]["status"] == "needs_fix"
    assert by_ref["needs-fix-skill:1.0.0"]["mountable"] is False
    assert by_ref["needs-fix-skill:1.0.0"]["status_message"] == "missing cli dependency"
    assert by_ref["needs-fix-skill:1.0.0"]["next_action"].startswith("Resolve listed issues")

    filtered_response = test_client.get("/api/skill-preflight?status=available&source_layer=workspace")
    assert filtered_response.status_code == 200
    filtered_items = filtered_response.json()["items"]
    assert [item["skill_ref"] for item in filtered_items] == ["ready-skill:1.0.0"]

    blocked_mount = test_client.post("/api/skill-preflight/needs-fix-skill:1.0.0/mount", json={})
    assert blocked_mount.status_code == 422
    blocked_detail = blocked_mount.json()["detail"]
    assert blocked_detail["code"] == "skill_preflight_not_mountable"

    ready_mount = test_client.post("/api/skill-preflight/ready-skill:1.0.0/mount", json={})
    assert ready_mount.status_code == 200
    assert ready_mount.json()["mount_status"] == "mounted"

    mounted_detail = test_client.get("/api/skill-preflight/ready-skill:1.0.0")
    assert mounted_detail.status_code == 200
    assert mounted_detail.json()["item"]["visible_in_default_agent"] is True

    missing_agent_mount = test_client.post(
        "/api/skill-preflight/ready-skill:1.0.0/mount",
        json={"agent_id": "missing-agent"},
    )
    assert missing_agent_mount.status_code == 404
    missing_agent_detail = missing_agent_mount.json()["detail"]
    assert missing_agent_detail["code"] == "agent_not_found"


def test_rescan_skill_preflight_returns_groupable_results_with_unavailable_reasons(client, tmp_path, monkeypatch):
    test_client, store, _agent_store = client
    from app.api import skill_preflight as skill_preflight_module

    skills_dir = tmp_path / "copied-skills"
    _write_skill_package(skills_dir, "ready-skill")
    broken_dir = skills_dir / "broken-skill"
    broken_dir.mkdir(parents=True, exist_ok=True)
    (broken_dir / "SKILL.md").write_text("invalid", encoding="utf-8")

    monkeypatch.setattr(
        skill_preflight_module,
        "_resolve_preflight_directories",
        lambda: [SkillDirectorySpec(layer="workspace", path=str(skills_dir))],
    )

    response = test_client.post("/api/skill-preflight/rescan")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["available"] == 1
    assert payload["summary"]["unavailable"] == 1
    assert payload["summary"]["needs_fix"] == 0
    items = {item["skill_ref"]: item for item in payload["items"]}
    assert items["ready-skill:1.0.0"]["status"] == "available"
    assert items["ready-skill:1.0.0"]["mountable"] is True
    assert items["broken-skill:unknown"]["status"] == "unavailable"
    assert items["broken-skill:unknown"]["mountable"] is False
    assert len(items["broken-skill:unknown"]["issues"]) > 0
    assert items["broken-skill:unknown"]["status_message"]
    assert "check" in items["broken-skill:unknown"]["next_action"].lower()
    assert store.get_preflight_record("ready-skill:1.0.0") is not None


def test_excalidraw_preflight_exposes_capability_level_and_blockers(client):
    test_client, store, _agent_store = client
    store.replace_preflight_records(
        [
            _record(
                skill_name="excalidraw-diagram-generator",
                status="needs_fix",
                layer="workspace",
                issues=[
                    "Excalidraw icon libraries/ directory is missing.",
                    "Missing required binary: python",
                ],
            )
        ]
    )

    response = test_client.get("/api/skill-preflight/excalidraw-diagram-generator:1.0.0")
    assert response.status_code == 200
    payload = response.json()["item"]
    health = payload["excalidraw_health"]
    assert health["effective_level"] == "L0"
    assert health["levels"] == ["L1", "L2", "L3"]
    assert health["checks"]["icon_library_available"] is False
    assert health["checks"]["script_dependencies_ready"] is False
    assert health["checks"]["action_invocable"] is True
    assert health["blockers"]
    first_blocker = health["blockers"][0]
    assert first_blocker["code"] == "icon_library_missing"
    assert first_blocker["fix_command"].startswith("python ")
    assert "split-excalidraw-library.py" in first_blocker["fix_command"]
    assert first_blocker["fix_path"].endswith("/libraries")
