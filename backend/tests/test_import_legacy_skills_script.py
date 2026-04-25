from pathlib import Path

from app.services.skills.import_models import SkillImportLifecycleState
from app.services.skills.import_store import SkillImportStore
from scripts.import_legacy_skills_to_import_gate import (
    collect_legacy_skill_candidates,
    replace_active_import,
    run_batch_import,
)


def _write_skill_package(root: Path, *, skill_name: str, version: str = "1.0.0") -> Path:
    package_dir = root / skill_name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {skill_name}
version: {version}
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are a test skill.
""",
        encoding="utf-8",
    )
    return package_dir


def test_collect_legacy_skill_candidates_skips_markdown_files(tmp_path):
    root = tmp_path / "skills"
    root.mkdir()
    _write_skill_package(root, skill_name="pkg-one")
    (root / "legacy-only.md").write_text("# legacy", encoding="utf-8")

    candidates, skipped = collect_legacy_skill_candidates(source_dirs=[("workspace", root)])

    assert [item.path.name for item in candidates] == ["pkg-one"]
    assert any("legacy_markdown_file:workspace:" in item for item in skipped)


def test_run_batch_import_replace_active_supersedes_previous_version(tmp_path):
    source_root = tmp_path / "skills"
    source_root.mkdir()
    _write_skill_package(source_root, skill_name="demo-skill", version="1.0.0")

    candidates, _ = collect_legacy_skill_candidates(source_dirs=[("workspace", source_root)])
    first = run_batch_import(
        candidates=candidates,
        activation_mode="activate-missing",
        data_dir=tmp_path / "data",
    )
    assert first["counts"]["active"] == 1

    source_root_v2 = tmp_path / "skills-v2"
    source_root_v2.mkdir()
    _write_skill_package(source_root_v2, skill_name="demo-skill", version="2.0.0")
    candidates_v2, _ = collect_legacy_skill_candidates(source_dirs=[("workspace", source_root_v2)])
    second = run_batch_import(
        candidates=candidates_v2,
        activation_mode="replace-active",
        data_dir=tmp_path / "data",
    )

    assert second["items"][0]["activation_result"] == "replaced"
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    entries = [item for item in store.list_entries() if item.record.skill_name == "demo-skill"]
    by_version = {item.record.skill_version: item for item in entries}
    assert by_version["1.0.0"].record.lifecycle_state == SkillImportLifecycleState.SUPERSEDED
    assert by_version["2.0.0"].record.lifecycle_state == SkillImportLifecycleState.ACTIVE


def test_replace_active_import_activates_when_no_existing_active(tmp_path):
    source_root = tmp_path / "skills"
    source_root.mkdir()
    _write_skill_package(source_root, skill_name="solo-skill")
    candidates, _ = collect_legacy_skill_candidates(source_dirs=[("workspace", source_root)])
    result = run_batch_import(
        candidates=candidates,
        activation_mode="import-only",
        data_dir=tmp_path / "data",
    )

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    new_entry = store.get_entry(result["items"][0]["import_id"])
    assert new_entry is not None

    action = replace_active_import(store=store, new_entry=new_entry)
    assert action == "activated"

    refreshed = store.get_entry(result["items"][0]["import_id"])
    assert refreshed is not None
    assert refreshed.record.lifecycle_state == SkillImportLifecycleState.ACTIVE
