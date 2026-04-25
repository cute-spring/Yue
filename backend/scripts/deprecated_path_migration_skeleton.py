import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_manifest(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _resolve_relative(root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _next_step(state: str) -> str:
    if state == "pending":
        return "Preview only: this skeleton does not write files yet."
    if state == "target_exists":
        return "Choose a different replacement path or clean up the existing target first."
    if state == "missing_source":
        return "Restore the deprecated source path or fix the manifest entry."
    if state == "invalid_entry":
        return "Add both deprecated_path and replacement_path to the manifest entry."
    return "Review this entry before any future apply pass."


def plan(root: Path, manifest_file: Path) -> Dict[str, Any]:
    root = root.resolve()
    manifest_file = manifest_file.resolve()
    entries = _load_manifest(manifest_file) if manifest_file.exists() else []

    planned_moves = []
    invalid_entry_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        deprecated_path = str(entry.get("deprecated_path") or entry.get("source") or "")
        replacement_path = str(entry.get("replacement_path") or entry.get("target") or "")
        label = entry.get("label")

        source_path = _resolve_relative(root, deprecated_path)
        target_path = _resolve_relative(root, replacement_path)

        if not deprecated_path or not replacement_path:
            state = "invalid_entry"
            invalid_entry_count += 1
        elif not source_path.exists():
            state = "missing_source"
        elif target_path.exists():
            state = "target_exists"
        else:
            state = "pending"

        planned_moves.append(
            {
                "deprecated_path": deprecated_path,
                "replacement_path": replacement_path,
                "label": label,
                "state": state,
                "next_step": _next_step(state),
            }
        )

    action_required_count = sum(1 for item in planned_moves if item["state"] != "pending")
    ready_move_count = sum(1 for item in planned_moves if item["state"] == "pending")

    return {
        "root": str(root),
        "manifest": str(manifest_file),
        "dry_run": True,
        "applied": False,
        "operation_mode": "preview_only",
        "status": "warn" if action_required_count else "ready",
        "invalid_entry_count": invalid_entry_count,
        "action_required_count": action_required_count,
        "ready_move_count": ready_move_count,
        "planned_move_count": len(planned_moves),
        "planned_moves": planned_moves,
        "written_files": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    report = plan(Path(args.root), Path(args.manifest))
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
