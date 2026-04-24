#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    "## Objective",
    "## Locked Scope",
    "## Source Docs",
    "## Current Stage",
    "## Current Batch",
    "## Completed",
    "## Pending",
    "## Parallelizable Candidates",
    "## Blockers",
    "## Latest Verification",
    "## Scope Drift Check",
    "## Recommended Next Batch",
    "## Decision Log",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_status.py <status-markdown-path>", file=sys.stderr)
        return 2

    status_path = Path(sys.argv[1]).expanduser().resolve()
    if not status_path.exists():
        print(f"missing status file: {status_path}", file=sys.stderr)
        return 1

    text = status_path.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        print("missing headings:", file=sys.stderr)
        for heading in missing:
            print(f"- {heading}", file=sys.stderr)
        return 1

    print(f"status file valid: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
