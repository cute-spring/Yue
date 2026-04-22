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


def _write_uploaded_skill_package(
    root: str,
    *,
    upload_token: str = "lifespan-upload-token",
    skill_name: str = "lifespan-upload-skill",
    skill_version: str = "1.0.0",
) -> str:
    package_dir = os.path.join(root, "data", "uploads", upload_token)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: {skill_name}
version: {skill_version}
description: Uploaded lifespan smoke skill
capabilities: [\"analysis\"]
entrypoint: system_prompt
---
## System Prompt
You are an uploaded lifespan smoke skill.
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
            import_payload = create_response.json()["import"]
            assert import_payload["activation_status"] == "active"

            active_skills = client.get("/api/skills")
            assert active_skills.status_code == 200
            assert any(item["name"] == "lifespan-route-skill" for item in active_skills.json())

            import_id = import_payload["id"]
            deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
            assert deactivate_response.status_code == 200

            after = client.get("/api/skills")
            assert after.status_code == 200
            assert all(item["name"] != "lifespan-route-skill" for item in after.json())
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def test_import_gate_runtime_refresh_visible_without_restart_for_uploaded_package(tmp_path, monkeypatch):
    from app import main as main_module
    from app.api import skill_imports as skill_imports_module
    from app.api import skills as skills_module
    from app.services import skill_service as skill_service_module

    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import-gate")
    monkeypatch.setenv("YUE_SKILLS_WATCH_ENABLED", "false")
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "data"))

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)
    registry = SkillRegistry()

    monkeypatch.setattr(skill_service_module, "skill_import_store", store)
    monkeypatch.setattr(skill_service_module, "skill_import_service", service)
    monkeypatch.setattr(skill_service_module, "skill_registry", registry)

    monkeypatch.setattr(skill_imports_module, "skill_import_store", store)
    monkeypatch.setattr(skill_imports_module, "skill_import_service", service)
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_upload_enabled": True},
    )
    monkeypatch.setattr(skills_module, "skill_registry", registry)

    monkeypatch.setattr(main_module, "skill_import_store", store)
    monkeypatch.setattr(main_module, "skill_registry", registry)
    monkeypatch.setattr(main_module.mcp_manager, "initialize", _noop_async)
    monkeypatch.setattr(main_module.mcp_manager, "cleanup", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "start", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "stop", _noop_async)

    _write_uploaded_skill_package(str(tmp_path), upload_token="lifespan-upload-token", skill_name="lifespan-upload-route-skill")

    try:
        with TestClient(main_module.app) as client:
            before = client.get("/api/skills")
            assert before.status_code == 200
            assert all(item["name"] != "lifespan-upload-route-skill" for item in before.json())

            create_response = client.post(
                "/api/skill-imports",
                json={"source_type": "upload", "upload_token": "lifespan-upload-token"},
            )
            assert create_response.status_code == 201
            import_payload = create_response.json()["import"]
            assert import_payload["activation_status"] == "active"

            active_skills = client.get("/api/skills")
            assert active_skills.status_code == 200
            assert any(item["name"] == "lifespan-upload-route-skill" for item in active_skills.json())

            import_id = import_payload["id"]
            deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
            assert deactivate_response.status_code == 200

            after = client.get("/api/skills")
            assert after.status_code == 200
            assert all(item["name"] != "lifespan-upload-route-skill" for item in after.json())
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")
