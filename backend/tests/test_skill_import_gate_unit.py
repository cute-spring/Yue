import os

from app.services.skills.import_models import (
    SkillActivationStatus,
    SkillImportLifecycleState,
)
from app.services.skills.import_service import SkillImportService
from app.services.skills.import_store import SkillImportStore


def _write_skill_package(root: str, *, requires_block: str = "") -> str:
    package_dir = os.path.join(root, "example-skill")
    os.makedirs(package_dir, exist_ok=True)
    with open(os.path.join(package_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            f"""---
name: example-skill
version: 1.0.0
description: Example skill
capabilities: ["analysis"]
entrypoint: system_prompt
{requires_block}---
## System Prompt
You are an example skill.
"""
        )
    return package_dir


def test_import_service_imports_valid_package_and_persists_record(tmp_path):
    package_dir = _write_skill_package(str(tmp_path))
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)

    result = service.import_from_directory(package_dir)

    assert result.record.skill_name == "example-skill"
    assert result.record.lifecycle_state == SkillImportLifecycleState.ACTIVATION_READY
    assert result.record.activation_status == SkillActivationStatus.INACTIVE
    assert result.report.standard_validation_status == "passed"
    assert result.report.compatibility_status == "compatible"

    persisted = store.get_record(result.record.id)
    assert persisted is not None
    assert persisted.skill_name == "example-skill"
    assert persisted.lifecycle_state == SkillImportLifecycleState.ACTIVATION_READY


def test_import_service_auto_activates_valid_package_when_enabled(tmp_path):
    package_dir = _write_skill_package(str(tmp_path))
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)

    result = service.import_from_directory(package_dir, auto_activate=True)

    assert result.record.lifecycle_state == SkillImportLifecycleState.ACTIVE
    assert result.record.activation_status == SkillActivationStatus.ACTIVE
    persisted = store.get_record(result.record.id)
    assert persisted is not None
    assert persisted.lifecycle_state == SkillImportLifecycleState.ACTIVE
    assert persisted.activation_status == SkillActivationStatus.ACTIVE


def test_import_service_auto_activate_does_not_replace_existing_active_import(tmp_path):
    package_dir = _write_skill_package(str(tmp_path))
    replacement_dir = os.path.join(str(tmp_path), "example-skill-v2")
    os.makedirs(replacement_dir, exist_ok=True)
    with open(os.path.join(replacement_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(
            """---
name: example-skill
version: 1.1.0
description: Example skill v2
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are an example skill v2.
"""
        )

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)

    first = service.import_from_directory(package_dir, auto_activate=True)
    second = service.import_from_directory(replacement_dir, auto_activate=True)

    assert first.record.lifecycle_state == SkillImportLifecycleState.ACTIVE
    assert first.record.activation_status == SkillActivationStatus.ACTIVE
    assert second.record.lifecycle_state == SkillImportLifecycleState.ACTIVATION_READY
    assert second.record.activation_status == SkillActivationStatus.INACTIVE

    active_entries = [
        entry for entry in store.list_entries()
        if entry.record.skill_name == "example-skill"
        and entry.record.activation_status == SkillActivationStatus.ACTIVE
    ]
    assert len(active_entries) == 1
    assert active_entries[0].record.id == first.record.id


def test_import_service_rejects_yue_incompatible_package_and_persists_report(tmp_path):
    package_dir = _write_skill_package(
        str(tmp_path),
        requires_block="requires:\n  bins: [missing_binary_for_stage1_test]\n",
    )
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillImportService(import_store=store)

    result = service.import_from_directory(package_dir)

    assert result.record.lifecycle_state == SkillImportLifecycleState.REJECTED
    assert result.report.standard_validation_status == "passed"
    assert result.report.compatibility_status == "incompatible"
    assert result.report.activation_eligibility == "ineligible"
    assert any("missing_binary_for_stage1_test" in issue for issue in result.report.compatibility_issues)

    persisted = store.get_record(result.record.id)
    assert persisted is not None
    assert persisted.lifecycle_state == SkillImportLifecycleState.REJECTED
