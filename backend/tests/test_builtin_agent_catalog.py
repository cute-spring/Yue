from pathlib import Path

import pytest

from app.services.builtin_agent_catalog import BuiltinAgentCatalog


def test_builtin_agent_catalog_loads_default_agents():
    catalog = BuiltinAgentCatalog()
    agents = catalog.list_builtin_agents()

    ids = {agent.id for agent in agents}
    assert ids == {
        "builtin-docs",
        "builtin-local-docs",
        "builtin-architect",
        "builtin-excel-analyst",
        "builtin-pdf-research",
        "builtin-ppt-builder",
        "builtin-action-lab",
        "builtin-translator",
    }


def test_builtin_agent_catalog_rejects_invalid_yaml(tmp_path: Path):
    (tmp_path / "good.yaml").write_text(
        """
id: builtin-ok
name: OK
system_prompt: ok
""".strip()
    )
    (tmp_path / "bad.yaml").write_text("id: [")

    catalog = BuiltinAgentCatalog(builtin_agents_dir=str(tmp_path))
    with pytest.raises(ValueError, match="bad.yaml"):
        catalog.list_builtin_agents()


def test_builtin_agent_catalog_rejects_missing_required_fields(tmp_path: Path):
    (tmp_path / "missing.yaml").write_text(
        """
id: builtin-missing
name: Missing Prompt
""".strip()
    )

    catalog = BuiltinAgentCatalog(builtin_agents_dir=str(tmp_path))
    with pytest.raises(ValueError, match="missing.yaml"):
        catalog.list_builtin_agents()


def test_builtin_agent_catalog_rejects_duplicate_ids(tmp_path: Path):
    (tmp_path / "first.yaml").write_text(
        """
id: builtin-dup
name: First
system_prompt: first
""".strip()
    )
    (tmp_path / "second.yaml").write_text(
        """
id: builtin-dup
name: Second
system_prompt: second
""".strip()
    )

    catalog = BuiltinAgentCatalog(builtin_agents_dir=str(tmp_path))
    with pytest.raises(ValueError, match="duplicate"):
        catalog.list_builtin_agents()
