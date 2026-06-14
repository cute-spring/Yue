from __future__ import annotations

import sys
from pathlib import Path


def ensure_local_repo_src_paths(anchor_file: str | Path | None = None) -> list[str]:
    """Add sibling src-based repos used in local development to sys.path."""
    anchor = Path(anchor_file).resolve() if anchor_file else Path(__file__).resolve()
    repo_root = anchor.parents[2]
    workspace_root = repo_root.parent

    added: list[str] = []
    candidates = [
        workspace_root / "session-context-manager" / "src",
    ]
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate.exists() and candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
            added.append(candidate_str)
    return added
