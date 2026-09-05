from pathlib import Path

import pytest

from app.services.workbench_mode_catalog import WorkbenchModeCatalog


EXPECTED_MODE_IDS = {
    "deep-research",
    "clarify-mode",
    "workspace-glossary",
    "session-handoff",
    "discovery-questionnaire",
    "agent-instruction-review",
}


def test_workbench_mode_catalog_loads_six_builtin_modes():
    catalog = WorkbenchModeCatalog()

    modes = catalog.list_workbench_modes()
    by_id = {mode.id: mode for mode in modes}

    assert set(by_id) == EXPECTED_MODE_IDS
    assert [mode.id for mode in modes] == [
        "clarify-mode",
        "session-handoff",
        "discovery-questionnaire",
        "deep-research",
        "workspace-glossary",
        "agent-instruction-review",
    ]


def test_workbench_modes_declare_shared_contract_fields():
    catalog = WorkbenchModeCatalog()

    for mode in catalog.list_workbench_modes():
        payload = mode.payload
        assert payload["presentation"] == "workbench_mode"
        assert payload["workflow_status"] == "contract_only"
        assert payload["product_boundary"] == "trusted_ai_workbench_skill_runtime"
        assert payload["visible_entry_points"]
        assert payload["expected_outputs"]
        assert payload["routing"]["target"]
        assert payload["routing"]["prompt_policy"]
        assert payload["routing"]["tool_policy"]
        assert payload["safety_boundaries"]
        assert "raw_slash_command_only" not in payload.get("safety_labels", [])


def test_workbench_mode_catalog_rejects_invalid_yaml(tmp_path: Path):
    (tmp_path / "bad.yaml").write_text("id: [", encoding="utf-8")

    catalog = WorkbenchModeCatalog(workbench_modes_dir=str(tmp_path))

    with pytest.raises(ValueError, match="bad.yaml"):
        catalog.list_workbench_modes()


def test_workbench_mode_catalog_rejects_missing_required_fields(tmp_path: Path):
    (tmp_path / "missing.yaml").write_text(
        """
id: clarify-mode
name: Clarify Mode
""".strip(),
        encoding="utf-8",
    )

    catalog = WorkbenchModeCatalog(workbench_modes_dir=str(tmp_path))

    with pytest.raises(ValueError, match="missing.yaml"):
        catalog.list_workbench_modes()


def test_workbench_mode_catalog_rejects_duplicate_ids(tmp_path: Path):
    for filename in ["first.yaml", "second.yaml"]:
        (tmp_path / filename).write_text(
            """
id: clarify-mode
name: Clarify Mode
capability: clarify_mode
purpose: Convert vague requests into decisions.
presentation: workbench_mode
workflow_status: contract_only
product_boundary: trusted_ai_workbench_skill_runtime
suggested_phase: phase_1_mvp
visible_entry_points:
  - kind: shortcut
    label: /clarify
expected_outputs:
  - kind: artifact
    label: Decision brief
safety_boundaries:
  - Do not interrupt simple chats unnecessarily.
routing:
  target: clarify_mode
  activation: manual_first
  prompt_policy: inject_mode_instructions_only
  tool_policy: no_additional_tools
""".strip(),
            encoding="utf-8",
        )

    catalog = WorkbenchModeCatalog(workbench_modes_dir=str(tmp_path))

    with pytest.raises(ValueError, match="duplicate"):
        catalog.list_workbench_modes()
