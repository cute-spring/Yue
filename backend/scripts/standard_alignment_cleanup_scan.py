import argparse
import json
from pathlib import Path
from typing import Iterable, List


DEFAULT_MARKERS: List[str] = [
    "标准对齐清理",
    "旧的多格式",
    "创作平台叙事",
    "deprecated path",
    "弃用路径",
    "旧路径",
]

_IGNORED_DIRS = {".git", ".pytest_cache", "__pycache__", "node_modules", "dist", "build", ".venv"}


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        yield path


def _first_match(lines: list[str], markers: List[str]) -> tuple[str | None, int | None, str | None]:
    for index, line in enumerate(lines, start=1):
        for marker in markers:
            if marker in line:
                return marker, index, line.strip()
    return None, None, None


def _suggested_action(marker: str) -> str:
    if marker == "标准对齐清理":
        return "Reword or remove the legacy alignment language in this file."
    if marker in {"旧的多格式", "创作平台叙事"}:
        return "Remove the legacy product framing from this line."
    if marker in {"deprecated path", "弃用路径", "旧路径"}:
        return "Replace the deprecated path reference and re-run the scan."
    return "Review this legacy marker and replace it with the current approved wording."


def scan(root: Path, markers: List[str] | None = None) -> dict:
    root = root.resolve()
    markers = markers or DEFAULT_MARKERS
    warnings = []
    marker_counts: dict[str, int] = {}
    scanned_files = 0

    for path in _iter_text_files(root):
        scanned_files += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        marker, line_no, excerpt = _first_match(text.splitlines(), markers)
        if marker is None:
            continue

        try:
            display_path = str(path.relative_to(root))
        except ValueError:
            display_path = str(path)

        warnings.append(
            {
                "path": display_path,
                "line": line_no,
                "marker": marker,
                "excerpt": excerpt,
                "suggested_action": _suggested_action(marker),
            }
        )
        marker_counts[marker] = marker_counts.get(marker, 0) + 1

    report = {
        "root": str(root),
        "scanned_file_count": scanned_files,
        "finding_count": len(warnings),
        "marker_counts": marker_counts,
        "warnings": warnings,
        "status": "warn" if warnings else "clean",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--marker", action="append", dest="markers")
    args = parser.parse_args()

    report = scan(Path(args.root), markers=args.markers)
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["finding_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
