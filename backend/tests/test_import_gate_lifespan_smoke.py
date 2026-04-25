import os
from types import SimpleNamespace

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
    runtime_context = SimpleNamespace(
        skill_registry=registry,
        skill_router=skill_service_module.skill_router,
        skill_action_execution_service=skill_service_module.skill_action_execution_service,
        skill_import_store=store,
        skill_import_service=service,
    )
    monkeypatch.setattr(skill_imports_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
    monkeypatch.setattr(skills_module, "get_stage4_lite_runtime_context", lambda: runtime_context)

    monkeypatch.setattr(main_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
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
            assert import_payload["lifecycle_state"] == "active"

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


def test_import_gate_runtime_state_restored_after_restart(tmp_path, monkeypatch):
    from app import main as main_module
    from app.api import skill_imports as skill_imports_module
    from app.api import skills as skills_module
    from app.services import skill_service as skill_service_module

    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", "import-gate")
    monkeypatch.setenv("YUE_SKILLS_WATCH_ENABLED", "false")

    data_dir = str(tmp_path / "data")
    store = SkillImportStore(data_dir=data_dir)
    service = SkillImportService(import_store=store)
    registry = SkillRegistry()

    monkeypatch.setattr(main_module.mcp_manager, "initialize", _noop_async)
    monkeypatch.setattr(main_module.mcp_manager, "cleanup", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "start", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "stop", _noop_async)

    monkeypatch.setattr(skill_service_module, "skill_import_store", store)
    monkeypatch.setattr(skill_service_module, "skill_import_service", service)
    monkeypatch.setattr(skill_service_module, "skill_registry", registry)
    runtime_context = SimpleNamespace(
        skill_registry=registry,
        skill_router=skill_service_module.skill_router,
        skill_action_execution_service=skill_service_module.skill_action_execution_service,
        skill_import_store=store,
        skill_import_service=service,
    )
    monkeypatch.setattr(skill_imports_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
    monkeypatch.setattr(skills_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
    monkeypatch.setattr(main_module, "get_stage4_lite_runtime_context", lambda: runtime_context)

    package_dir = _write_skill_package(str(tmp_path), skill_name="lifespan-restart-skill")

    try:
        with TestClient(main_module.app) as client:
            create_response = client.post(
                "/api/skill-imports",
                json={"source_type": "directory", "source_path": package_dir},
            )
            assert create_response.status_code == 201
            assert create_response.json()["import"]["lifecycle_state"] == "active"
            active_skills = client.get("/api/skills")
            assert active_skills.status_code == 200
            assert any(item["name"] == "lifespan-restart-skill" for item in active_skills.json())

        restarted_registry = SkillRegistry()
        monkeypatch.setattr(skill_service_module, "skill_registry", restarted_registry)
        restarted_runtime_context = SimpleNamespace(
            skill_registry=restarted_registry,
            skill_router=skill_service_module.skill_router,
            skill_action_execution_service=skill_service_module.skill_action_execution_service,
            skill_import_store=store,
            skill_import_service=service,
        )
        monkeypatch.setattr(skills_module, "get_stage4_lite_runtime_context", lambda: restarted_runtime_context)
        monkeypatch.setattr(main_module, "get_stage4_lite_runtime_context", lambda: restarted_runtime_context)

        with TestClient(main_module.app) as restarted_client:
            restored = restarted_client.get("/api/skills")
            assert restored.status_code == 200
            assert any(item["name"] == "lifespan-restart-skill" for item in restored.json())
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


@pytest.mark.parametrize(
    "runtime_mode, expected_reload_status",
    [
        ("legacy", 200),
        ("import-gate", 409),
    ],
)
def test_hybrid_runtime_matrix_reload_import_activate_deactivate(
    tmp_path,
    monkeypatch,
    runtime_mode,
    expected_reload_status,
):
    from app import main as main_module
    from app.api import skill_imports as skill_imports_module
    from app.api import skills as skills_module
    from app.services import skill_service as skill_service_module

    monkeypatch.setenv("YUE_SKILL_RUNTIME_MODE", runtime_mode)
    monkeypatch.setenv("YUE_SKILLS_WATCH_ENABLED", "false")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)
    registry = SkillRegistry()
    refresh_calls: list[str] = []

    monkeypatch.setattr(skill_service_module, "skill_import_store", store)
    monkeypatch.setattr(skill_service_module, "skill_import_service", service)
    monkeypatch.setattr(skill_service_module, "skill_registry", registry)
    runtime_context = SimpleNamespace(
        skill_registry=registry,
        skill_router=skill_service_module.skill_router,
        skill_action_execution_service=skill_service_module.skill_action_execution_service,
        skill_import_store=store,
        skill_import_service=service,
    )
    monkeypatch.setattr(skill_imports_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
    monkeypatch.setattr(skill_imports_module, "refresh_skill_runtime_catalog", lambda: refresh_calls.append("refresh"))
    monkeypatch.setattr(skills_module, "get_stage4_lite_runtime_context", lambda: runtime_context)

    monkeypatch.setattr(main_module, "get_stage4_lite_runtime_context", lambda: runtime_context)
    monkeypatch.setattr(main_module.mcp_manager, "initialize", _noop_async)
    monkeypatch.setattr(main_module.mcp_manager, "cleanup", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "start", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "stop", _noop_async)

    package_dir = _write_skill_package(str(tmp_path), skill_name=f"hybrid-lifespan-{runtime_mode}")

    try:
        with TestClient(main_module.app) as client:
            reload_response = client.post("/api/skills/reload")
            assert reload_response.status_code == expected_reload_status

            create_response = client.post(
                "/api/skill-imports",
                json={"source_type": "directory", "source_path": package_dir},
            )
            assert create_response.status_code == 201
            import_id = create_response.json()["import"]["id"]

            deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
            assert deactivate_response.status_code == 200

            activate_response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
            assert activate_response.status_code == 200
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")

    assert refresh_calls == ["refresh", "refresh", "refresh"]


def test_main_module_resolves_runtime_dependencies_via_context_seam():
    from app import main as main_module

    assert not hasattr(main_module, "skill_import_store")
    assert not hasattr(main_module, "skill_registry")
