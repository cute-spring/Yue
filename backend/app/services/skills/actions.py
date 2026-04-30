import uuid
from typing import Any, Dict, List, Optional

from app.services.skills.models import (
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionApprovalResult,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionExecutionResult,
    RuntimeSkillActionInvocationResult,
)
from app.services.skills.excalidraw_orchestrator import (
    EXCALIDRAW_SKILL_NAME,
    build_excalidraw_output_contract,
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


def _is_excalidraw_invocation(result: RuntimeSkillActionInvocationResult) -> bool:
    return result.skill_name == EXCALIDRAW_SKILL_NAME


def _apply_excalidraw_output_contract(
    *,
    invocation: RuntimeSkillActionInvocationResult,
    status: str,
    lifecycle_status: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = dict(metadata or {})
    if not _is_excalidraw_invocation(invocation):
        return payload
    payload.update(
        build_excalidraw_output_contract(
            invocation=invocation,
            status=status,
            lifecycle_status=lifecycle_status,
            metadata=payload,
        )
    )
    return payload


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
        for key in ("output_file_path", "action_steps", "warnings", "failure_recovery", "observability"):
            if key in metadata:
                payload[key] = metadata[key]
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
        for key in ("output_file_path", "action_steps", "warnings", "failure_recovery", "observability"):
            if key in metadata:
                payload[key] = metadata[key]
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


class SkillActionExecutionService:
    """
    Platform-tool-bounded bridge for package actions.

    This service intentionally does not execute scripts itself and is not a
    stepping stone toward a skill-owned runner. It exposes a stable
    preflight/status contract so skills stay inside Yue's platform tool
    boundary, including platform tools such as builtin:exec when authorized.
    """

    def __init__(self, registry: Any):
        self.registry = registry

    def build_transition_result(
        self,
        *,
        invocation: RuntimeSkillActionInvocationResult,
        status: str,
        request_id: Optional[str] = None,
        lifecycle_phase: str = "execution",
        lifecycle_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuntimeSkillActionExecutionResult:
        resolved_lifecycle_status = lifecycle_status or _legacy_status_to_lifecycle_status(status)
        result_metadata = _apply_excalidraw_output_contract(
            invocation=invocation,
            status=status,
            lifecycle_status=resolved_lifecycle_status,
            metadata=metadata,
        )
        invocation_id = str(
            result_metadata.get("invocation_id")
            or _build_invocation_id(result=invocation, request_id=request_id)
        )
        result_metadata.setdefault("invocation_id", invocation_id)
        event_payload = build_action_execution_transition_event(
            status=status,
            result=invocation,
            request_id=request_id,
            lifecycle_phase=lifecycle_phase,
            lifecycle_status=resolved_lifecycle_status,
            metadata=result_metadata,
            invocation_id=invocation_id,
        )
        return RuntimeSkillActionExecutionResult(
            status=status,
            lifecycle_phase=lifecycle_phase,
            lifecycle_status=resolved_lifecycle_status,
            invocation=invocation,
            execution_mode="non_executing",
            request_id=request_id,
            event_payloads=[event_payload],
            metadata=result_metadata,
        )

    def build_approval_result(
        self,
        *,
        preflight_result: RuntimeSkillActionExecutionResult,
        approval_request: RuntimeSkillActionApprovalRequest,
    ) -> RuntimeSkillActionApprovalResult:
        invocation = preflight_result.invocation
        invocation_id = str(
            (preflight_result.metadata or {}).get("invocation_id")
            or _build_invocation_id(result=invocation, request_id=preflight_result.request_id)
        )
        approval_token = _build_approval_token(
            result=invocation,
            request_id=preflight_result.request_id,
        )
        if preflight_result.lifecycle_status != "preflight_approval_required":
            status = "invalid"
            approved = False
            metadata = {"reason": "approval_not_required", "approval_token": approval_token, "invocation_id": invocation_id}
        elif approval_request.approval_token and approval_request.approval_token != approval_token:
            status = "invalid"
            approved = False
            metadata = {"reason": "approval_token_mismatch", "approval_token": approval_token, "invocation_id": invocation_id}
        elif approval_request.approved:
            status = "approved"
            approved = True
            metadata = {"reason": "approved", "approval_token": approval_token, "invocation_id": invocation_id}
        else:
            status = "rejected"
            approved = False
            metadata = {"reason": "rejected", "approval_token": approval_token, "invocation_id": invocation_id}

        return RuntimeSkillActionApprovalResult(
            approved=approved,
            status=status,
            lifecycle_phase="approval",
            lifecycle_status=status,
            approval_token=approval_token,
            invocation=invocation,
            request_id=approval_request.request_id or preflight_result.request_id,
            event_payloads=[
                build_action_approval_event(
                    result=invocation,
                    approved=approved,
                    status=status,
                    approval_token=approval_token,
                    request_id=approval_request.request_id or preflight_result.request_id,
                    invocation_id=invocation_id,
                )
            ],
            metadata=metadata,
        )

    def build_stub_execution_results(
        self,
        *,
        preflight_result: RuntimeSkillActionExecutionResult,
        approval_result: Optional[RuntimeSkillActionApprovalResult] = None,
    ) -> List[RuntimeSkillActionExecutionResult]:
        lifecycle_status = preflight_result.lifecycle_status
        if lifecycle_status == "preflight_blocked":
            return []

        request_id = preflight_result.request_id
        invocation = preflight_result.invocation
        base_metadata = {
            "stub": True,
            "provider": (preflight_result.metadata or {}).get("provider"),
            "model_name": (preflight_result.metadata or {}).get("model_name"),
            "validated_arguments": (preflight_result.metadata or {}).get("validated_arguments", {}),
            "invocation_id": (preflight_result.metadata or {}).get("invocation_id"),
        }

        if lifecycle_status == "preflight_approval_required":
            if approval_result and approval_result.lifecycle_status == "approved":
                return [
                    self.build_transition_result(
                        invocation=invocation,
                        status="queued",
                        request_id=request_id,
                        lifecycle_phase="execution",
                        lifecycle_status="queued",
                        metadata={
                            **base_metadata,
                            "reason": "approved_resume",
                            "approval_token": approval_result.approval_token,
                        },
                    ),
                    self.build_transition_result(
                        invocation=invocation,
                        status="skipped",
                        request_id=request_id,
                        lifecycle_phase="execution",
                        lifecycle_status="skipped",
                        metadata={
                            **base_metadata,
                            "reason": "non_executing_by_design",
                            "approval_token": approval_result.approval_token,
                        },
                    ),
                ]
            return [
                self.build_transition_result(
                    invocation=invocation,
                    status="awaiting_approval",
                    request_id=request_id,
                    lifecycle_phase="execution",
                    lifecycle_status="awaiting_approval",
                    metadata={
                        **base_metadata,
                        "reason": "approval_required",
                        "approval_token": _build_approval_token(
                            result=invocation,
                            request_id=request_id,
                        ),
                    },
                )
            ]

        return [
            self.build_transition_result(
                invocation=invocation,
                status="queued",
                request_id=request_id,
                lifecycle_phase="execution",
                lifecycle_status="queued",
                metadata={
                    **base_metadata,
                    "reason": "non_executing_by_design",
                },
            ),
            self.build_transition_result(
                invocation=invocation,
                status="skipped",
                request_id=request_id,
                lifecycle_phase="execution",
                lifecycle_status="skipped",
                metadata={
                    **base_metadata,
                    "reason": "non_executing_by_design",
                },
            ),
        ]

    def preflight(self, request: RuntimeSkillActionExecutionRequest) -> RuntimeSkillActionExecutionResult:
        invocation = self.registry.validate_action_invocation(request.invocation)
        request_id = request.request_id or uuid.uuid4().hex[:12]
        invocation_id = _build_invocation_id(result=invocation, request_id=request_id)
        status, lifecycle_status = _resolve_preflight_status(invocation)
        result_metadata = _apply_excalidraw_output_contract(
            invocation=invocation,
            status=status,
            lifecycle_status=lifecycle_status,
            metadata={
                "provider": request.invocation.provider,
                "model_name": request.invocation.model_name,
                "argument_keys": sorted(request.invocation.arguments.keys()),
                "validated_arguments": invocation.metadata.get("validated_arguments", {}),
                "invocation_id": invocation_id,
            },
        )

        events = [
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

        return RuntimeSkillActionExecutionResult(
            status=status,
            lifecycle_phase="preflight",
            lifecycle_status=lifecycle_status,
            invocation=invocation,
            execution_mode="non_executing",
            request_id=request_id,
            event_payloads=events,
            metadata=result_metadata,
        )
