from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from app.main import _resolve_runtime_skill_directories
from app.services.skills.import_models import (
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
    RUNTIME_CONVERGENCE_STRATEGY_HYBRID,
    RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT,
    RUNTIME_MODE_IMPORT_GATE,
    RUNTIME_MODE_LEGACY,
    is_skill_import_mutation_allowed,
    RuntimeSkillCatalogProjector,
    refresh_runtime_registry_for_import_gate,
    resolve_skill_runtime_convergence_strategy,
    resolve_skill_runtime_mode,
)


def _entry(
    *,
    skill_name: str,
    source_type: SkillImportSourceType,
    source_ref: str,
    lifecycle_state: SkillImportLifecycleState,
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
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="inactive-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.INACTIVE,
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="versioned-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(older_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
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
            updated_at=now,
        )
    )

    restarted_store = SkillImportStore(data_dir=str(tmp_path / "data"))
    projector = RuntimeSkillCatalogProjector(import_store=restarted_store)

    projected = projector.project_active_import_dirs()
    assert projected == [SkillDirectorySpec(layer="import", path=str(active_dir.resolve()))]

def test_runtime_catalog_projector_prefers_higher_version_when_updated_at_matches(tmp_path):
    now = datetime.utcnow()
    older_dir = _write_skill_package(tmp_path, "same-time-skill-v1")
    newer_dir = _write_skill_package(tmp_path, "same-time-skill-v2")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="same-time-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(older_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=now,
            version="1.0.0",
        )
    )
    store.save_entry(
        _entry(
            skill_name="same-time-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(newer_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=now,
            version="2.0.0",
        )
    )

    projected = RuntimeSkillCatalogProjector(import_store=store).project_active_import_dirs()
    assert projected == [SkillDirectorySpec(layer="import", path=str(newer_dir.resolve()))]


def test_runtime_catalog_projector_skips_invalid_source_refs(tmp_path):
    now = datetime.utcnow()
    valid_dir = _write_skill_package(tmp_path, "valid-skill")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="broken-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref="bad\0path",
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=now,
        )
    )
    store.save_entry(
        _entry(
            skill_name="valid-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(valid_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=now,
        )
    )

    projected = RuntimeSkillCatalogProjector(import_store=store).project_active_import_dirs()
    assert projected == [SkillDirectorySpec(layer="import", path=str(valid_dir.resolve()))]


def test_resolve_runtime_mode_defaults_to_import_gate_and_supports_explicit_legacy(tmp_path):
    legacy_dirs = [SkillDirectorySpec(layer="builtin", path="/tmp/legacy-skill-dir")]
    active_dir = _write_skill_package(tmp_path, "switch-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="switch-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=datetime.utcnow(),
        )
    )

    class FakeResolver:
        def resolve(self):
            return legacy_dirs

    assert resolve_skill_runtime_mode(None) == RUNTIME_MODE_IMPORT_GATE
    assert resolve_skill_runtime_mode("import-gate") == RUNTIME_MODE_IMPORT_GATE
    assert resolve_skill_runtime_mode("  IMPORT_GATE  ") == RUNTIME_MODE_IMPORT_GATE
    assert resolve_skill_runtime_mode("legacy") == RUNTIME_MODE_LEGACY
    assert resolve_skill_runtime_mode("unexpected-value") == RUNTIME_MODE_IMPORT_GATE

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


def test_mutation_guard_strict_strategy_blocks_only_explicit_legacy_runtime():
    assert is_skill_import_mutation_allowed(
        runtime_mode=None,
        convergence_strategy=RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT,
    )
    assert not is_skill_import_mutation_allowed(
        runtime_mode=RUNTIME_MODE_LEGACY,
        convergence_strategy=RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT,
    )


def test_resolve_runtime_convergence_strategy_supports_strict_and_default_aliases():
    assert resolve_skill_runtime_convergence_strategy(None) == RUNTIME_CONVERGENCE_STRATEGY_HYBRID
    assert resolve_skill_runtime_convergence_strategy("default") == RUNTIME_CONVERGENCE_STRATEGY_HYBRID
    assert resolve_skill_runtime_convergence_strategy("  STRICT  ") == RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT


def test_refresh_runtime_registry_for_import_gate_is_repeatable(tmp_path):
    active_dir = _write_skill_package(tmp_path, "repeatable-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="repeatable-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
            updated_at=datetime.utcnow(),
        )
    )

    calls = []

    class FakeRegistry:
        def __init__(self):
            self.skill_dirs = []
            self.layered_skill_dirs = []

        def set_layered_skill_dirs(self, layered_skill_dirs):
            self.layered_skill_dirs = list(layered_skill_dirs)
            calls.append([item.path for item in layered_skill_dirs])

        def load_all(self):
            self.skill_dirs = [item.path for item in self.layered_skill_dirs]
            calls.append(list(self.skill_dirs))

    registry = FakeRegistry()

    from app.services.skills.runtime_catalog import refresh_runtime_registry_for_import_gate

    assert refresh_runtime_registry_for_import_gate(
        skill_registry=registry,
        import_store=store,
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
    )
    assert refresh_runtime_registry_for_import_gate(
        skill_registry=registry,
        import_store=store,
        runtime_mode=RUNTIME_MODE_IMPORT_GATE,
    )

    assert registry.layered_skill_dirs == [SkillDirectorySpec(layer="import", path=str(active_dir.resolve()))]
    assert registry.skill_dirs == [str(active_dir.resolve())]
    assert calls == [
        [str(active_dir.resolve())],
        [str(active_dir.resolve())],
        [str(active_dir.resolve())],
        [str(active_dir.resolve())],
    ]


def test_refresh_runtime_registry_for_import_gate_noop_in_legacy_mode():
    calls = {"set_layered": 0, "load_all": 0}

    class FakeRegistry:
        skill_dirs = []

        def set_layered_skill_dirs(self, _layered_skill_dirs):
            calls["set_layered"] += 1

        def load_all(self):
            calls["load_all"] += 1

    result = refresh_runtime_registry_for_import_gate(
        skill_registry=FakeRegistry(),
        runtime_mode=RUNTIME_MODE_LEGACY,
    )

    assert result is False
    assert calls == {"set_layered": 0, "load_all": 0}


def test_import_gate_projection_is_loadable_by_runtime_registry(tmp_path):
    active_dir = _write_skill_package(tmp_path, "routable-skill")
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    store.save_entry(
        _entry(
            skill_name="routable-skill",
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(active_dir),
            lifecycle_state=SkillImportLifecycleState.ACTIVE,
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
