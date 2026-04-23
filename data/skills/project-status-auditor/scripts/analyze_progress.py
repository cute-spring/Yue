import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_doc_sets_path() -> Path:
    return Path(__file__).resolve().parent.parent / "references" / "doc_sets.json"


def _normalize_files(paths: list[Path]) -> list[Path]:
    deduped = {}
    for path in paths:
        deduped[str(path.resolve())] = path.resolve()
    return sorted(deduped.values(), key=lambda item: str(item))


def _scan_markdown_files(plans_dir: Path) -> list[Path]:
    files: list[Path] = []
    for root, _, names in os.walk(plans_dir):
        for name in names:
            if name.endswith(".md"):
                files.append((Path(root) / name).resolve())
    return _normalize_files(files)


def _load_doc_set(doc_set: str, doc_sets_file: Path) -> list[Path]:
    if not doc_sets_file.exists():
        raise FileNotFoundError(f"doc sets file not found: {doc_sets_file}")
    with open(doc_sets_file, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("doc sets file must be a JSON object")
    groups = payload.get("doc_sets", {})
    if not isinstance(groups, dict):
        raise ValueError("doc sets file missing object field: doc_sets")
    selected = groups.get(doc_set)
    if not isinstance(selected, list) or not selected:
        available = ", ".join(sorted(groups.keys()))
        raise ValueError(f"doc set not found or empty: {doc_set}; available: {available}")
    return _normalize_files([Path(item).expanduser() for item in selected if isinstance(item, str)])


def _resolve_targets(args: argparse.Namespace) -> tuple[str, list[Path]]:
    if args.docs:
        return "docs", _normalize_files([Path(item).expanduser() for item in args.docs])
    if args.doc_set:
        return "doc_set", _load_doc_set(args.doc_set, Path(args.doc_sets_file).expanduser())
    plans_dir = Path(args.plans_dir).expanduser()
    if not plans_dir.exists():
        raise FileNotFoundError(f"directory not found: {plans_dir}")
    return "plans_dir", _scan_markdown_files(plans_dir)


def _extract_declared_progress(lines: list[str]) -> list[dict]:
    patterns = [
        re.compile(r"(?P<label>(?:Stage|Epic|Phase)\s*[\w\-. ]+?)\s*[:：|]\s*[~≈约]?\s*(?P<pct>\d{1,3})%"),
        re.compile(r"(?P<label>(?:Stage|Epic|Phase)\s*[\w\-. ]+?)\s*[~≈约]\s*(?P<pct>\d{1,3})%"),
    ]
    results = []
    for idx, line in enumerate(lines, start=1):
        text = line.strip()
        if not text:
            continue
        consumed_spans = set()
        for pattern in patterns:
            for match in pattern.finditer(text):
                span = match.span()
                if span in consumed_spans:
                    continue
                consumed_spans.add(span)
                pct = int(match.group("pct"))
                if pct < 0 or pct > 100:
                    continue
                results.append(
                    {
                        "label": re.sub(r"\s+", " ", match.group("label")).strip(),
                        "percent": pct,
                        "line": idx,
                        "raw": text,
                    }
                )
    return results


def analyze_markdown_file(file_path: Path) -> dict:
    with open(file_path, "r", encoding="utf-8") as handle:
        content = handle.read()
    lines = content.splitlines()

    tasks = re.findall(r"- \[( |x|X)\] (.*)", content)
    completed = [item[1] for item in tasks if item[0].lower() == "x"]
    pending = [item[1] for item in tasks if item[0].strip() == ""]

    declared_progress = _extract_declared_progress(lines)
    task_percent = 0
    if tasks:
        task_percent = round(len(completed) * 100 / len(tasks), 2)

    return {
        "file": str(file_path),
        "total": len(tasks),
        "completed_count": len(completed),
        "pending_count": len(pending),
        "task_completion_percent": task_percent,
        "completed": completed,
        "pending": pending,
        "declared_progress_signals": declared_progress,
    }


def _build_summary(results: list[dict]) -> dict:
    total = sum(item["total"] for item in results)
    completed = sum(item["completed_count"] for item in results)
    pending = sum(item["pending_count"] for item in results)
    overall = round(completed * 100 / total, 2) if total else 0

    pending_items = []
    declared_progress = []
    for item in results:
        pending_items.extend({"file": item["file"], "task": task} for task in item["pending"])
        declared_progress.extend({"file": item["file"], **entry} for entry in item["declared_progress_signals"])

    return {
        "total_task_count": total,
        "completed_task_count": completed,
        "pending_task_count": pending,
        "overall_task_completion_percent": overall,
        "pending_items": pending_items,
        "declared_progress_signals": declared_progress,
    }


def _relpath(path: str) -> str:
    try:
        return os.path.relpath(path, os.getcwd())
    except Exception:
        return path


def _collect_subitem_progress(summary: dict) -> list[dict]:
    # Keep latest signal per label based on source ordering from scan.
    latest_by_label: dict[str, dict] = {}
    for item in summary.get("declared_progress_signals", []):
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        latest_by_label[label] = item
    rows = list(latest_by_label.values())
    rows.sort(key=lambda item: str(item.get("label") or "").lower())
    return rows


def _render_markdown(payload: dict, *, max_pending: int = 200, title: str = "Project Progress Report") -> str:
    summary = payload.get("summary", {})
    docs = payload.get("inputs", {}).get("docs", []) or []
    subitems = _collect_subitem_progress(summary)
    pending_items = summary.get("pending_items", []) or []
    pending_shown = pending_items[:max_pending]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = [
        f"# {title}",
        "",
        f"- Generated at: {generated_at}",
        f"- Mode: `{payload.get('mode')}`",
        f"- Docs analyzed: {len(docs)}",
        "",
        "## Overall Progress",
        "",
        f"- Overall completion: **{summary.get('overall_task_completion_percent', 0)}%**",
        f"- Tasks: {summary.get('completed_task_count', 0)}/{summary.get('total_task_count', 0)} completed",
        "",
        "## Sub-item Progress (%)",
        "",
    ]

    if subitems:
        lines.extend(
            [
                "| Sub-item | Progress | Source |",
                "|---|---:|---|",
            ]
        )
        for item in subitems:
            source = f"{_relpath(str(item.get('file') or ''))}:{item.get('line', 0)}"
            lines.append(f"| {item.get('label', '')} | {item.get('percent', 0)}% | `{source}` |")
    else:
        lines.append("- No declared progress signals found in input docs.")

    lines.extend(
        [
            "",
            "## Unfinished Items",
            "",
        ]
    )
    if pending_shown:
        for item in pending_shown:
            task = str(item.get("task") or "").strip()
            source = _relpath(str(item.get("file") or ""))
            lines.append(f"- [ ] {task} (`{source}`)")
        remaining = max(0, len(pending_items) - len(pending_shown))
        if remaining:
            lines.append(f"- ... and {remaining} more pending items")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze progress from markdown docs. Supports generic doc input via --docs "
            "or named groups via --doc-set. Falls back to --plans-dir scan for compatibility."
        )
    )
    parser.add_argument(
        "--plans-dir",
        default="docs/plans",
        help="Directory to recursively scan markdown files (compat mode when --docs/--doc-set not set).",
    )
    parser.add_argument(
        "--docs",
        nargs="+",
        help="Explicit markdown file paths to analyze.",
    )
    parser.add_argument(
        "--doc-set",
        default="",
        help="Named doc set defined in --doc-sets-file.",
    )
    parser.add_argument(
        "--doc-sets-file",
        default=str(_default_doc_sets_path()),
        help="JSON file that stores named doc sets.",
    )
    parser.add_argument(
        "--output-format",
        default="json",
        choices=["json", "markdown"],
        help="Output format.",
    )
    parser.add_argument(
        "--markdown-out",
        default="",
        help="Optional file path to write markdown report.",
    )
    parser.add_argument(
        "--max-pending",
        type=int,
        default=200,
        help="Max pending items to include in markdown output.",
    )
    parser.add_argument(
        "--title",
        default="Project Progress Report",
        help="Report title for markdown output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        mode, targets = _resolve_targets(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    missing = [str(path) for path in targets if not path.exists()]
    if missing:
        print(
            json.dumps(
                {
                    "mode": mode,
                    "error": "missing_docs",
                    "missing": missing,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    results = [analyze_markdown_file(path) for path in targets]
    payload = {
        "mode": mode,
        "inputs": {
            "plans_dir": str(Path(args.plans_dir).expanduser()),
            "doc_set": args.doc_set or None,
            "doc_sets_file": str(Path(args.doc_sets_file).expanduser()),
            "docs": [str(path) for path in targets],
        },
        "summary": _build_summary(results),
        "files": results,
    }
    markdown_output = ""
    if args.output_format == "markdown" or args.markdown_out:
        markdown_output = _render_markdown(payload, max_pending=max(1, args.max_pending), title=args.title)
        if args.markdown_out:
            out_path = Path(args.markdown_out).expanduser()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown_output, encoding="utf-8")

    try:
        if args.output_format == "markdown":
            print(markdown_output)
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
