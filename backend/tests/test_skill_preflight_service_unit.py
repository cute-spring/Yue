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


def _write_setup_skill_package(root: Path, name: str, *, runtime: str = "python") -> Path:
    package_dir = root / name
    package_dir.mkdir(parents=True, exist_ok=True)
    commands = (
        ["python -m venv .yue/python/venv"]
        if runtime == "python"
        else ["npm install --prefix .yue/node"]
    )
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {name}
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are {name}.
""",
        encoding="utf-8",
    )
    _write_manifest(
        package_dir,
        f"""format_version: 1
name: {name}
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
install:
  setup:
    runtime: {runtime}
    commands:
      - {commands[0]}
""",
    )
    return package_dir


def _write_manifest(package_dir: Path, content: str) -> None:
    (package_dir / "manifest.yaml").write_text(content, encoding="utf-8")


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


def test_preflight_service_marks_manifest_declared_setup_as_trust_gated(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    package_dir = _write_skill_package(skills_dir, "setup-skill")
    _write_manifest(
        package_dir,
        """format_version: 1
name: setup-skill
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
install:
  setup:
    runtime: python
    commands:
      - python -m venv .yue/python/venv
""",
    )

    service = SkillPreflightService(import_store=SkillImportStore(data_dir=str(tmp_path / "data")))
    records = service.refresh([SkillDirectorySpec(layer="workspace", path=str(skills_dir))])

    assert len(records) == 1
    record = records[0]
    assert record.setup_capable is True
    assert record.setup_required is True
    assert record.trust_status == "untrusted"
    assert record.setup_status == "available"
    assert record.setup_runtime == "python"
    assert record.setup_supported_runtimes == ["python"]
    assert record.last_setup_commands == ["python -m venv .yue/python/venv"]


def test_preflight_service_ignores_markdown_only_install_setup_for_phase1(tmp_path):
    skills_dir = tmp_path / "skills"
    package_dir = skills_dir / "setup-skill"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        """---
name: setup-skill
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
install:
  setup:
    runtime: python
    commands:
      - python -m venv .yue/python/venv
---
## System Prompt
You are setup-skill.
""",
        encoding="utf-8",
    )

    service = SkillPreflightService(import_store=SkillImportStore(data_dir=str(tmp_path / "data")))
    records = service.refresh([SkillDirectorySpec(layer="workspace", path=str(skills_dir))])

    assert len(records) == 1
    record = records[0]
    assert record.setup_capable is False
    assert record.setup_required is False
    assert record.setup_status == "not_needed"


def test_preflight_service_marks_invalid_setup_runtime_as_needs_fix(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    package_dir = _write_skill_package(skills_dir, "bad-setup-skill")
    _write_manifest(
        package_dir,
        """format_version: 1
name: bad-setup-skill
version: 1.0.0
description: test
capabilities: ["analysis"]
entrypoint: system_prompt
install:
  setup:
    runtime: bash
    commands:
      - ./scripts/setup.sh
""",
    )

    service = SkillPreflightService(import_store=SkillImportStore(data_dir=str(tmp_path / "data")))
    records = service.refresh([SkillDirectorySpec(layer="workspace", path=str(skills_dir))])

    assert len(records) == 1
    record = records[0]
    assert record.status == "needs_fix"
    assert record.setup_capable is False
    assert any("install.setup.runtime must be one of: python, node" in issue for issue in record.issues)


def test_preflight_service_derives_setup_state_from_manifest(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    _write_setup_skill_package(skills_dir, "setup-skill", runtime="python")

    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    service = SkillPreflightService(import_store=store)
    records = service.refresh([SkillDirectorySpec(layer="workspace", path=str(skills_dir))])

    assert len(records) == 1
    record = records[0]
    assert record.setup_capable is True
    assert record.setup_required is True
    assert record.setup_runtime == "python"
    assert record.setup_supported_runtimes == ["python"]
    assert record.trust_status == "untrusted"
    assert record.setup_status == "available"
    assert record.package_fingerprint and record.package_fingerprint.startswith("sha256:")
