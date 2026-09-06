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


def test_built_in_workbench_modes_satisfy_release_acceptance_contract():
    catalog = WorkbenchModeCatalog()
    modes = {mode.id: mode.payload for mode in catalog.list_workbench_modes()}

    expected_outputs = {
        "clarify-mode": "Decision brief",
        "session-handoff": "Session handoff",
        "discovery-questionnaire": "Discovery questionnaire",
        "deep-research": "Research report",
        "workspace-glossary": "Workspace glossary entry",
        "agent-instruction-review": "Instruction quality report",
    }
    required_safety_labels = {
        "clarify-mode": {"user_decision_required"},
        "session-handoff": {"redaction_required", "no_external_side_effect", "provenance_recommended"},
        "discovery-questionnaire": {
            "external_send_approval_required",
            "sensitive_data_minimization",
            "human_source_boundary",
        },
        "deep-research": {
            "evidence_required",
            "source_scope_required",
            "missing_evidence_visible",
            "durable_memory_approval_required",
        },
        "workspace-glossary": {
            "durable_memory_approval_required",
            "provenance_required",
            "conflict_review_required",
        },
        "agent-instruction-review": {"admin_only", "advisory_only", "import_gate_required"},
    }

    for mode_id, payload in modes.items():
        assert any(entry["kind"] != "shortcut" for entry in payload["visible_entry_points"])
        assert expected_outputs[mode_id] in {
            output["label"] for output in payload["expected_outputs"]
        }
        assert any(output["reusable_across_sessions"] for output in payload["expected_outputs"])
        assert required_safety_labels[mode_id].issubset(set(payload["safety_labels"]))

        for output in payload["expected_outputs"]:
            if output["workspace_attachment"] == "required":
                assert output["provenance"] in {"required", "recommended"}

    assert modes["workspace-glossary"]["routing"]["activation"] == "user_confirmed_write"
    assert modes["workspace-glossary"]["routing"]["tool_policy"] == "durable_memory_write_requires_approval"
    assert modes["agent-instruction-review"]["routing"]["tool_policy"] == "read_only_skill_metadata"
    assert modes["deep-research"]["routing"]["tool_policy"] == "source_scoped_read_only_for_mvp"


def test_release_validation_records_remaining_risks_and_deferred_items():
    repo_root = Path(__file__).resolve().parents[2]
    validation_path = (
        repo_root
        / "docs"
        / "specs"
        / "yue-built-in-skills"
        / "2026-09-06-release-validation.md"
    )

    content = validation_path.read_text(encoding="utf-8")

    assert "## Remaining Risks" in content
    assert "## Deferred Phase 2 / Phase 3 Items" in content
    for capability in [
        "Deep Research",
        "Clarify Mode",
        "Workspace Glossary / Domain Modeling",
        "Session Handoff",
        "Discovery Questionnaire",
        "Agent Instruction Review",
    ]:
        assert capability in content
    assert "trusted AI workbench and skill runtime platform" in content
    assert "full skill authoring IDE" in content


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
