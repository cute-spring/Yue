from __future__ import annotations

import sys
from pathlib import Path

from app.bootstrap_paths import ensure_local_repo_src_paths


def test_ensure_local_repo_src_paths_adds_session_context_manager_src(monkeypatch):
    anchor = Path(__file__).resolve().parents[1] / "app" / "__init__.py"
    expected = str(anchor.parents[2].parent / "session-context-manager" / "src")
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != expected])

    added = ensure_local_repo_src_paths(anchor)

    assert expected in sys.path
    assert expected in added
