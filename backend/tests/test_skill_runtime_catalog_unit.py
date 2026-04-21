from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from app.main import _resolve_runtime_skill_directories
from app.services.skills.import_models import (
    SkillActivationStatus,
    SkillImportLifecycleState,
    SkillImportPreview,
    SkillImportRecord,
    SkillImportReport,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec
from app.services.skills.registry import SkillRegistry
from app.services.skills.runtime_catalog import (
    RUNTIME_MODE_IMPORT_GATE,
    RUNTIME_MODE_LEGACY,
    RuntimeSkillCatalogProjector,
    resolve_skill_runtime_mode,
)


def _entry(
    *,
    skill_name: str,
    source_type: SkillImportSourceType,
    source_ref: str,
    lifecycle_state: SkillImportLifecycleState,
    activation_status: SkillActivationStatus,
    updated_at: datetime,
    version: str = "1.0.0",
) -> SkillImportStoredEntry:
    record = SkillImportRecord(
        skill_name=skill_name,
        skill_version=version,
        display_name=skill_name,
        source_type=source_type,
        source_ref=source_ref,
        package_format="package_directory",
        lifecycle_state=lifecycle_state,
        activation_status=activation_status,
        updated_at=updated_at,
    )
    return SkillImportStoredEntry(
        record=record,
        report=SkillImportReport(
            import_id=record.id,
            parse_status="passed",
            standard_validation_status="passed",
            compatibility_status="compatible",
            activation_eligibility="eligible",
        ),
        preview=SkillImportPreview(
            skill_name=skill_name,
            skill_version=version,
            description="test",
            capabilities=[],
            entrypoint="system_prompt",
        ),
    )


def _write_skill_package(root: Path, skill_name: str) -> Path:
    package_dir = root / skill_name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        """---
name: {name}
version: 1.0.0
description: test
capabilities: [\"analysis\"]
entrypoint: system_prompt
---
## System Prompt
You are a test skill.
""".format(name=skill_name),
        encoding="utf-8",
    )
    return package_dir


def test_runtime_catalog_projector_only_consumes_active_directory_imports(tmp_path):
    now = datetime.utcnow()
    active_dir = _write_skill_package(tmp_path, "active-skill")
    newer_dir = _write_skill_package(tmp_path, "versioned-skill-v2")
    older_dir = _write_skill_package(tmp_path, "versioned-skill-v1")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="active-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="inactive-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.INACTIVE,
            activation_status=SkillActivationStatus.INACTIVE,
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="upload-skill",
            source_type=SkillImportSourceType.UPLOAD,
            source_ref="upload-token-1",
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="versioned-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(older_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=now - timedelta(minutes=2),
            version="1.0.0",
        )
    )
    store.save_entry(
        _entry(
            skill_name="versioned-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(newer_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=now,
            version="2.0.0",
        )
    )

    projector = RuntimeSkillCatalogProjector(import_store=store)
    projected = projector.project_active_import_dirs()

    assert [item.layer for item in projected] == ["import", "import"]
    assert [item.path for item in projected] == sorted([str(active_dir.resolve()), str(newer_dir.resolve())])


def test_runtime_catalog_projector_recovers_active_projection_after_restart(tmp_path):
    active_dir = _write_skill_package(tmp_path, "restart-skill")
    now = datetime.utcnow()
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="restart-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=now,
        )
    )

    restarted_store = SkillImportStore(data_dir=str(tmp_path / "data"))
    projector = RuntimeSkillCatalogProjector(import_store=restarted_store)

    projected = projector.project_active_import_dirs()
    assert projected == [SkillDirectorySpec(layer="import", path=str(active_dir.resolve()))]


def test_resolve_runtime_mode_and_directory_path_switch(tmp_path):
    legacy_dirs = [SkillDirectorySpec(layer="builtin", path="/tmp/legacy-skill-dir")]
    active_dir = _write_skill_package(tmp_path, "switch-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="switch-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=datetime.utcnow(),
        )
    )

    class FakeResolver:
        def resolve(self):
            return legacy_dirs

    assert resolve_skill_runtime_mode(None) == RUNTIME_MODE_LEGACY
    assert resolve_skill_runtime_mode("import-gate") == RUNTIME_MODE_IMPORT_GATE

    resolved_legacy = _resolve_runtime_skill_directories(
        resolver=FakeResolver(),
        import_store=store,
        runtime_mode=RUNTIME_MODE_LEGACY,
    )
    resolved_gate = _resolve_runtime_skill_directories(
        resolver=FakeResolver(),
        import_store=store,
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
    )

    assert resolved_legacy == legacy_dirs
    assert resolved_gate == [SkillDirectorySpec(layer="import", path=str(active_dir.resolve()))]


def test_import_gate_projection_is_loadable_by_runtime_registry(tmp_path):
    active_dir = _write_skill_package(tmp_path, "routable-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="routable-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            activation_status=SkillActivationStatus.ACTIVE,
            updated_at=datetime.utcnow(),
        )
    )

    projected_dirs = RuntimeSkillCatalogProjector(import_store=store).project_active_import_dirs()
    registry = SkillRegistry()
    registry.set_layered_skill_dirs(projected_dirs)
    registry.skill_dirs = [item.path for item in projected_dirs]
    registry.load_all()

    selected = registry.get_skill("routable-skill", "1.0.0")
    assert selected is not None
    assert selected.name == "routable-skill"
