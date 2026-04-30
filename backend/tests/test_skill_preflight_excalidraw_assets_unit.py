from __future__ import annotations

from pathlib import Path

from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec
from app.services.skills.preflight_service import SkillPreflightService


def _write_excalidraw_skill(root: Path) -> Path:
    package_dir = root / "excalidraw-diagram-generator"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        """---
name: excalidraw-diagram-generator
version: 1.0.0
description: test
capabilities: ["diagram_generation"]
entrypoint: system_prompt
---
## System Prompt
You are excalidraw-diagram-generator.
""",
        encoding="utf-8",
    )
    return package_dir


def _refresh_preflight_for(path: Path):
    store = SkillImportStore(data_dir=str(path / ".data"))
    service = SkillPreflightService(import_store=store)
    records = service.refresh([SkillDirectorySpec(layer="workspace", path=str(path))])
    assert len(records) == 1
    return records[0]


def test_excalidraw_preflight_marks_missing_libraries_as_needs_fix(tmp_path):
    _write_excalidraw_skill(tmp_path)

    record = _refresh_preflight_for(tmp_path)

    assert record.status == "needs_fix"
    assert any("libraries/ directory is missing" in issue for issue in record.issues)
    assert any("split-excalidraw-library.py" in suggestion for suggestion in record.suggestions)


def test_excalidraw_preflight_marks_malformed_library_as_needs_fix(tmp_path):
    package_dir = _write_excalidraw_skill(tmp_path)
    malformed_library = package_dir / "libraries" / "aws-icons"
    malformed_library.mkdir(parents=True, exist_ok=True)
    # intentionally malformed: missing reference.md and empty icons/
    (malformed_library / "icons").mkdir(parents=True, exist_ok=True)

    record = _refresh_preflight_for(tmp_path)

    assert record.status == "needs_fix"
    assert any("aws-icons" in issue and "reference.md" in issue for issue in record.issues)
    assert any("aws-icons" in issue and "icons/" in issue for issue in record.issues)


def test_excalidraw_preflight_accepts_healthy_library(tmp_path):
    package_dir = _write_excalidraw_skill(tmp_path)
    healthy_library = package_dir / "libraries" / "aws-icons"
    (healthy_library / "icons").mkdir(parents=True, exist_ok=True)
    (healthy_library / "reference.md").write_text("# aws icons\n", encoding="utf-8")
    (healthy_library / "icons" / "EC2.json").write_text("{}", encoding="utf-8")

    record = _refresh_preflight_for(tmp_path)

    assert record.status == "available"
    assert not any("libraries/" in issue for issue in record.issues)
