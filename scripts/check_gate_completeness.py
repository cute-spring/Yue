import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence


RELEASE_ID_PATTERN = re.compile(r"RRG-(\d{8})-(\d{3})")
MEMORY_UNSAFE_PATTERN = re.compile(
    r"response\s*\.\s*content\s*\.\s*decode\(\s*['\"]utf-8['\"]\s*\)"
)
REQUIRED_QUALITY_FIELDS = (
    "backend_unit_regression",
    "frontend_typecheck",
    "frontend_unit",
)
RISK_TIER_BOUNDS = {
    "low": (0, 1),
    "medium": (2, 3),
    "high": (4, 6),
}
ROLLBACK_TARGET_MINUTES = {
    "medium": 15.0,
    "high": 30.0,
}
DEFAULT_PHASE1_DIR = "docs/release_readiness_gate/phase1"
FALLBACK_PHASE1_DIR = "docs/release/phase1"


def normalize_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1].strip()
    return value


def extract_section(content: str, section_marker: str) -> str:
    pattern = re.compile(
        rf"^##\s+.*{re.escape(section_marker)}.*$\n?(?P<body>[\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return ""
    return match.group("body")


def find_field(content: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return None
    return normalize_value(match.group(1))


def parse_quality_evidence(content: str) -> dict[str, dict[str, str]]:
    quality_section = extract_section(content, "Quality Evidence")
    result: dict[str, dict[str, str]] = {}
    current_item: str | None = None
    for line in quality_section.splitlines():
        item_match = re.match(r"^\s*-\s*([a-z0-9_]+)\s*$", line)
        if item_match:
            current_item = item_match.group(1)
            result[current_item] = {}
            continue
        detail_match = re.match(r"^\s*-\s*([a-z_]+)\s*:\s*(.+?)\s*$", line)
        if detail_match and current_item:
            result[current_item][detail_match.group(1)] = normalize_value(detail_match.group(2))
    return result


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    if not re.fullmatch(r"-?\d+", value.strip()):
        return None
    return int(value.strip())


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))


def risk_tier_for_score(score: int) -> str | None:
    for tier, (low, high) in RISK_TIER_BOUNDS.items():
        if low <= score <= high:
            return tier
    return None


