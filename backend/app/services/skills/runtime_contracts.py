import uuid
from typing import Any, Dict, Optional

from app.services.skills.models import (
    RuntimeSkillActionApprovalResult,
    RuntimeSkillActionExecutionResult,
    RuntimeSkillActionInvocationResult,
)


def _legacy_status_to_lifecycle_status(status: str) -> str:
    if status == "approval_required":
        return "preflight_approval_required"
    if status == "awaiting_approval":
        return "awaiting_approval"
    if status == "blocked":
        return "preflight_blocked"
    if status == "queued":
        return "queued"
    if status == "running":
        return "running"
    if status == "succeeded":
        return "succeeded"
    if status == "failed":
        return "failed"
    if status == "skipped":
        return "skipped"
    return "preflight_ready"


def _resolve_preflight_status(result: RuntimeSkillActionInvocationResult) -> tuple[str, str]:
    if result.validation_errors or result.missing_requirements:
        return "blocked", "preflight_blocked"
    if result.approval_required:
        return "approval_required", "preflight_approval_required"
    return "ready", "preflight_ready"


def _build_approval_token(
    *,
    result: RuntimeSkillActionInvocationResult,
    request_id: Optional[str] = None,
) -> str:
    token_base = request_id or "manual"
    return f"approval:{result.skill_name}:{result.skill_version}:{result.action_id}:{token_base}"


def _build_invocation_id(
    *,
    result: RuntimeSkillActionInvocationResult,
    request_id: Optional[str] = None,
) -> str:
    token_base = request_id or uuid.uuid4().hex[:12]
    return f"invoke:{result.skill_name}:{result.skill_version}:{result.action_id}:{token_base}"


