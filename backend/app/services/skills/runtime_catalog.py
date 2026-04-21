from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict

from app.services.skills.import_models import (
    SkillActivationStatus,
    SkillImportLifecycleState,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec

RUNTIME_MODE_LEGACY = "legacy"
RUNTIME_MODE_IMPORT_GATE = "import-gate"
RUNTIME_MODE_ENV_KEY = "YUE_SKILL_RUNTIME_MODE"


def resolve_skill_runtime_mode(runtime_mode: Optional[str] = None) -> str:
    raw = (runtime_mode or os.getenv(RUNTIME_MODE_ENV_KEY, RUNTIME_MODE_LEGACY)).strip().lower()
    if raw in {"import-gate", "import_gate"}:
        return RUNTIME_MODE_IMPORT_GATE
    return RUNTIME_MODE_LEGACY


class RuntimeSkillCatalogProjector:
    def __init__(self, *, import_store: Optional[SkillImportStore] = None):
        self.import_store = import_store or SkillImportStore()

    def project_active_import_dirs(self) -> list[SkillDirectorySpec]:
        latest_by_skill: Dict[str, SkillImportStoredEntry] = {}
        for entry in self.import_store.list_entries():
            record = entry.record
            if record.activation_status != SkillActivationStatus.ACTIVE:
                continue
            if record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
                continue
            if record.source_type != SkillImportSourceType.DIRECTORY:
                continue
            if not record.source_ref:
                continue
            previous = latest_by_skill.get(record.skill_name)
            if previous is None or record.updated_at > previous.record.updated_at:
                latest_by_skill[record.skill_name] = entry

        projected: list[SkillDirectorySpec] = []
        for entry in sorted(latest_by_skill.values(), key=lambda item: item.record.skill_name):
            path = Path(entry.record.source_ref).expanduser().resolve()
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
