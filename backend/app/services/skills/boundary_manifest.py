from __future__ import annotations

from dataclasses import dataclass


ROLE_REUSABLE_NOW = "reusable_now"
ROLE_REUSABLE_AFTER_CLEANUP = "reusable_after_cleanup"
ROLE_TRANSITIONAL_ONLY = "transitional_only"
ROLE_YUE_ONLY = "yue_only"


@dataclass(frozen=True)
class BoundaryEntry:
    path: str
    role: str
    rationale: str


BOUNDARY_ENTRIES: tuple[BoundaryEntry, ...] = (
    BoundaryEntry(
        path="backend/app/services/skills/models.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Pure runtime data models with no Yue host service coupling.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/parsing.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Package parsing and validation helpers stay inside the runtime core boundary.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/import_models.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Import-gate records and reports are portable runtime contracts.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/import_store.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Filesystem-backed import persistence is reusable in copy-first and package-first hosts.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/import_service.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Import orchestration depends on runtime-core services, not Yue host modules.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/policy.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Policy checks are runtime-domain logic with no Yue-only imports.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/directories.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Directory resolution logic is part of the portable runtime data plane.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/registry.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Registry loading and overlay ordering remain core runtime behavior.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/runtime_catalog.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Runtime catalog projection and mode resolution are core import-gate mechanics.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/runtime_seams.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Runtime seam protocols are the intended host/core contract surface.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/actions.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Action payload shaping belongs to runtime core behavior.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/compatibility.py",
        role=ROLE_REUSABLE_AFTER_CLEANUP,
        rationale="Compatibility logic is close to core but still assumes Yue builtin tool registration defaults.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/routing.py",
        role=ROLE_REUSABLE_NOW,
        rationale="Routing now keeps scoring and attribute-based visibility in core while host-specific group semantics live outside it.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/host_adapters.py",
        role=ROLE_REUSABLE_AFTER_CLEANUP,
        rationale="Host adapter protocols are reusable, but the convenience bundle still mirrors Yue host service shapes.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/bootstrap.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="Bootstrap exposes reusable builders but still ships Yue-default route mounting and repo-relative defaults.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/adapters.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="Legacy adapters preserve Yue agent compatibility and are not part of the future pure core package.",
    ),
    BoundaryEntry(
        path="backend/app/services/skills/__init__.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="The export barrel mixes reusable and transitional symbols for copy-first adoption.",
    ),
    BoundaryEntry(
        path="backend/app/services/skill_service.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="Copy-first compatible shell that centralizes runtime access, but should not survive as pure core.",
    ),
    BoundaryEntry(
        path="backend/app/api/skills.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="Host-local route module that is copyable today but should eventually be replaced by route strategies.",
    ),
    BoundaryEntry(
        path="backend/app/api/skill_imports.py",
        role=ROLE_TRANSITIONAL_ONLY,
        rationale="Host-local import API remains useful for copy-first reuse but is not future core surface.",
    ),
    BoundaryEntry(
        path="backend/app/api/skill_groups.py",
        role=ROLE_YUE_ONLY,
        rationale="Direct skill-group store CRUD reflects Yue host semantics and should stay outside core.",
    ),
    BoundaryEntry(
        path="backend/app/main.py",
        role=ROLE_YUE_ONLY,
        rationale="Application startup wiring remains Yue-specific even after runtime bootstrap improvements.",
    ),
)


BOUNDARY_MANIFEST: dict[str, tuple[str, ...]] = {
    ROLE_REUSABLE_NOW: tuple(entry.path for entry in BOUNDARY_ENTRIES if entry.role == ROLE_REUSABLE_NOW),
    ROLE_REUSABLE_AFTER_CLEANUP: tuple(
        entry.path for entry in BOUNDARY_ENTRIES if entry.role == ROLE_REUSABLE_AFTER_CLEANUP
    ),
    ROLE_TRANSITIONAL_ONLY: tuple(entry.path for entry in BOUNDARY_ENTRIES if entry.role == ROLE_TRANSITIONAL_ONLY),
    ROLE_YUE_ONLY: tuple(entry.path for entry in BOUNDARY_ENTRIES if entry.role == ROLE_YUE_ONLY),
}


BOUNDARY_ENTRY_BY_PATH: dict[str, BoundaryEntry] = {entry.path: entry for entry in BOUNDARY_ENTRIES}
