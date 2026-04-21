import os

import pytest
from fastapi.testclient import TestClient

from app.services.skill_service import SkillImportService, SkillImportStore, SkillRegistry


def _write_skill_package(root: str, *, skill_name: str = "lifespan-smoke-skill", skill_version: str = "1.0.0") -> str:
    package_dir = os.path.join(root, skill_name)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: {skill_name}
version: {skill_version}
description: Lifespan smoke skill
capabilities: [\"analysis\"]
entrypoint: system_prompt
---
## System Prompt
You are a lifespan smoke skill.
"""
        )
    return package_dir


def _noop_async(*_args, **_kwargs):
    async def _inner():
        return None

    return _inner()


def test_import_gate_runtime_refresh_visible_without_restart(tmp_path, monkeypatch):
    from app import main as main_module
    from app.api import skill_imports as skill_imports_module
    from app.api import skills as skills_module
    from app.services import skill_service as skill_service_module

    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import-gate")
    monkeypatch.setenv("YUE_SKILLS_WATCH_ENABLED", "false")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)
    registry = SkillRegistry()

    monkeypatch.setattr(skill_service_module, "skill_import_store", store)
    monkeypatch.setattr(skill_service_module, "skill_import_service", service)
    monkeypatch.setattr(skill_service_module, "skill_registry", registry)

    monkeypatch.setattr(skill_imports_module, "skill_import_store", store)
    monkeypatch.setattr(skill_imports_module, "skill_import_service", service)
    monkeypatch.setattr(skills_module, "skill_registry", registry)

    monkeypatch.setattr(main_module, "skill_import_store", store)
    monkeypatch.setattr(main_module, "skill_registry", registry)
    monkeypatch.setattr(main_module.mcp_manager, "initialize", _noop_async)
    monkeypatch.setattr(main_module.mcp_manager, "cleanup", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "start", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "stop", _noop_async)

    package_dir = _write_skill_package(str(tmp_path), skill_name="lifespan-route-skill")

    try:
        with TestClient(main_module.app) as client:
            before = client.get("/api/skills")
            assert before.status_code == 200
            assert all(item["name"] != "lifespan-route-skill" for item in before.json())

            create_response = client.post(
                "/api/skill-imports",
                json={"source_type": "directory", "source_path": package_dir},
            )
            assert create_response.status_code == 201
            import_id = create_response.json()["import"]["id"]

            activate_response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
            assert activate_response.status_code == 200

            active_skills = client.get("/api/skills")
            assert active_skills.status_code == 200
            assert any(item["name"] == "lifespan-route-skill" for item in active_skills.json())

            deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
            assert deactivate_response.status_code == 200

            after = client.get("/api/skills")
            assert after.status_code == 200
            assert all(item["name"] != "lifespan-route-skill" for item in after.json())
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")
