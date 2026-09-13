from __future__ import annotations

import tomllib
from pathlib import Path


def test_backend_declares_session_context_manager_from_an_immutable_source():
    manifest_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    manifest = tomllib.loads(manifest_path.read_text())

    dependencies = manifest["project"]["dependencies"]

    assert (
        "session-context-manager @ "
        "git+https://github.com/cute-spring/session-context-manager.git"
        "@fcc07a62f23df1060b50d6ef499756f1b4eee13f"
    ) in dependencies
    assert manifest["tool"]["hatch"]["metadata"]["allow-direct-references"] is True
