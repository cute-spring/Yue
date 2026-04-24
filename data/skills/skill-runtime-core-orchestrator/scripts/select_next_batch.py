#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


SECTION_PATTERN = re.compile(r"^## (?P<title>.+)$", re.MULTILINE)
TASK_PATTERN = re.compile(r"- `(?P<task>[A-Z]\d+)`")


def extract_section(text: str, title: str) -> str:
    matches = list(SECTION_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        if match.group("title") != title:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end]
    return ""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: select_next_batch.py <status-markdown-path>", file=sys.stderr)
        return 2

    status_path = Path(sys.argv[1]).expanduser().resolve()
    if not status_path.exists():
        print(f"missing status file: {status_path}", file=sys.stderr)
        return 1

    text = status_path.read_text(encoding="utf-8")
    pending = TASK_PATTERN.findall(extract_section(text, "Pending"))
    parallel = TASK_PATTERN.findall(extract_section(text, "Parallelizable Candidates"))
    blockers = extract_section(text, "Blockers").strip()

    print(f"status_file: {status_path}")
    print(f"pending_tasks: {', '.join(pending) if pending else 'none'}")
    print(f"parallel_candidates: {', '.join(parallel) if parallel else 'none'}")
    print(f"blockers: {blockers if blockers else 'none'}")

    if pending:
        primary = pending[0]
        sidecars = [task for task in parallel if task != primary][:3]
        print(f"recommended_primary: {primary}")
        print(f"recommended_sidecars: {', '.join(sidecars) if sidecars else 'none'}")
    else:
        print("recommended_primary: none")
        print("recommended_sidecars: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
