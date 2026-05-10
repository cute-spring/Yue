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


def _base_record_dump(*, name: str, status: str) -> dict:
    return _preflight_record(name=name, status=status).model_dump(
        exclude={
            "setup_capable",
            "setup_required",
            "trust_status",
            "setup_status",
            "setup_supported_runtimes",
            "setup_runtime",
            "isolated_env_path",
            "package_fingerprint",
            "last_setup_started_at",
            "last_setup_finished_at",
            "last_setup_commands",
            "setup_last_error",
        }
    )


def test_preflight_record_defaults_setup_fields_when_install_setup_not_declared():
    record = _preflight_record(name="plain-skill", status="available")

    assert record.setup_capable is False
    assert record.setup_required is False
    assert record.trust_status == "untrusted"
    assert record.setup_status == "not_needed"
    assert record.setup_supported_runtimes == []
    assert record.setup_last_error is None


def test_import_store_preflight_defaults_empty_list(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))

    assert store.list_preflight_records() == []


def test_import_store_saves_and_reads_preflight_record(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    record = SkillPreflightRecord(
        **_base_record_dump(name="demo-skill", status="available"),
        setup_capable=True,
        setup_required=True,
        trust_status="trusted",
        setup_status="succeeded",
        setup_supported_runtimes=["python"],
        setup_runtime="python",
        isolated_env_path="/tmp/demo-skill/.yue/python/venv",
        package_fingerprint="sha256:demo",
        last_setup_commands=["python -m venv .yue/python/venv"],
        setup_last_error=None,
    )

    store.save_preflight_record(record)
    items = store.list_preflight_records()

    assert len(items) == 1
    assert items[0].skill_ref == "demo-skill:1.0.0"
    assert items[0].status == "available"
    assert items[0].setup_capable is True
    assert items[0].setup_required is True
    assert items[0].trust_status == "trusted"
    assert items[0].setup_status == "succeeded"
    assert items[0].setup_supported_runtimes == ["python"]
    assert items[0].setup_runtime == "python"
    assert items[0].isolated_env_path == "/tmp/demo-skill/.yue/python/venv"
    assert items[0].package_fingerprint == "sha256:demo"
    assert items[0].last_setup_commands == ["python -m venv .yue/python/venv"]


def test_import_store_replace_preflight_records_overwrites_previous(tmp_path):
    store = SkillImportStore(data_dir=str(tmp_path / "data"))
    old = _preflight_record(name="old-skill", status="unavailable")
    new = SkillPreflightRecord(
        **_base_record_dump(name="new-skill", status="needs_fix"),
        setup_capable=True,
        setup_required=True,
        trust_status="trusted",
        setup_status="failed",
        setup_supported_runtimes=["node"],
        setup_runtime="node",
        isolated_env_path="/tmp/new-skill/.yue/node",
        package_fingerprint="sha256:new",
        setup_last_error="npm install failed",
    )

    store.save_preflight_record(old)
    store.replace_preflight_records([new])
    items = store.list_preflight_records()

    assert len(items) == 1
    assert items[0].skill_ref == "new-skill:1.0.0"
    assert items[0].status == "needs_fix"
    assert items[0].setup_capable is True
    assert items[0].trust_status == "trusted"
    assert items[0].setup_status == "failed"
    assert items[0].setup_supported_runtimes == ["node"]
    assert items[0].setup_last_error == "npm install failed"
