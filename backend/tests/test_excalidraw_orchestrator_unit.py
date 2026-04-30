import platform

from app.services.skills.actions import SkillActionExecutionService
from app.services.skills.excalidraw_orchestrator import build_excalidraw_output_contract
from app.services.skills.models import RuntimeSkillActionDescriptor, SkillSpec
from app.services.skills.policy import SkillPolicyGate
from app.services.skills.registry import SkillRegistry
from app.services.skills.routing import SkillRouter


def _build_excalidraw_invocation(action_id: str):
    action = RuntimeSkillActionDescriptor(
        id=action_id,
        name="excalidraw-diagram-generator",
        version="1.0.0",
        tool="builtin:exec",
        approval_policy="manual",
    )
    return SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:exec"])


def test_build_excalidraw_output_contract_success_includes_required_fields():
    invocation = _build_excalidraw_invocation("add_icon_to_diagram")

    payload = build_excalidraw_output_contract(
        invocation=invocation,
        status="succeeded",
        lifecycle_status="succeeded",
        metadata={
            "validated_arguments": {
                "diagram_path": "/tmp/diagram.excalidraw",
            },
            "tool_result": {
                "output_file_path": "/tmp/diagram.excalidraw.edit",
            },
        },
    )

    assert payload["output_file_path"] == "/tmp/diagram.excalidraw.edit"
    assert isinstance(payload["action_steps"], list)
    assert payload["action_steps"]
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["failure_recovery"], dict)


def test_skill_action_execution_service_enriches_failed_excalidraw_transition_with_recovery():
    invocation = _build_excalidraw_invocation("add_icon_to_diagram")
    service = SkillActionExecutionService(SkillRegistry())

    result = service.build_transition_result(
        invocation=invocation,
        status="failed",
        request_id="req-excalidraw-fail",
        lifecycle_phase="execution",
        lifecycle_status="failed",
        metadata={
            "validated_arguments": {"diagram_path": "/tmp/diagram.excalidraw"},
            "tool_error": "icon not found",
        },
    )

    assert result.metadata["output_file_path"] == "/tmp/diagram.excalidraw"
    assert isinstance(result.metadata["action_steps"], list)
    assert isinstance(result.metadata["warnings"], list)
    assert result.metadata["failure_recovery"]["failed_step"] == "inject_icon"
    assert result.event_payloads[0]["output_file_path"] == "/tmp/diagram.excalidraw"
    assert result.event_payloads[0]["failure_recovery"]["retryable"] is True


def test_skill_router_contract_exposes_excalidraw_output_protocol():
    registry = SkillRegistry()
    registry.register(
        SkillSpec(
            name="excalidraw-diagram-generator",
            version="1.0.0",
            description="Generate diagram files",
            capabilities=["diagram", "excalidraw"],
            entrypoint="instructions",
            instructions="Generate Excalidraw output",
            os=[platform.system().lower()],
        )
    )
    router = SkillRouter(registry)
    agent = type("Agent", (), {"visible_skills": ["excalidraw-diagram-generator:1.0.0"]})()

    contract = router.route_with_contract(agent, "create excalidraw architecture diagram")

    assert contract["selected"]["name"] == "excalidraw-diagram-generator"
    assert contract["output_protocol"]["required_fields"] == [
        "output_file_path",
        "action_steps",
        "warnings",
    ]
    assert contract["output_protocol"]["failure_recovery_field"] == "failure_recovery"


def test_skill_action_execution_service_includes_observability_fields_for_excalidraw():
    invocation = _build_excalidraw_invocation("add_arrow_to_diagram")
    service = SkillActionExecutionService(SkillRegistry())

    result = service.build_transition_result(
        invocation=invocation,
        status="failed",
        request_id="req-observability",
        lifecycle_phase="execution",
        lifecycle_status="failed",
        metadata={
            "validated_arguments": {"diagram_path": "/tmp/obs.excalidraw"},
            "tool_error": "arrow inference failed",
            "started_at": "2026-04-26T10:00:00Z",
            "finished_at": "2026-04-26T10:00:01Z",
            "duration_ms": 1000,
        },
    )

    observability = result.metadata["observability"]
    assert observability["duration_ms"] == 1000
    assert observability["error_kind"] == "retryable_error"
    assert observability["retryable"] is True
    assert observability["artifact_path"] == "/tmp/obs.excalidraw"
    assert result.event_payloads[0]["observability"]["duration_ms"] == 1000
