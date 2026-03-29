from typing import Any, Dict

from app.services.skills.models import (
    RuntimeBrowserContinuityResolutionResult,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionInvocationResult,
)
from app.services.skills.runtime_contracts import (
    build_action_execution_result_event,
    build_action_invocation_event,
)


def build_preflight_result_metadata(
    *,
    request: RuntimeSkillActionExecutionRequest,
    invocation: RuntimeSkillActionInvocationResult,
    continuity_resolution_result: RuntimeBrowserContinuityResolutionResult,
    invocation_id: str,
) -> Dict[str, Any]:
    resolved_browser_continuity_resolution = (
        continuity_resolution_result.metadata
        if continuity_resolution_result.metadata
        else invocation.metadata.get("browser_continuity_resolution", {})
    )
    return {
        "provider": request.invocation.provider,
        "model_name": request.invocation.model_name,
        "argument_keys": sorted(request.invocation.arguments.keys()),
        "validated_arguments": invocation.metadata.get("validated_arguments", {}),
        "tool_family": invocation.metadata.get("tool_family"),
        "operation": invocation.metadata.get("operation"),
        "runtime_metadata_expectations": invocation.metadata.get("runtime_metadata_expectations", {}),
        "runtime_metadata": invocation.metadata.get("runtime_metadata", {}),
        "browser_continuity": invocation.metadata.get("browser_continuity", {}),
        "browser_continuity_resolution": resolved_browser_continuity_resolution,
        "browser_continuity_resolver": {
            "resolver_id": continuity_resolution_result.resolver_id,
            "status": continuity_resolution_result.status,
            "resolved": continuity_resolution_result.resolved,
        },
        "invocation_id": invocation_id,
    }


def build_preflight_result_events(
    *,
    invocation: RuntimeSkillActionInvocationResult,
    request_id: str,
    invocation_id: str,
    status: str,
    lifecycle_status: str,
    result_metadata: Dict[str, Any],
) -> list[Dict[str, Any]]:
    return [
        build_action_invocation_event(
            phase="preflight",
            result=invocation,
            request_id=request_id,
            invocation_id=invocation_id,
        ),
        build_action_execution_result_event(
            status=status,
            result=invocation,
            request_id=request_id,
            lifecycle_phase="preflight",
            lifecycle_status=lifecycle_status,
            invocation_id=invocation_id,
            metadata=result_metadata,
        ),
    ]
