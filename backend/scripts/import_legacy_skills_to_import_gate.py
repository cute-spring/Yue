import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.services.skills.import_models import (
    SkillImportLifecycleState,
    SkillImportStoredEntry,
)
from app.services.skills.import_service import SkillImportService
from app.services.skills.import_store import SkillImportStore


@dataclass(frozen=True)
class LegacySkillCandidate:
    path: Path
    layer: str


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_source_dirs() -> list[tuple[str, Path]]:
    return [
        ("builtin", _backend_root() / "data" / "skills"),
        ("workspace", _workspace_root() / "data" / "skills"),
        ("user", Path(os.path.expanduser("~/.yue/skills"))),
    ]


def _iter_skill_dirs(root: Path) -> Iterable[Path]:
    if not root.exists() or not root.is_dir():
        return []
    return sorted(
        item for item in root.iterdir()
        if item.is_dir() and (item / "SKILL.md").exists()
    )


def collect_legacy_skill_candidates(
    *,
    source_dirs: list[tuple[str, Path]],
) -> tuple[list[LegacySkillCandidate], list[str]]:
    candidates: list[LegacySkillCandidate] = []
    skipped: list[str] = []

    for layer, root in source_dirs:
        if not root.exists():
            skipped.append(f"missing_dir:{layer}:{root}")
            continue
        if not root.is_dir():
            skipped.append(f"not_dir:{layer}:{root}")
            continue

        found_any = False
        for item in sorted(root.iterdir()):
            if item.is_dir():
                if (item / "SKILL.md").exists():
                    candidates.append(LegacySkillCandidate(path=item.resolve(), layer=layer))
                    found_any = True
                continue
            if item.is_file() and item.suffix.lower() == ".md":
                skipped.append(f"legacy_markdown_file:{layer}:{item}")
        if not found_any:
            skipped.append(f"no_package_dirs:{layer}:{root}")

    return candidates, skipped


def _find_active_entry(store: SkillImportStore, skill_name: str) -> SkillImportStoredEntry | None:
    for entry in store.list_entries():
        if entry.record.skill_name != skill_name:
            continue
        if entry.record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
            continue
        return entry
    return None


def replace_active_import(
    *,
    store: SkillImportStore,
    new_entry: SkillImportStoredEntry,
) -> str:
    active_entry = _find_active_entry(store, new_entry.record.skill_name)
    if active_entry is None:
        if new_entry.record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
            new_entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
            new_entry.record.reason_code = "activated_by_batch_import"
            store.save_entry(new_entry)
        return "activated"

    if active_entry.record.id == new_entry.record.id:
        return "already_active"

    active_entry.record.lifecycle_state = SkillImportLifecycleState.SUPERSEDED
    active_entry.record.reason_code = "superseded_by_batch_import"
    active_entry.record.superseded_by_import_id = new_entry.record.id

    new_entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
    new_entry.record.reason_code = "activated_by_batch_replacement"
    new_entry.record.supersedes_import_id = active_entry.record.id

    store.save_entry(active_entry)
    store.save_entry(new_entry)
    return "replaced"


def run_batch_import(
    *,
    candidates: list[LegacySkillCandidate],
    activation_mode: str,
    data_dir: Path | None = None,
) -> dict:
    store = SkillImportStore(data_dir=str(data_dir) if data_dir else None)
    service = SkillImportService(import_store=store)

    imported: list[dict] = []
    for candidate in candidates:
        auto_activate = activation_mode == "activate-missing"
        result = service.import_from_directory(
            candidate.path,
            source_ref=str(candidate.path),
            auto_activate=auto_activate,
        )
        activation_result = "not_requested"

        if activation_mode == "replace-active" and result.report.activation_eligibility == "eligible":
            saved_entry = store.get_entry(result.record.id)
            if saved_entry is not None:
                activation_result = replace_active_import(store=store, new_entry=saved_entry)
            else:
                activation_result = "missing_saved_entry"
        elif result.record.lifecycle_state == SkillImportLifecycleState.ACTIVE:
            activation_result = "active"
        elif result.record.lifecycle_state == SkillImportLifecycleState.INACTIVE:
            activation_result = "inactive"
        elif result.record.lifecycle_state == SkillImportLifecycleState.REJECTED:
            activation_result = "rejected"

        imported.append(
            {
                "path": str(candidate.path),
                "layer": candidate.layer,
                "skill_name": result.record.skill_name,
                "skill_version": result.record.skill_version,
                "import_id": result.record.id,
                "lifecycle_state": result.record.lifecycle_state.value,
                "activation_result": activation_result,
                "eligibility": result.report.activation_eligibility,
                "errors": list(result.report.errors),
                "warnings": list(result.report.warnings),
                "compatibility_issues": list(result.report.compatibility_issues),
            }
        )

    counts = {
        "total_candidates": len(candidates),
        "imported": len(imported),
        "active": sum(1 for item in imported if item["activation_result"] in {"active", "activated", "replaced", "already_active"}),
        "inactive": sum(1 for item in imported if item["activation_result"] == "inactive"),
        "rejected": sum(1 for item in imported if item["activation_result"] == "rejected"),
    }
    return {
        "activation_mode": activation_mode,
        "data_dir": str(data_dir) if data_dir else os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")),
        "counts": counts,
        "items": imported,
    }


def _parse_source_dirs(args: argparse.Namespace) -> list[tuple[str, Path]]:
    if args.source_dir:
        return [("custom", Path(item).expanduser().resolve()) for item in args.source_dir]

    allowed_layers = set(args.layers)
    return [(layer, path.resolve()) for layer, path in _default_source_dirs() if layer in allowed_layers]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch import legacy skill package directories into import-gate storage."
    )
    parser.add_argument(
        "--source-dir",
        action="append",
        help="Explicit legacy skill root directory to scan. Repeatable.",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        choices=["builtin", "workspace", "user"],
        default=["workspace", "user"],
        help="Default legacy layers to scan when --source-dir is not provided.",
    )
    parser.add_argument(
        "--activation-mode",
        choices=["import-only", "activate-missing", "replace-active"],
        default="import-only",
        help="Whether to keep imports inactive, activate only empty slots, or replace current active versions.",
    )
    parser.add_argument(
        "--data-dir",
        help="Override import-gate data directory. Defaults to YUE_DATA_DIR or ~/.yue/data.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only scan and print candidates; do not write skill_imports.json.",
    )
    args = parser.parse_args()

    source_dirs = _parse_source_dirs(args)
    candidates, skipped = collect_legacy_skill_candidates(source_dirs=source_dirs)

    result = {
        "source_dirs": [{"layer": layer, "path": str(path)} for layer, path in source_dirs],
        "dry_run": args.dry_run,
        "activation_mode": args.activation_mode,
        "candidate_count": len(candidates),
        "candidates": [{"layer": item.layer, "path": str(item.path)} for item in candidates],
        "skipped": skipped,
    }

    if not args.dry_run:
        batch = run_batch_import(
            candidates=candidates,
            activation_mode=args.activation_mode,
            data_dir=Path(args.data_dir).expanduser().resolve() if args.data_dir else None,
        )
        result["batch"] = batch

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
