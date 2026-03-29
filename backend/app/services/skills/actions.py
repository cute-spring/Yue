import uuid
from typing import Any, Dict, List, Optional

from app.services.skills.browser_continuity_contracts import (
    BrowserContinuityResolver,
    ExplicitContextBrowserContinuityResolver,
)
from app.services.skills.models import (
    RuntimeBrowserContinuityResolutionRequest,
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionApprovalResult,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionExecutionResult,
    RuntimeSkillActionInvocationResult,
)
from app.services.skills.runtime_planning import (
    build_preflight_result_events,
    build_preflight_result_metadata,
)
from app.services.skills.runtime_contracts import (
    _build_approval_token,
    _build_invocation_id,
    _legacy_status_to_lifecycle_status,
    _resolve_preflight_status,
    build_action_approval_event,
    build_action_approval_message,
    build_action_execution_stub_message,
    build_action_execution_transition_event,
    build_action_preflight_message,
)
class SkillActionExecutionService:
    """
    Platform-tool-bounded bridge for package actions.

    This service intentionally does not execute scripts itself and is not a
    stepping stone toward a skill-owned runner. It exposes a stable
    preflight/status contract so skills stay inside Yue's platform tool
    boundary, including platform tools such as builtin:exec when authorized.
    """

    def __init__(self, registry: Any, continuity_resolver: Any = None):
        self.registry = registry
        self.continuity_resolver = continuity_resolver or ExplicitContextBrowserContinuityResolver()

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
        result_metadata = dict(metadata or {})
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
        continuity_resolution_result = self.continuity_resolver.resolve(
            RuntimeBrowserContinuityResolutionRequest(
                invocation_request=request.invocation,
                invocation_result=invocation,
                request_id=request_id,
                browser_continuity=invocation.metadata.get("browser_continuity", {}),
                browser_continuity_resolution=invocation.metadata.get("browser_continuity_resolution", {}),
            )
        )
        result_metadata = build_preflight_result_metadata(
            request=request,
            invocation=invocation,
            continuity_resolution_result=continuity_resolution_result,
            invocation_id=invocation_id,
        )
        events = build_preflight_result_events(
            invocation=invocation,
            request_id=request_id,
            invocation_id=invocation_id,
            status=status,
            lifecycle_status=lifecycle_status,
            result_metadata=result_metadata,
        )

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
