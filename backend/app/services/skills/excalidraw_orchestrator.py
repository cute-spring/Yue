import json
from typing import Any, Dict, List

from app.services.skills.models import RuntimeSkillActionInvocationResult


EXCALIDRAW_SKILL_NAME = "excalidraw-diagram-generator"
_ACTION_STEP_MAP = {
    "add_icon_to_diagram": "inject_icon",
    "add_arrow_to_diagram": "auto_connect_arrows",
    "split_excalidraw_library": "prepare_icon_library",
}


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


def _resolve_primary_step(action_id: str) -> str:
    return _ACTION_STEP_MAP.get(action_id, "execute_action")


def _extract_output_path(metadata: Dict[str, Any]) -> str | None:
    explicit_path = metadata.get("output_file_path")
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path.strip()

    tool_result = metadata.get("tool_result")
    if isinstance(tool_result, dict):
        output_file_path = tool_result.get("output_file_path")
        if isinstance(output_file_path, str) and output_file_path.strip():
            return output_file_path.strip()
    elif isinstance(tool_result, str):
        try:
            parsed = json.loads(tool_result)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            output_file_path = parsed.get("output_file_path")
            if isinstance(output_file_path, str) and output_file_path.strip():
                return output_file_path.strip()

    return None


def _extract_diagram_path(metadata: Dict[str, Any]) -> str | None:
    validated_args = metadata.get("validated_arguments")
    if isinstance(validated_args, dict):
        diagram_path = validated_args.get("diagram_path")
        if isinstance(diagram_path, str) and diagram_path.strip():
            return diagram_path.strip()
    return None


def _step_status_for_lifecycle(lifecycle_status: str) -> str:
    if lifecycle_status in {"succeeded"}:
        return "completed"
    if lifecycle_status in {"failed", "preflight_blocked"}:
        return "failed"
    if lifecycle_status in {"skipped"}:
        return "skipped"
    return "pending"


def build_excalidraw_output_contract(
    *,
    invocation: RuntimeSkillActionInvocationResult,
    status: str,
    lifecycle_status: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    metadata = dict(metadata or {})
    output_file_path = _extract_output_path(metadata)
    base_diagram_path = _extract_diagram_path(metadata)
    primary_step = _resolve_primary_step(invocation.action_id)
    step_status = _step_status_for_lifecycle(lifecycle_status or status)

    action_steps: List[Dict[str, Any]] = [
        {
            "step": "create_base_diagram",
            "status": "completed" if base_diagram_path else "skipped",
            "detail": "Base diagram path from validated arguments."
            if base_diagram_path
            else "No diagram_path provided in validated arguments.",
        },
        {
            "step": primary_step,
            "status": step_status,
            "detail": f"Lifecycle status is `{lifecycle_status}`.",
        },
        {
            "step": "save_artifact",
            "status": "completed"
            if output_file_path and lifecycle_status == "succeeded"
            else ("failed" if lifecycle_status == "failed" else "pending"),
            "detail": "Artifact output path resolved."
            if output_file_path
            else "Artifact output path not available yet.",
        },
    ]

    warnings = _as_list(metadata.get("warnings"))
    if lifecycle_status == "succeeded" and not output_file_path:
        warnings.append("Execution succeeded but `output_file_path` was not found in tool result metadata.")
    if lifecycle_status == "preflight_blocked":
        reasons = invocation.validation_errors or invocation.missing_requirements
        if reasons:
            warnings.append("Preflight blocked: " + ", ".join(reasons))

    recovery_path = output_file_path or base_diagram_path
    if lifecycle_status == "preflight_blocked":
        failed_step = "preflight_validation"
        retryable = False
        retry_suggestion = "Fix validation errors or missing requirements, then retry the action."
    elif lifecycle_status == "awaiting_approval":
        failed_step = "approval"
        retryable = True
        retry_suggestion = "Approve the action request and retry execution."
    elif lifecycle_status == "failed":
        failed_step = primary_step
        retryable = True
        retry_suggestion = "Retry with corrected arguments/assets, or continue editing the current diagram file."
    else:
        failed_step = None
        retryable = True
        retry_suggestion = "Continue with the next enhancement step if needed."

    failure_recovery = {
        "failed_step": failed_step,
        "retryable": retryable,
        "retry_suggestion": retry_suggestion,
        "continue_editable_file_path": recovery_path,
        "error_message": metadata.get("tool_error"),
    }
    if lifecycle_status == "preflight_blocked":
        error_kind = "configuration_error"
    elif lifecycle_status == "failed":
        error_kind = "retryable_error"
    else:
        error_kind = None
    observability = {
        "started_at": metadata.get("started_at"),
        "finished_at": metadata.get("finished_at"),
        "duration_ms": metadata.get("duration_ms"),
        "error_kind": error_kind,
        "retryable": retryable,
        "artifact_path": output_file_path or base_diagram_path,
    }

    return {
        "output_file_path": output_file_path or base_diagram_path,
        "action_steps": action_steps,
        "warnings": warnings,
        "failure_recovery": failure_recovery,
        "observability": observability,
    }