def build_action_execution_transition_event(
    *,
    status: str,
    result: RuntimeSkillActionInvocationResult,
    request_id: Optional[str] = None,
    lifecycle_phase: str = "execution",
    lifecycle_status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    invocation_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = build_action_execution_result_event(
        status=status,
        result=result,
        request_id=request_id,
        lifecycle_phase=lifecycle_phase,
        lifecycle_status=lifecycle_status or _legacy_status_to_lifecycle_status(status),
        invocation_id=invocation_id,
    )
    if metadata:
        payload["metadata"] = dict(metadata)
    return payload


def build_action_invocation_event(
    *,
    phase: str,
    result: RuntimeSkillActionInvocationResult,
    request_id: Optional[str] = None,
    invocation_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event": f"skill.action.{phase}",
        "lifecycle_phase": phase,
        "lifecycle_status": f"{phase}_evaluated",
        "skill_name": result.skill_name,
        "skill_version": result.skill_version,
        "action_id": result.action_id,
        "accepted": result.accepted,
        "approval_required": result.approval_required,
        "approval_policy": result.approval_policy,
        "mapped_tool": result.mapped_tool,
        "execution_mode": result.execution_mode,
        "request_id": request_id,
        "invocation_id": invocation_id,
        "validation_errors": list(result.validation_errors),
        "missing_requirements": list(result.missing_requirements),
    }


def build_action_approval_event(
    *,
    result: RuntimeSkillActionInvocationResult,
    approved: bool,
    status: str,
    approval_token: str,
    request_id: Optional[str] = None,
    invocation_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event": "skill.action.approval",
        "lifecycle_phase": "approval",
        "lifecycle_status": status,
        "skill_name": result.skill_name,
        "skill_version": result.skill_version,
        "action_id": result.action_id,
        "accepted": result.accepted,
        "approved": approved,
        "approval_required": result.approval_required,
        "approval_policy": result.approval_policy,
        "approval_token": approval_token,
        "mapped_tool": result.mapped_tool,
        "execution_mode": result.execution_mode,
        "request_id": request_id,
        "invocation_id": invocation_id,
        "validation_errors": list(result.validation_errors),
        "missing_requirements": list(result.missing_requirements),
    }


def build_action_execution_result_event(
    *,
    status: str,
    result: RuntimeSkillActionInvocationResult,
    request_id: Optional[str] = None,
    lifecycle_phase: str = "preflight",
    lifecycle_status: Optional[str] = None,
    invocation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "event": "skill.action.result",
        "status": status,
        "lifecycle_phase": lifecycle_phase,
        "lifecycle_status": lifecycle_status or _legacy_status_to_lifecycle_status(status),
        "skill_name": result.skill_name,
        "skill_version": result.skill_version,
        "action_id": result.action_id,
        "accepted": result.accepted,
        "approval_required": result.approval_required,
        "approval_policy": result.approval_policy,
        "mapped_tool": result.mapped_tool,
        "execution_mode": result.execution_mode,
        "request_id": request_id,
        "invocation_id": invocation_id,
        "validation_errors": list(result.validation_errors),
        "missing_requirements": list(result.missing_requirements),
    }
    if metadata:
        payload["metadata"] = dict(metadata)
    return payload


def build_action_preflight_message(result: RuntimeSkillActionExecutionResult) -> str:
    action_id = result.invocation.action_id
    skill_name = result.invocation.skill_name
    lifecycle_status = result.lifecycle_status or _legacy_status_to_lifecycle_status(result.status)
    if lifecycle_status == "preflight_ready":
        return f"[Action Preflight] `{skill_name}.{action_id}` is ready as a platform-tool action. Yue will only continue through approved platform tools, not a skill-owned runner."
    if lifecycle_status == "preflight_approval_required":
        return f"[Action Preflight] `{skill_name}.{action_id}` requires approval before any platform-tool continuation. Yue will only continue through approved platform tools, not a skill-owned runner."
    reasons = result.invocation.validation_errors or result.invocation.missing_requirements
    reason_text = ", ".join(reasons) if reasons else "unknown reason"
    return f"[Action Preflight] `{skill_name}.{action_id}` is blocked: {reason_text}. Yue will only continue through approved platform tools, not a skill-owned runner."


def build_action_execution_stub_message(result: RuntimeSkillActionExecutionResult) -> str:
    action_id = result.invocation.action_id
    skill_name = result.invocation.skill_name
    if result.lifecycle_status == "queued":
        return f"[Action Flow] `{skill_name}.{action_id}` was queued for platform-tool handling."
    if result.lifecycle_status == "awaiting_approval":
        return f"[Action Flow] `{skill_name}.{action_id}` is awaiting approval before any platform-tool continuation can be considered."
    if result.lifecycle_status == "skipped":
        reason = str((result.metadata or {}).get("reason") or "non_executing_by_design")
        if reason == "approval_required":
            return f"[Action Flow] `{skill_name}.{action_id}` was skipped because approval is still required."
        return f"[Action Flow] `{skill_name}.{action_id}` was skipped because no platform-tool handoff was performed in this stub flow."
    if result.lifecycle_status == "blocked":
        return f"[Action Flow] `{skill_name}.{action_id}` is blocked."
    return f"[Action Flow] `{skill_name}.{action_id}` is in `{result.lifecycle_status}` state."


def build_action_approval_message(result: RuntimeSkillActionApprovalResult) -> str:
    action_id = result.invocation.action_id
    skill_name = result.invocation.skill_name
    if result.lifecycle_status == "approved":
        return f"[Action Approval] `{skill_name}.{action_id}` was approved. Platform-tool action flow can continue."
    if result.lifecycle_status == "rejected":
        return f"[Action Approval] `{skill_name}.{action_id}` was rejected. The action flow will not continue."
    return f"[Action Approval] `{skill_name}.{action_id}` approval request is invalid."


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _build_resolved_browser_context_id(
    *,
    session_id: str,
    tab_id: str,
    element_ref: str,
    resolution_source: str,
) -> str:
    seed = f"{resolution_source}:{session_id}:{tab_id}:{element_ref}"
    return f"browser_ctx:{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"
