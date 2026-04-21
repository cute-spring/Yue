import os
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

    activate_response = client.post(f"/api/skill-imports/{import_id}/activate", json={})
    assert activate_response.status_code == 200
    activate_payload = activate_response.json()
    assert activate_payload["import_id"] == import_id
    assert activate_payload["lifecycle_state"] == SkillImportLifecycleState.ACTIVE.value
    assert activate_payload["activation_status"] == SkillActivationStatus.ACTIVE.value

    deactivate_response = client.post(f"/api/skill-imports/{import_id}/deactivate", json={})
    assert deactivate_response.status_code == 200
    deactivate_payload = deactivate_response.json()
    assert deactivate_payload["import_id"] == import_id
    assert deactivate_payload["lifecycle_state"] == SkillImportLifecycleState.INACTIVE.value
    assert deactivate_payload["activation_status"] == SkillActivationStatus.INACTIVE.value


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

    activate_response = client.post(f"/api/skill-imports/{old_import_id}/activate", json={})
    assert activate_response.status_code == 200

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


def test_replace_requires_existing_active_import_for_target_skill(client, tmp_path):
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


def test_replace_returns_invalid_request_on_target_skill_mismatch(client, tmp_path):
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
    activate_response = client.post(f"/api/skill-imports/{old_import_id}/activate", json={})
    assert activate_response.status_code == 200

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
    assert active_ids == {alpha_v1}

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


def test_post_import_upload_returns_unpack_failed_for_placeholder_flow(client):
    response = client.post(
        "/api/skill-imports",
        json={"source_type": "upload", "upload_token": "upload_123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "import_unpack_failed"


def test_activate_returns_already_active_when_import_is_active(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="already-active-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]
    client.post(f"/api/skill-imports/{import_id}/activate", json={})

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
    client.post(f"/api/skill-imports/{v1_id}/activate", json={})

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


def test_replace_rejects_when_target_import_is_already_active(client, tmp_path):
    package_dir = _write_skill_package(str(tmp_path), skill_name="already-active-replace-skill")
    create_response = client.post(
        "/api/skill-imports",
        json={"source_type": "directory", "source_path": package_dir},
    )
    import_id = create_response.json()["import"]["id"]
    client.post(f"/api/skill-imports/{import_id}/activate", json={})

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
    client.post(f"/api/skill-imports/{active_id}/activate", json={})

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
