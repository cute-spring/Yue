import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.skills.import_models import (
    SkillActivationStatus,
    SkillImportLifecycleState,
)
from app.services.skills.import_service import SkillImportService
from app.services.skills.import_store import SkillImportStore


def _write_skill_package(
    root: str,
    *,
    skill_name: str = "example-skill",
    skill_version: str = "1.0.0",
    dir_name: str | None = None,
) -> str:
    package_dir = os.path.join(root, dir_name or skill_name)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: {skill_name}
version: {skill_version}
description: Example skill
capabilities: [\"analysis\"]
entrypoint: system_prompt
---
## System Prompt
You are an example skill.
"""
        )
    return package_dir


def _write_incompatible_skill_package(
    root: str,
    *,
    skill_name: str = "bad-skill",
    skill_version: str = "1.0.0",
    dir_name: str | None = None,
) -> str:
    package_dir = os.path.join(root, dir_name or skill_name)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: {skill_name}
version: {skill_version}
description: Incompatible skill
capabilities: ["analysis"]
entrypoint: system_prompt
requires:
  bins: [missing_binary_for_stage2_api_test]
---
## System Prompt
You are an incompatible skill.
"""
        )
    return package_dir


def _write_unparseable_skill_directory(root: str, *, dir_name: str = "broken-skill-dir") -> str:
    package_dir = os.path.join(root, dir_name)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "README.md"), "w", encoding="utf-8") as handle:
        handle.write("no SKILL.md here")
    return package_dir


