from __future__ import annotations

import tomllib
from pathlib import Path


def test_backend_embeds_session_context_module_without_external_package():
    manifest_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    manifest = tomllib.loads(manifest_path.read_text())

    dependencies = manifest["project"]["dependencies"]

    assert all("session-context-manager" not in dependency for dependency in dependencies)
    module_path = manifest_path.parent / "app" / "modules" / "session_context" / "__init__.py"
    assert module_path.is_file()
