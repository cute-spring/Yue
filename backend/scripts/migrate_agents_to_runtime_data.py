import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _default_legacy_file() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "agents.json"


def _default_runtime_file() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "agents.json"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _checksum(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def migrate(legacy_file: Path, runtime_file: Path, dry_run: bool = False, force: bool = False) -> dict:
    result = {
        "legacy_file": str(legacy_file),
        "runtime_file": str(runtime_file),
        "dry_run": dry_run,
        "migrated": False,
        "legacy_checksum": None,
        "runtime_checksum_before": None,
        "runtime_checksum_after": None,
        "status": "noop",
    }
    if not legacy_file.exists():
        result["status"] = "legacy_missing"
        return result
    legacy_data = _load_json(legacy_file)
    result["legacy_checksum"] = _checksum(legacy_data)

    runtime_data = None
    if runtime_file.exists():
        runtime_data = _load_json(runtime_file)
        result["runtime_checksum_before"] = _checksum(runtime_data)
        if result["runtime_checksum_before"] == result["legacy_checksum"] and not force:
            result["runtime_checksum_after"] = result["runtime_checksum_before"]
            result["status"] = "already_synced"
            return result

    result["runtime_checksum_after"] = result["legacy_checksum"]
    if dry_run:
        result["status"] = "dry_run"
        return result

    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    with runtime_file.open("w", encoding="utf-8") as f:
        json.dump(legacy_data, f, indent=2, ensure_ascii=False)
    result["migrated"] = True
    result["status"] = "migrated"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-file", default=str(_default_legacy_file()))
    parser.add_argument("--runtime-file", default=str(_default_runtime_file()))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = migrate(
        legacy_file=Path(args.legacy_file),
        runtime_file=Path(args.runtime_file),
        dry_run=args.dry_run,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