def _write_uploaded_skill_package(
    root: str,
    *,
    upload_token: str = "upload_123",
    skill_name: str = "uploaded-skill",
    skill_version: str = "1.0.0",
) -> str:
    package_dir = os.path.join(root, "data", "uploads", upload_token)
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: {skill_name}
version: {skill_version}
description: Uploaded skill
capabilities: [\"analysis\"]
entrypoint: system_prompt
---
## System Prompt
You are an uploaded skill.
"""
        )
    return package_dir


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)

    monkeypatch.setattr(skill_imports_module, "skill_import_store", store)
    monkeypatch.setattr(skill_imports_module, "skill_import_service", service)

    app = FastAPI()
    app.include_router(skill_imports_module.router, prefix="/api/skill-imports")
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def test_post_import_and_get_and_list(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="imported-skill")

    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["import"]["skill_name"] == "imported-skill"
    assert payload["report"]["activation_eligibility"] == "eligible"
    assert payload["preview"]["skill_name"] == "imported-skill"
    assert payload["import"]["lifecycle_state"] == SkillImportLifecycleState.ACTIVE.value
    assert payload["import"]["activation_status"] == SkillActivationStatus.ACTIVE.value

    import_id = payload["import"]["id"]

    get_response = client.get(f"/api/skill-imports/{import_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["import"]["id"] == import_id
    assert get_payload["report"]["import_id"] == import_id

    list_response = client.get("/api/skill-imports")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert isinstance(list_payload["items"], list)
    assert len(list_payload["items"]) == 1
    assert list_payload["items"][0]["id"] == import_id


def test_activate_and_deactivate_import(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="activate-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
    assert deactivate_response.status_code == 200
    deactivate_payload = deactivate_response.json()
    assert deactivate_payload["import_id"] == import_id
    assert deactivate_payload["lifecycle_state"] == SkillImportLifecycleState.INACTIVE.value
    assert deactivate_payload["activation_status"] == SkillActivationStatus.INACTIVE.value

    activate_response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
    assert activate_response.status_code == 200
    activate_payload = activate_response.json()
    assert activate_payload["import_id"] == import_id
    assert activate_payload["lifecycle_state"] == SkillImportLifecycleState.ACTIVE.value
    assert activate_payload["activation_status"] == SkillActivationStatus.ACTIVE.value


def test_post_import_auto_activation_triggers_runtime_refresh_hook(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    calls: list[str] = []
    monkeypatch.setattr(skill_imports_module, "refresh_skill_runtime_catalog", lambda: calls.append("refresh"))

    package_dir = _write_skill_package(str(tmp_path), skill_name="refresh-activate-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    assert create_response.status_code == 201
    assert calls == ["refresh"]


def test_deactivate_triggers_runtime_refresh_hook(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    calls: list[str] = []
    monkeypatch.setattr(skill_imports_module, "refresh_skill_runtime_catalog", lambda: calls.append("refresh"))

    package_dir = _write_skill_package(str(tmp_path), skill_name="refresh-deactivate-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]
    calls.clear()

    response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
    assert response.status_code == 200
    assert calls == ["refresh"]


def test_post_import_respects_auto_activation_flag_off(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_auto_activate_enabled": False},
    )
    package_dir = _write_skill_package(str(tmp_path), skill_name="manual-activate-skill")

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["import"]["lifecycle_state"] == SkillImportLifecycleState.ACTIVATION_READY.value
    assert payload["import"]["activation_status"] == SkillActivationStatus.INACTIVE.value


def test_post_import_auto_activate_does_not_replace_existing_active_import(client, tmp_path):
    active_dir = _write_skill_package(
        str(tmp_path),
        skill_name="auto-activate-conflict-skill",
        skill_version="1.0.0",
        dir_name="auto-activate-conflict-v1",
    )
    active_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": active_dir},
    )
    assert active_response.status_code == 201
    active_import = active_response.json()["import"]
    assert active_import["activation_status"] == SkillActivationStatus.ACTIVE.value

    pending_dir = _write_skill_package(
        str(tmp_path),
        skill_name="auto-activate-conflict-skill",
        skill_version="1.1.0",
        dir_name="auto-activate-conflict-v2",
    )
    pending_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": pending_dir},
    )
    assert pending_response.status_code == 201
    pending_import = pending_response.json()["import"]
    assert pending_import["lifecycle_state"] == SkillImportLifecycleState.ACTIVATION_READY.value
    assert pending_import["activation_status"] == SkillActivationStatus.INACTIVE.value

    list_response = client.get("/api/skill-imports", params={"skill_name": "auto-activate-conflict-skill"})
    items = list_response.json()["items"]
    active_items = [item for item in items if item["activation_status"] == SkillActivationStatus.ACTIVE.value]
    assert len(active_items) == 1
    assert active_items[0]["id"] == active_import["id"]


def test_get_unknown_import_returns_stable_not_found_code(client):
    response = client.get("/api/skill-imports/imp_missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "skill_import_not_found"


def test_activate_unknown_import_returns_stable_not_found_code(client):
    response = client.post("/api/skill-imports/imp_missing/activate", json={})
    assert response.status_code == 404
    assert response.json()["detail"] == "skill_import_not_found"


def test_deactivate_inactive_import_returns_stable_conflict_code(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="inactive-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    first_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
    assert first_response.status_code == 200

    response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_import_not_active"


def test_replace_promotes_new_import_and_supersedes_previous_active(client, tmp_path):
    old_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-skill",
        skill_version="1.0.0",
        dir_name="replace-skill-v1",
    )
    old_create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": old_package_dir},
    )
    old_import_id = old_create_response.json()["import"]["id"]

    new_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-skill",
        skill_version="1.1.0",
        dir_name="replace-skill-v1_1",
    )
    new_create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": new_package_dir},
    )
    new_import_id = new_create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{new_import_id}/replace",
        json={"target_skill_name": "replace-skill"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["activated_import_id"] == new_import_id
    assert payload["superseded_import_id"] == old_import_id
    assert payload["skill_name"] == "replace-skill"
    assert payload["active_version"] == "1.1.0"

    old_get_response = client.get(f"/api/skill-imports/{old_import_id}")
    old_import = old_get_response.json()["import"]
    assert old_import["lifecycle_state"] == SkillImportLifecycleState.SUPERSEDED.value
    assert old_import["activation_status"] == SkillActivationStatus.SUPERSEDED.value
    assert old_import["superseded_by_import_id"] == new_import_id

    new_get_response = client.get(f"/api/skill-imports/{new_import_id}")
    new_import = new_get_response.json()["import"]
    assert new_import["lifecycle_state"] == SkillImportLifecycleState.ACTIVE.value
    assert new_import["activation_status"] == SkillActivationStatus.ACTIVE.value
    assert new_import["supersedes_import_id"] == old_import_id


def test_replace_triggers_runtime_refresh_hook(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    calls: list[str] = []
    monkeypatch.setattr(skill_imports_module, "refresh_skill_runtime_catalog", lambda: calls.append("refresh"))

    old_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="refresh-replace-skill",
        skill_version="1.0.0",
        dir_name="refresh-replace-skill-v1",
    )
    old_import_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": old_package_dir},
    ).json()["import"]["id"]
    calls.clear()

    new_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="refresh-replace-skill",
        skill_version="1.1.0",
        dir_name="refresh-replace-skill-v1_1",
    )
    new_import_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": new_package_dir},
    ).json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{new_import_id}/replace",
        json={"target_skill_name": "refresh-replace-skill"},
    )
    assert response.status_code == 200
    assert calls == ["refresh"]


def test_replace_unknown_import_returns_stable_not_found_code(client):
    response = client.post(
        "/api/skill-imports/imp_missing/replace",
        json={"target_skill_name": "replace-skill"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "skill_import_not_found"


def test_replace_requires_activation_ready_state(client, tmp_path):
    package_dir = _write_incompatible_skill_package(
        str(tmp_path),
        skill_name="replace-bad-skill",
        skill_version="2.0.0",
        dir_name="replace-bad-skill-v2",
    )
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{import_id}/replace",
        json={"target_skill_name": "replace-bad-skill"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "skill_activation_ineligible"


def test_replace_requires_existing_active_import_for_target_skill(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_auto_activate_enabled": False},
    )
    package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-no-active-skill",
        skill_version="1.1.0",
        dir_name="replace-no-active-skill-v1_1",
    )
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{import_id}/replace",
        json={"target_skill_name": "replace-no-active-skill"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_replacement_conflict"


def test_replace_returns_invalid_request_on_target_skill_mismatch(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_auto_activate_enabled": False},
    )
    package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-mismatch-skill",
        skill_version="1.1.0",
        dir_name="replace-mismatch-skill-v1_1",
    )
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{import_id}/replace",
        json={"target_skill_name": "other-skill"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_replace_rejects_missing_target_skill_name_as_invalid_request(client, tmp_path):
    package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-missing-target-skill",
        skill_version="1.1.0",
        dir_name="replace-missing-target-v1_1",
    )
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(f"/api/skill-imports/{import_id}/replace", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_replace_conflict_when_multiple_active_imports_exist(client, tmp_path):
    from app.api import skill_imports as skill_imports_module

    old_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-multi-active-skill",
        skill_version="1.0.0",
        dir_name="replace-multi-active-v1",
    )
    old_create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": old_package_dir},
    )
    old_import_id = old_create_response.json()["import"]["id"]
    parallel_active_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-multi-active-skill",
        skill_version="1.0.1",
        dir_name="replace-multi-active-v1_0_1",
    )
    parallel_create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": parallel_active_dir},
    )
    parallel_import_id = parallel_create_response.json()["import"]["id"]
    parallel_entry = skill_imports_module.skill_import_store.get_entry(parallel_import_id)
    parallel_entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
    parallel_entry.record.activation_status = SkillActivationStatus.ACTIVE
    skill_imports_module.skill_import_store.save_entry(parallel_entry)

    new_package_dir = _write_skill_package(
        str(tmp_path),
        skill_name="replace-multi-active-skill",
        skill_version="1.1.0",
        dir_name="replace-multi-active-v1_1",
    )
    new_create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": new_package_dir},
    )
    new_import_id = new_create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{new_import_id}/replace",
        json={"target_skill_name": "replace-multi-active-skill"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_replacement_conflict"


def test_list_skill_imports_filters_and_latest_only(client, tmp_path):
    alpha_v1_dir = _write_skill_package(
        str(tmp_path),
        skill_name="alpha-skill",
        skill_version="1.0.0",
        dir_name="alpha-v1",
    )
    alpha_v1 = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": alpha_v1_dir},
    ).json()["import"]["id"]
    client.post(f"/api/skill-imports/{alpha_v1}/activate", json={})

    alpha_v2_dir = _write_skill_package(
        str(tmp_path),
        skill_name="alpha-skill",
        skill_version="1.1.0",
        dir_name="alpha-v2",
    )
    alpha_v2 = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": alpha_v2_dir},
    ).json()["import"]["id"]

    beta_dir = _write_skill_package(
        str(tmp_path),
        skill_name="beta-skill",
        skill_version="1.0.0",
        dir_name="beta-v1",
    )
    beta_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": beta_dir},
    ).json()["import"]["id"]

    by_skill = client.get("/api/skill-imports", params={"skill_name": "alpha-skill"})
    assert by_skill.status_code == 200
    by_skill_ids = {item["id"] for item in by_skill.json()["items"]}
    assert by_skill_ids == {alpha_v1, alpha_v2}

    by_activation = client.get("/api/skill-imports", params={"activation_status": "active"})
    assert by_activation.status_code == 200
    active_ids = {item["id"] for item in by_activation.json()["items"]}
    assert active_ids == {alpha_v1, beta_id}

    latest_only = client.get("/api/skill-imports", params={"latest_only": "true"})
    assert latest_only.status_code == 200
    latest_items = latest_only.json()["items"]
    assert len(latest_items) == 2
    latest_ids = {item["id"] for item in latest_items}
    assert alpha_v2 in latest_ids
    assert beta_id in latest_ids


def test_list_skill_imports_rejects_invalid_lifecycle_state_query(client):
    response = client.get("/api/skill-imports", params={"lifecycle_state": "unexpected_state"})
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_list_skill_imports_rejects_invalid_activation_status_query(client):
    response = client.get("/api/skill-imports", params={"activation_status": "unexpected_status"})
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_post_import_returns_422_with_stable_code_for_incompatible_package(client, tmp_path):
    package_dir = _write_incompatible_skill_package(str(tmp_path), skill_name="incompatible-skill")

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"] == "skill_yue_compatibility_failed"
    assert payload["report"]["activation_eligibility"] == "ineligible"


def test_post_import_returns_parse_failed_code_for_unparseable_directory(client, tmp_path):
    package_dir = _write_unparseable_skill_directory(str(tmp_path))

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"] == "skill_parse_failed"
    assert payload["report"]["parse_status"] == "failed"


def test_post_import_directory_requires_source_path(client):
    response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "import_source_missing"


def test_post_import_directory_rejects_nonexistent_source_path(client):
    response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": "/tmp/not-found-skill-path"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "import_source_not_found"


def test_post_import_upload_requires_upload_token(client):
    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "import_source_missing"


def test_post_import_upload_returns_not_found_for_missing_upload_directory(client):
    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "upload_123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "import_unpack_failed"


def test_post_import_upload_resolves_upload_token_directory_package(client, tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "data"))
    from app.api import skill_imports as skill_imports_module
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_upload_enabled": True},
    )
    package_dir = _write_uploaded_skill_package(str(tmp_path), upload_token="upload_123", skill_name="upload-dir-skill")

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "upload_123"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["import"]["skill_name"] == "upload-dir-skill"
    assert payload["import"]["source_type"] == "upload"
    assert payload["import"]["source_ref"] == package_dir
    assert payload["report"]["activation_eligibility"] == "eligible"
    assert payload["preview"]["skill_name"] == "upload-dir-skill"


def test_post_import_upload_rejects_dot_segments_in_upload_token(client, tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "data"))
    from app.api import skill_imports as skill_imports_module
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_upload_enabled": True},
    )

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "../escape"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_post_import_upload_rejects_upload_root_token(client, tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data" / "uploads").mkdir(parents=True, exist_ok=True)
    from app.api import skill_imports as skill_imports_module
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_upload_enabled": True},
    )

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "."},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_post_import_upload_rejects_url_encoded_dot_segments(client, tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "data"))
    from app.api import skill_imports as skill_imports_module
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_upload_enabled": True},
    )

    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "%2e%2e/escape"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_activate_returns_already_active_when_import_is_active(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="already-active-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_import_already_active"


def test_activate_requires_activation_ready_state(client, tmp_path):
    package_dir = _write_incompatible_skill_package(str(tmp_path), skill_name="ineligible-activate-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
    assert response.status_code == 422
    assert response.json()["detail"] == "skill_activation_ineligible"


def test_activate_conflicts_when_same_skill_has_another_active_import(client, tmp_path):
    v1_dir = _write_skill_package(
        str(tmp_path),
        skill_name="activate-conflict-skill",
        skill_version="1.0.0",
        dir_name="activate-conflict-v1",
    )
    v1_create = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": v1_dir},
    )
    v1_id = v1_create.json()["import"]["id"]

    v2_dir = _write_skill_package(
        str(tmp_path),
        skill_name="activate-conflict-skill",
        skill_version="1.1.0",
        dir_name="activate-conflict-v2",
    )
    v2_create = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": v2_dir},
    )
    v2_id = v2_create.json()["import"]["id"]

    response = client.post(f"/api/skill-imports/{v2_id}/activate", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_replacement_conflict"


def test_concurrent_activate_same_skill_versions_keeps_single_active(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    original_save_entry = skill_imports_module._save_entry

    def delayed_save(entry):
        time.sleep(0.05)
        return original_save_entry(entry)

    monkeypatch.setattr(skill_imports_module, "_save_entry", delayed_save)
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_auto_activate_enabled": False},
    )

    v1_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-activate-skill",
        skill_version="1.0.0",
        dir_name="concurrent-activate-v1",
    )
    v2_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-activate-skill",
        skill_version="1.1.0",
        dir_name="concurrent-activate-v2",
    )

    v1_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": v1_dir},
    ).json()["import"]["id"]
    v2_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": v2_dir},
    ).json()["import"]["id"]

    def _activate(import_id: str):
        return client.post(f"/api/skill-imports/{import_id}/activate", json={})

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_activate, v1_id)
        second = pool.submit(_activate, v2_id)
        responses = [first.result(), second.result()]

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [200, 409]
    conflict_payload = next(response.json() for response in responses if response.status_code == 409)
    assert conflict_payload["detail"] == "skill_replacement_conflict"

    list_response = client.get("/api/skill-imports", params={"skill_name": "concurrent-activate-skill"})
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    active_items = [item for item in items if item["activation_status"] == SkillActivationStatus.ACTIVE.value]
    assert len(active_items) == 1


def test_concurrent_import_same_skill_versions_auto_activate_keeps_single_active(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    original_import = skill_imports_module.skill_import_service.import_from_directory

    def delayed_import(*args, **kwargs):
        time.sleep(0.05)
        return original_import(*args, **kwargs)

    monkeypatch.setattr(skill_imports_module.skill_import_service, "import_from_directory", delayed_import)

    v1_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-auto-import-skill",
        skill_version="1.0.0",
        dir_name="concurrent-auto-import-v1",
    )
    v2_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-auto-import-skill",
        skill_version="1.1.0",
        dir_name="concurrent-auto-import-v2",
    )

    def _import(path: str):
        return client.post("/api/skill-imports", json={"source_type": "directory", "source_path": path})

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_import, v1_dir)
        second = pool.submit(_import, v2_dir)
        responses = [first.result(), second.result()]

    assert sorted(response.status_code for response in responses) == [201, 201]
    imports = [response.json()["import"] for response in responses]
    active_imports = [item for item in imports if item["activation_status"] == SkillActivationStatus.ACTIVE.value]
    pending_imports = [item for item in imports if item["activation_status"] == SkillActivationStatus.INACTIVE.value]
    assert len(active_imports) == 1
    assert len(pending_imports) == 1
    assert pending_imports[0]["lifecycle_state"] == SkillImportLifecycleState.ACTIVATION_READY.value

    list_response = client.get("/api/skill-imports", params={"skill_name": "concurrent-auto-import-skill"})
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    active_items = [item for item in items if item["activation_status"] == SkillActivationStatus.ACTIVE.value]
    assert len(active_items) == 1


def test_concurrent_deactivate_and_replace_keep_single_mutation_result(client, tmp_path, monkeypatch):
    from app.api import skill_imports as skill_imports_module

    original_save_entry = skill_imports_module._save_entry

    def delayed_save(entry):
        time.sleep(0.05)
        return original_save_entry(entry)

    monkeypatch.setattr(skill_imports_module, "_save_entry", delayed_save)
    monkeypatch.setattr(
        skill_imports_module.config_service,
        "get_feature_flags",
        lambda: {"skill_import_auto_activate_enabled": False},
    )

    active_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-mutation-skill",
        skill_version="1.0.0",
        dir_name="concurrent-mutation-v1",
    )
    active_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": active_dir},
    ).json()["import"]["id"]
    activate_response = client.post(f"/api/skill-imports/{active_id}/activate", json={})
    assert activate_response.status_code == 200

    replacement_dir = _write_skill_package(
        str(tmp_path),
        skill_name="concurrent-mutation-skill",
        skill_version="1.1.0",
        dir_name="concurrent-mutation-v2",
    )
    replacement_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": replacement_dir},
    ).json()["import"]["id"]

    def _deactivate():
        return client.post(f"/api/skill-imports/{active_id}/deactivate", json={})

    def _replace():
        return client.post(
            f"/api/skill-imports/{replacement_id}/replace",
            json={"target_skill_name": "concurrent-mutation-skill"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_deactivate)
        second = pool.submit(_replace)
        responses = [first.result(), second.result()]

    assert sorted(response.status_code for response in responses) == [200, 409]
    list_response = client.get("/api/skill-imports", params={"skill_name": "concurrent-mutation-skill"})
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    active_items = [item for item in items if item["activation_status"] == SkillActivationStatus.ACTIVE.value]
    assert len(active_items) <= 1


def test_replace_rejects_when_target_import_is_already_active(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="already-active-replace-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]

    response = client.post(
        f"/api/skill-imports/{import_id}/replace",
        json={"target_skill_name": "already-active-replace-skill"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "skill_import_already_active"


def test_list_skill_imports_filters_by_lifecycle_state_hit(client, tmp_path):
    active_dir = _write_skill_package(
        str(tmp_path),
        skill_name="lifecycle-hit-skill",
        skill_version="1.0.0",
        dir_name="lifecycle-hit-active",
    )
    active_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": active_dir},
    ).json()["import"]["id"]

    inactive_dir = _write_skill_package(
        str(tmp_path),
        skill_name="lifecycle-hit-skill",
        skill_version="1.1.0",
        dir_name="lifecycle-hit-inactive",
    )
    inactive_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": inactive_dir},
    ).json()["import"]["id"]

    response = client.get("/api/skill-imports", params={"lifecycle_state": "active"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert active_id in ids
    assert inactive_id not in ids


def test_latest_only_does_not_replace_newer_item_with_older_record(client, tmp_path):
    from app.api import skill_imports as skill_imports_module

    newer_dir = _write_skill_package(
        str(tmp_path),
        skill_name="latest-reverse-skill",
        skill_version="2.0.0",
        dir_name="latest-reverse-newer",
    )
    newer_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": newer_dir},
    ).json()["import"]["id"]

    older_dir = _write_skill_package(
        str(tmp_path),
        skill_name="latest-reverse-skill",
        skill_version="1.0.0",
        dir_name="latest-reverse-older",
    )
    older_id = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": older_dir},
    ).json()["import"]["id"]

    newer_entry = skill_imports_module.skill_import_store.get_entry(newer_id)
    older_entry = skill_imports_module.skill_import_store.get_entry(older_id)
    newer_entry.record.updated_at = datetime(2026, 4, 21, 12, 0, 0)
    older_entry.record.updated_at = datetime(2026, 4, 21, 11, 0, 0)
    skill_imports_module.skill_import_store.save_entry(newer_entry)
    skill_imports_module.skill_import_store.save_entry(older_entry)

    response = client.get("/api/skill-imports", params={"latest_only": "true"})
    assert response.status_code == 200
    items = response.json()["items"]
    latest = next(item for item in items if item["skill_name"] == "latest-reverse-skill")
    assert latest["id"] == newer_id
