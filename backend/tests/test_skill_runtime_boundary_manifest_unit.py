from __future__ import annotations

from pathlib import Path

from app.services.skills.boundary_manifest import (
    BOUNDARY_ENTRIES,
    BOUNDARY_MANIFEST,
    ROLE_REUSABLE_AFTER_CLEANUP,
    ROLE_REUSABLE_NOW,
    ROLE_TRANSITIONAL_ONLY,
    ROLE_YUE_ONLY,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DISALLOWED_REUSABLE_IMPORT_SNIPPETS = (
    "from app.services.agent_store import",
    "from app.services.config_service import",
    "from app.services.skill_group_store import",
    "from app.api import",
)


def _read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_boundary_manifest_roles_are_complete_and_unique() -> None:
    expected_roles = {
        ROLE_REUSABLE_NOW,
        ROLE_REUSABLE_AFTER_CLEANUP,
        ROLE_TRANSITIONAL_ONLY,
        ROLE_YUE_ONLY,
    }
    assert set(BOUNDARY_MANIFEST) == expected_roles

    flattened_paths = [entry.path for entry in BOUNDARY_ENTRIES]
    assert len(flattened_paths) == len(set(flattened_paths))
    assert all(entry.rationale.strip() for entry in BOUNDARY_ENTRIES)


def test_boundary_manifest_paths_exist() -> None:
    for relative_path in {path for paths in BOUNDARY_MANIFEST.values() for path in paths}:
        assert (REPO_ROOT / relative_path).exists(), relative_path


def test_reusable_boundary_files_avoid_known_yue_only_imports() -> None:
    reusable_paths = (
        *BOUNDARY_MANIFEST[ROLE_REUSABLE_NOW],
        *BOUNDARY_MANIFEST[ROLE_REUSABLE_AFTER_CLEANUP],
    )

    for relative_path in reusable_paths:
        source = _read_repo_file(relative_path)
        for snippet in DISALLOWED_REUSABLE_IMPORT_SNIPPETS:
            assert snippet not in source, f"{relative_path} should not import {snippet}"


def test_transitional_and_yue_only_shells_are_classified_explicitly() -> None:
    assert "backend/app/services/skill_service.py" in BOUNDARY_MANIFEST[ROLE_TRANSITIONAL_ONLY]
    assert "backend/app/api/skills.py" in BOUNDARY_MANIFEST[ROLE_TRANSITIONAL_ONLY]
    assert "backend/app/api/skill_imports.py" in BOUNDARY_MANIFEST[ROLE_TRANSITIONAL_ONLY]
    assert "backend/app/api/skill_groups.py" in BOUNDARY_MANIFEST[ROLE_YUE_ONLY]
    assert "backend/app/main.py" in BOUNDARY_MANIFEST[ROLE_YUE_ONLY]
