from __future__ import annotations

from pathlib import Path

from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec
from app.services.skills.preflight_service import SkillPreflightService


def _write_skill_package(root: Path, name: str, *, requires_env: str | None = None) -> Path:
    package_dir = root / name
    package_dir.mkdir(parents=True, exist_ok=True)
    requires_block = f"requires:\n  env: [\"{requires_env}\"]\n" if requires_env else ""
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {name}
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
{requires_block}---
## System Prompt
You are {name}.
""",
        encoding="utf-8",
    )
    return package_dir


def test_preflight_service_scans_and_persists_records(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    _write_skill_package(skills_dir, "good-skill")
    _write_skill_package(skills_dir, "env-skill", requires_env="DEMO_REQUIRED_ENV")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    evaluator = SkillCompatibilityEvaluator(supported_tools={"builtin:docs_read"}, current_os="darwin")
    service = SkillPreflightService(import_store=store, compatibility_evaluator=evaluator)

    records = service.refresh(
        [SkillDirectorySpec(layer="workspace", path=str(skills_dir))]
    )

    by_ref = {item.skill_ref: item for item in records}
    assert by_ref["good-skill:1.0.0"].status == "available"
    assert by_ref["env-skill:1.0.0"].status == "needs_fix"
    assert store.get_preflight_record("good-skill:1.0.0") is not None
    assert store.get_preflight_record("env-skill:1.0.0") is not None


def test_preflight_service_marks_parse_failure_as_unavailable(tmp_path):
    skills_dir = tmp_path / "skills"
    package_dir = skills_dir / "broken-skill"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text("not-a-valid-skill", encoding="utf-8")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillPreflightService(import_store=store)

    records = service.refresh(
        [SkillDirectorySpec(layer="workspace", path=str(skills_dir))]
    )

    assert len(records) == 1
    assert records[0].status == "unavailable"
    assert "Failed to parse skill package" in records[0].issues[0]
