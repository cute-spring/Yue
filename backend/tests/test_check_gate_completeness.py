import importlib.util
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "check_gate_completeness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_gate_completeness", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validate_report_file_accepts_valid_low_risk_report(tmp_path):
    module = _load_module()
    docs_root = tmp_path
    report = docs_root / "gate_reports" / "RRG-20260314-001.md"
    _write(
        report,
        """# Gate Report: RRG-20260314-001
## 2) Quality Evidence
- backend_unit_regression
  - command: `pytest tests/test_api_chat_unit.py -q`
  - result: `PASS (21 passed)`
- frontend_typecheck
  - command: `npx tsc --noEmit`
  - result: `PASS (exit code 0)`
- frontend_unit
  - command: `npm run test`
  - result: `PASS (14 passed)`
## 3) Risk Scoring
- runtime_path_touched (R): `0`
- data_schema_touched (D): `0`
- ui_api_protocol_touched (P): `1`
- risk_score: `1`
- tier: `low`
## 5) Decision
- result: `go`
- approver: `release-owner-manual-phase1`
- timestamp: `2026-03-14T22:31:00+08:00`
""",
    )
    errors = module.validate_report_file(report, docs_root)
    assert errors == []


def test_validate_report_file_requires_rollback_drill_for_medium_risk(tmp_path):
    module = _load_module()
    docs_root = tmp_path
    report = docs_root / "gate_reports" / "RRG-20260314-003.md"
    _write(
        report,
        """# Gate Report: RRG-20260314-003
## 2) Quality Evidence
- backend_unit_regression
  - command: `pytest tests/test_api_chat_unit.py -q`
  - result: `PASS (21 passed)`
- frontend_typecheck
  - command: `npx tsc --noEmit`
  - result: `PASS (exit code 0)`
- frontend_unit
  - command: `npm run test`
  - result: `PASS (14 passed)`
## 3) Risk Scoring
- runtime_path_touched (R): `1`
- data_schema_touched (D): `0`
- ui_api_protocol_touched (P): `1`
- risk_score: `2`
- tier: `medium`
## 4) Rollback Readiness
- required: `yes (medium tier)`
## 5) Decision
- result: `go`
- approver: `release-owner-manual-phase1`
- timestamp: `2026-03-14T22:33:00+08:00`
""",
    )
    errors = module.validate_report_file(report, docs_root)
    assert any("drill_evidence" in error for error in errors)


def test_validate_report_file_rejects_failed_rollback_drill(tmp_path):
    module = _load_module()
    docs_root = tmp_path
    drill = docs_root / "rollback_drills" / "RBD-20260314-001.md"
    _write(
        drill,
        """# Rollback Drill Evidence: RBD-20260314-001
- related_release_id: `RRG-20260314-003`
- risk_tier: `medium`
- drill_duration_minutes: `17`
- target_met: `no`
""",
    )
    report = docs_root / "gate_reports" / "RRG-20260314-003.md"
    _write(
        report,
        """# Gate Report: RRG-20260314-003
## 2) Quality Evidence
- backend_unit_regression
  - command: `pytest tests/test_api_chat_unit.py -q`
  - result: `PASS (21 passed)`
- frontend_typecheck
  - command: `npx tsc --noEmit`
  - result: `PASS (exit code 0)`
- frontend_unit
  - command: `npm run test`
  - result: `PASS (14 passed)`
## 3) Risk Scoring
- runtime_path_touched (R): `1`
- data_schema_touched (D): `0`
- ui_api_protocol_touched (P): `1`
- risk_score: `2`
- tier: `medium`
## 4) Rollback Readiness
- drill_evidence: `rollback_drills/RBD-20260314-001.md`
## 5) Decision
- result: `go`
- approver: `release-owner-manual-phase1`
- timestamp: `2026-03-14T22:33:00+08:00`
""",
    )
    errors = module.validate_report_file(report, docs_root)
    assert any("target_met" in error or "duration" in error for error in errors)


def test_check_memory_safe_patterns_rejects_response_decode(tmp_path):
    module = _load_module()
    test_file = tmp_path / "tests" / "test_api_chat_unit.py"
    decode_expr = 'response.' + 'content' + '.decode("utf-8")'
    _write(
        test_file,
        f"""def test_stream():
    body = {decode_expr}
    assert "event: content" in body
""",
    )
    violations = module.check_memory_safe_patterns([test_file])
    assert violations


def test_resolve_phase1_root_falls_back_to_docs_release_phase1(tmp_path):
    module = _load_module()
    (tmp_path / "docs" / "release" / "phase1").mkdir(parents=True)

    resolved = module.resolve_phase1_root(tmp_path, module.DEFAULT_PHASE1_DIR)

    assert resolved == (tmp_path / "docs" / "release" / "phase1").resolve()
