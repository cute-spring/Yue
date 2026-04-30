from __future__ import annotations

from app.services.skills.import_models import SkillPreflightRecord
from app.services.skills.import_store import SkillImportStore


def _preflight_record(*, name: str, status: str) -> SkillPreflightRecord:
    return SkillPreflightRecord(
        skill_name=name,
        skill_version="1.0.0",
        skill_ref=f"{name}:1.0.0",
        source_path=f"/tmp/{name}",
        source_layer="workspace",
        status=status,
        issues=[],
        warnings=[],
        suggestions=[],
    )


def test_import_store_preflight_defaults_empty_list(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))

    assert store.list_preflight_records() == []


def test_import_store_saves_and_reads_preflight_record(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = _preflight_record(name="demo-skill", status="available")

    store.save_preflight_record(record)
    items = store.list_preflight_records()

    assert len(items) == 1
    assert items[0].skill_ref == "demo-skill:1.0.0"
    assert items[0].status == "available"


def test_import_store_replace_preflight_records_overwrites_previous(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    old = _preflight_record(name="old-skill", status="unavailable")
    new = _preflight_record(name="new-skill", status="needs_fix")

    store.save_preflight_record(old)
    store.replace_preflight_records([new])
    items = store.list_preflight_records()

    assert len(items) == 1
    assert items[0].skill_ref == "new-skill:1.0.0"
    assert items[0].status == "needs_fix"
