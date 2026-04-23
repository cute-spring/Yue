from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Dict

from app.services.skills.import_models import (
    SkillImportLifecycleState,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec

RUNTIME_MODE_LEGACY = "legacy"
RUNTIME_MODE_IMPORT_GATE = "import-gate"
RUNTIME_MODE_ENV_KEY = "YUE_SKILL_RUNTIME_MODE"
RUNTIME_CONVERGENCE_STRATEGY_ENV_KEY = "YUE_SKILL_RUNTIME_CONVERGENCE_STRATEGY"
RUNTIME_CONVERGENCE_STRATEGY_HYBRID = "hybrid"
RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT = "import-gate-strict"


def resolve_skill_runtime_mode(runtime_mode: Optional[str] = None) -> str:
    raw_value = runtime_mode if isinstance(runtime_mode, str) else os.getenv(RUNTIME_MODE_ENV_KEY, RUNTIME_MODE_IMPORT_GATE)
    if not isinstance(raw_value, str):
        raw_value = RUNTIME_MODE_IMPORT_GATE
    raw = raw_value.strip().lower()
    if raw in {"legacy"}:
        return RUNTIME_MODE_LEGACY
    if raw in {"import-gate", "import_gate"}:
        return RUNTIME_MODE_IMPORT_GATE
    # Prefer import-gate by default; only explicit legacy keeps legacy behavior.
    return RUNTIME_MODE_IMPORT_GATE


def resolve_skill_runtime_convergence_strategy(strategy: Optional[str] = None) -> str:
    raw_value = (
        strategy
        if isinstance(strategy, str)
        else os.getenv(RUNTIME_CONVERGENCE_STRATEGY_ENV_KEY, RUNTIME_CONVERGENCE_STRATEGY_HYBRID)
    )
    if not isinstance(raw_value, str):
        raw_value = RUNTIME_CONVERGENCE_STRATEGY_HYBRID
    raw = raw_value.strip().lower()
    if raw in {
        "strict",
        "import-gate-strict",
        "import_gate_strict",
        "import-gate-only",
        "import_gate_only",
    }:
        return RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT
    return RUNTIME_CONVERGENCE_STRATEGY_HYBRID


def is_skill_import_mutation_allowed(
    *,
    runtime_mode: Optional[str] = None,
    convergence_strategy: Optional[str] = None,
) -> bool:
    strategy = resolve_skill_runtime_convergence_strategy(convergence_strategy)
    if strategy != RUNTIME_CONVERGENCE_STRATEGY_IMPORT_GATE_STRICT:
        return True
    return resolve_skill_runtime_mode(runtime_mode) == RUNTIME_MODE_IMPORT_GATE


class RuntimeSkillCatalogProjector:
    def __init__(self, *, import_store: Optional[SkillImportStore] = None):
        self.import_store = import_store or SkillImportStore()

    def project_active_import_dirs(self) -> list[SkillDirectorySpec]:
        def version_key(version: str):
            return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", version)]

        latest_by_skill: Dict[str, SkillImportStoredEntry] = {}
        for entry in self.import_store.list_entries():
            record = entry.record
            if record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
                continue
            if record.source_type != SkillImportSourceType.DIRECTORY:
                continue
            if not record.source_ref:
                continue
            previous = latest_by_skill.get(record.skill_name)
            if previous is None:
                latest_by_skill[record.skill_name] = entry
                continue
            previous_record = previous.record
            if record.updated_at > previous_record.updated_at:
                latest_by_skill[record.skill_name] = entry
                continue
            if record.updated_at == previous_record.updated_at and version_key(record.skill_version) > version_key(previous_record.skill_version):
                latest_by_skill[record.skill_name] = entry

        projected: list[SkillDirectorySpec] = []
        for entry in sorted(latest_by_skill.values(), key=lambda item: item.record.skill_name):
            try:
                path = Path(entry.record.source_ref).expanduser().resolve()
            except (OSError, ValueError):
                continue
            if not path.exists():
                continue
            projected.append(SkillDirectorySpec(layer="import", path=str(path)))
        return projected


def refresh_runtime_registry_for_import_gate(
    *,
    skill_registry,
    import_store: Optional[SkillImportStore] = None,
    runtime_mode: Optional[str] = None,
) -> bool:
    if resolve_skill_runtime_mode(runtime_mode) != RUNTIME_MODE_IMPORT_GATE:
        return False
    projector = RuntimeSkillCatalogProjector(import_store=import_store)
    projected_dirs = projector.project_active_import_dirs()
    skill_registry.set_layered_skill_dirs(projected_dirs)
    skill_registry.skill_dirs = [item.path for item in projected_dirs]
    skill_registry.load_all()
    return True
