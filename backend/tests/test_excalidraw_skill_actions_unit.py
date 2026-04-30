from pathlib import Path

from app.services.skills.actions import SkillActionExecutionService
from app.services.skills.models import RuntimeSkillActionExecutionRequest, RuntimeSkillActionInvocationRequest
from app.services.skills.registry import SkillRegistry


def _excalidraw_skill_dir() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "skills"
        / "excalidraw-diagram-generator"
    )


def _build_registry() -> SkillRegistry:
    registry = SkillRegistry(skill_dirs=[str(_excalidraw_skill_dir().parent)])
    registry.load_all()
    return registry


def test_excalidraw_actions_have_expected_schema_contracts():
    registry = _build_registry()
    actions = registry.get_action_descriptors("excalidraw-diagram-generator", "1.0.0")
    actions_by_id = {item.id: item for item in actions}

    assert set(actions_by_id.keys()) == {
        "add_icon_to_diagram",
        "add_arrow_to_diagram",
        "split_excalidraw_library",
    }
    add_icon = actions_by_id["add_icon_to_diagram"]
    assert add_icon.tool == "builtin:exec"
    assert add_icon.approval_policy == "manual"
    assert add_icon.input_schema.get("required") == ["diagram_path", "icon_name", "x", "y"]
    assert add_icon.output_schema.get("required") == ["output_file_path"]


def test_validate_action_invocation_accepts_and_preserves_valid_arguments():
    registry = _build_registry()
    request = RuntimeSkillActionInvocationRequest(
        skill_name="excalidraw-diagram-generator",
        skill_version="1.0.0",
        action_id="add_icon_to_diagram",
        enabled_tools=["builtin:exec"],
        arguments={
            "diagram_path": "/tmp/a.excalidraw",
            "icon_name": "EC2",
            "x": 120,
            "y": 80,
            "label": "web",
            "library_path": "/tmp/lib",
        },
    )

    result = registry.validate_action_invocation(request)

    assert result.accepted is True
    assert result.validation_errors == []
    assert result.missing_requirements == []
    assert result.metadata["validated_arguments"]["icon_name"] == "EC2"
    assert result.metadata["validated_arguments"]["library_path"] == "/tmp/lib"


def test_validate_action_invocation_rejects_schema_mismatch():
    registry = _build_registry()
    request = RuntimeSkillActionInvocationRequest(
        skill_name="excalidraw-diagram-generator",
        skill_version="1.0.0",
        action_id="add_icon_to_diagram",
        enabled_tools=["builtin:exec"],
        arguments={
            "diagram_path": "/tmp/a.excalidraw",
            "icon_name": "EC2",
            "x": "not-a-number",
            "y": 80,
        },
    )

    result = registry.validate_action_invocation(request)

    assert result.accepted is False
    assert any("Invalid type for action argument `x`" in item for item in result.validation_errors)


def test_preflight_metadata_contains_validated_argument_passthrough():
    registry = _build_registry()
    service = SkillActionExecutionService(registry)
    preflight = service.preflight(
        RuntimeSkillActionExecutionRequest(
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="excalidraw-diagram-generator",
                skill_version="1.0.0",
                action_id="add_arrow_to_diagram",
                enabled_tools=["builtin:exec"],
                arguments={
                    "diagram_path": "/tmp/diagram.excalidraw",
                    "from_x": 10,
                    "from_y": 20,
                    "to_x": 30,
                    "to_y": 40,
                    "style": "dashed",
                },
            ),
            request_id="req-pass-through",
        )
    )

    validated = preflight.metadata["validated_arguments"]
    assert validated["diagram_path"] == "/tmp/diagram.excalidraw"
    assert validated["style"] == "dashed"