def resolve_evidence_path(raw_path: str, phase1_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    candidates = [
        phase1_root / path,
        phase1_root.parents[2] / path,
        phase1_root / "rollback_drills" / path.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_rollback_drill(drill_path: Path, release_id: str, tier: str) -> list[str]:
    errors: list[str] = []
    if not drill_path.exists():
        return [f"{drill_path}: rollback drill file does not exist"]
    content = drill_path.read_text(encoding="utf-8")
    related_release_id = find_field(content, "related_release_id")
    if related_release_id != release_id:
        errors.append(
            f"{drill_path}: related_release_id '{related_release_id}' does not match release_id '{release_id}'"
        )
    drill_tier = find_field(content, "risk_tier")
    if drill_tier and drill_tier.lower() != tier:
        errors.append(f"{drill_path}: risk_tier '{drill_tier}' does not match tier '{tier}'")
    target_met = (find_field(content, "target_met") or "").strip().lower()
    if target_met not in {"yes", "true", "pass"}:
        errors.append(f"{drill_path}: target_met must be yes/true/pass")
    drill_duration = parse_float(find_field(content, "drill_duration_minutes"))
    if drill_duration is None:
        errors.append(f"{drill_path}: drill_duration_minutes is missing or invalid")
    else:
        threshold = ROLLBACK_TARGET_MINUTES[tier]
        if drill_duration > threshold:
            errors.append(
                f"{drill_path}: rollback duration {drill_duration} exceeds {threshold} minutes for {tier} tier"
            )
    recovery_section = extract_section(content, "Recovery Verification")
    if re.search(r"FAIL", recovery_section, re.IGNORECASE):
        errors.append(f"{drill_path}: recovery verification contains FAIL")
    return errors


def validate_report_file(report_path: Path, phase1_root: Path) -> list[str]:
    errors: list[str] = []
    content = report_path.read_text(encoding="utf-8")
    release_id = find_field(content, "release_id")
    if not release_id:
        header_match = re.search(r"^#\s+Gate Report:\s*(RRG-\d{8}-\d{3})\s*$", content, re.MULTILINE)
        if header_match:
            release_id = header_match.group(1)
    if not release_id:
        errors.append(f"{report_path}: missing release_id")
        release_id = report_path.stem

    quality = parse_quality_evidence(content)
    for field in REQUIRED_QUALITY_FIELDS:
        entry = quality.get(field)
        if not entry:
            errors.append(f"{report_path}: missing quality field '{field}'")
            continue
        command = entry.get("command", "").strip()
        result = entry.get("result", "").strip()
        if not command:
            errors.append(f"{report_path}: '{field}' is missing command")
        if not result:
            errors.append(f"{report_path}: '{field}' is missing result")
            continue
        result_upper = result.upper()
        if "PASS" not in result_upper:
            errors.append(f"{report_path}: '{field}' result must be PASS")
        if "FAIL" in result_upper:
            errors.append(f"{report_path}: '{field}' includes FAIL")

    r = parse_int(find_field(content, "runtime_path_touched (R)"))
    d = parse_int(find_field(content, "data_schema_touched (D)"))
    p = parse_int(find_field(content, "ui_api_protocol_touched (P)"))
    risk_score = parse_int(find_field(content, "risk_score"))
    tier = (find_field(content, "tier") or "").strip().lower()

    for label, value in (("R", r), ("D", d), ("P", p)):
        if value is None or value < 0 or value > 2:
            errors.append(f"{report_path}: {label} score must be an integer between 0 and 2")
    if risk_score is None:
        errors.append(f"{report_path}: risk_score is missing or invalid")
    if tier not in RISK_TIER_BOUNDS:
        errors.append(f"{report_path}: tier must be one of low/medium/high")
    if None not in {r, d, p, risk_score}:
        expected_score = r + d + p
        if expected_score != risk_score:
            errors.append(
                f"{report_path}: risk_score {risk_score} does not match R+D+P ({expected_score})"
            )
        expected_tier = risk_tier_for_score(risk_score)
        if expected_tier and tier and tier != expected_tier:
            errors.append(
                f"{report_path}: tier '{tier}' does not match score-derived tier '{expected_tier}'"
            )

    decision_section = extract_section(content, "Decision")
    decision_result = (find_field(decision_section, "result") or "").strip().lower()
    approver = find_field(decision_section, "approver")
    timestamp = find_field(decision_section, "timestamp")
    if decision_result not in {"go", "no-go"}:
        errors.append(f"{report_path}: decision result must be go or no-go")
    if decision_result != "go":
        errors.append(f"{report_path}: decision result must be go for promotion")
    if not approver:
        errors.append(f"{report_path}: missing decision approver")
    if not timestamp:
        errors.append(f"{report_path}: missing decision timestamp")
    else:
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{report_path}: invalid ISO-8601 timestamp '{timestamp}'")

    if tier in {"medium", "high"}:
        drill_ref = find_field(content, "drill_evidence")
        if not drill_ref:
            errors.append(f"{report_path}: medium/high tier requires drill_evidence linkage")
        else:
            drill_path = resolve_evidence_path(drill_ref, phase1_root)
            errors.extend(validate_rollback_drill(drill_path, release_id, tier))
        required_value = (find_field(content, "required") or "").lower()
        if "yes" not in required_value:
            errors.append(f"{report_path}: medium/high tier rollback required must be yes")
        evidence_attached = find_field(content, "evidence_attached")
        if evidence_attached and evidence_attached.lower() not in {"yes", "true"}:
            errors.append(f"{report_path}: evidence_attached must be yes/true when provided")

    return errors


def is_test_file(path: Path) -> bool:
    value = path.as_posix()
    return path.suffix == ".py" and ("/tests/" in value or path.name.startswith("test_"))


def check_memory_safe_patterns(test_files: Sequence[Path]) -> list[str]:
    violations: list[str] = []
    for path in test_files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if MEMORY_UNSAFE_PATTERN.search(content):
            violations.append(
                f"{path}: use response.iter_lines() for stream assertions instead of response.content.decode(\"utf-8\")"
            )
    return violations


def read_changed_files_from_git(repo_root: Path) -> list[Path]:
    command_candidates = [
        ["git", "diff", "--name-only", "--cached", "--diff-filter=ACMRTUXB"],
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"],
        ["git", "diff", "--name-only", "HEAD~1..HEAD", "--diff-filter=ACMRTUXB"],
    ]
    collected: list[Path] = []
    for command in command_candidates:
        try:
            result = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            value = line.strip()
            if not value:
                continue
            path = (repo_root / value).resolve()
            if path not in collected:
                collected.append(path)
    return collected


def release_sort_key(report_path: Path) -> tuple[str, int]:
    match = RELEASE_ID_PATTERN.search(report_path.stem)
    if not match:
        return ("00000000", -1)
    return (match.group(1), int(match.group(2)))


def select_report_files(
    phase1_root: Path,
    explicit_reports: Sequence[str],
    changed_files: Sequence[Path],
) -> list[Path]:
    gate_reports_dir = phase1_root / "gate_reports"
    all_reports = sorted(gate_reports_dir.glob("RRG-*.md"), key=release_sort_key)
    if explicit_reports:
        selected = []
        for value in explicit_reports:
            path = Path(value)
            if not path.is_absolute():
                path = (phase1_root.parents[2] / value).resolve()
            selected.append(path)
        return selected
    changed_reports = [
        path.resolve()
        for path in changed_files
        if "gate_reports" in path.as_posix() and path.suffix == ".md"
    ]
    if changed_reports:
        return changed_reports
    if not all_reports:
        return []
    return [all_reports[-1].resolve()]


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release readiness gate completeness.")
    parser.add_argument(
        "--phase1-dir",
        default=DEFAULT_PHASE1_DIR,
        help="Path to phase1 directory relative to repository root.",
    )
    parser.add_argument(
        "--gate-report-files",
        nargs="*",
        default=[],
        help="Optional specific gate report files to validate.",
    )
    parser.add_argument(
        "--changed-files",
        nargs="*",
        default=[],
        help="Optional changed files list used for memory-safe checks and report selection.",
    )
    return parser.parse_args()


def resolve_phase1_root(repo_root: Path, requested_phase1_dir: str) -> Path:
    primary = (repo_root / requested_phase1_dir).resolve()
    if primary.exists():
        return primary
    if requested_phase1_dir == DEFAULT_PHASE1_DIR:
        fallback = (repo_root / FALLBACK_PHASE1_DIR).resolve()
        if fallback.exists():
            return fallback
    return primary


def main() -> int:
    args = parse_cli_args()
    repo_root = Path(__file__).resolve().parents[1]
    phase1_root = resolve_phase1_root(repo_root, args.phase1_dir)
    if not phase1_root.exists():
        print(f"[ERROR] Phase 1 directory not found: {phase1_root}")
        return 1

    changed_files = []
    if args.changed_files:
        changed_files = [((repo_root / value).resolve()) for value in args.changed_files]
    else:
        changed_files = read_changed_files_from_git(repo_root)

    report_files = select_report_files(phase1_root, args.gate_report_files, changed_files)
    errors: list[str] = []
    if not report_files:
        errors.append("No gate report files found for validation")
    else:
        for report_path in report_files:
            if not report_path.exists():
                errors.append(f"{report_path}: report file does not exist")
                continue
            errors.extend(validate_report_file(report_path, phase1_root))

    test_files = [path for path in changed_files if is_test_file(path)]
    errors.extend(check_memory_safe_patterns(test_files))

    if errors:
        print("[FAIL] Release readiness gate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    validated = ", ".join(str(path.relative_to(repo_root)) for path in report_files)
    print(f"[PASS] Gate reports validated: {validated}")
    if test_files:
        print(f"[PASS] Memory-safe stream assertions check passed for {len(test_files)} modified test file(s)")
    else:
        print("[PASS] No modified test files required memory-safe stream assertion checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
