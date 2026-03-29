from typing import Any, Dict, Optional

from app.services.skills.models import (
    RuntimeBrowserContinuityLookupRequest,
    RuntimeBrowserContinuityLookupResult,
    RuntimeBrowserContinuityResolutionRequest,
    RuntimeBrowserContinuityResolutionResult,
)
from app.services.skills.runtime_contracts import (
    _build_resolved_browser_context_id,
    _non_empty_string,
)


class BrowserContinuityResolver:
    def resolve(
        self,
        request: RuntimeBrowserContinuityResolutionRequest,
    ) -> RuntimeBrowserContinuityResolutionResult:
        raise NotImplementedError


class DefaultBrowserContinuityResolver(BrowserContinuityResolver):
    def resolve(
        self,
        request: RuntimeBrowserContinuityResolutionRequest,
    ) -> RuntimeBrowserContinuityResolutionResult:
        derived_resolution = dict(request.browser_continuity_resolution or {})
        return RuntimeBrowserContinuityResolutionResult(
            resolver_id="default_noop",
            status="deferred" if derived_resolution else "not_applicable",
            resolved=False,
            metadata=derived_resolution,
        )


class BrowserContinuityLookupBackend:
    def lookup(
        self,
        request: RuntimeBrowserContinuityLookupRequest,
    ) -> RuntimeBrowserContinuityLookupResult:
        raise NotImplementedError


class DefaultBrowserContinuityLookupBackend(BrowserContinuityLookupBackend):
    def lookup(
        self,
        request: RuntimeBrowserContinuityLookupRequest,
    ) -> RuntimeBrowserContinuityLookupResult:
        return RuntimeBrowserContinuityLookupResult(
            backend_id="default_noop",
            status="not_configured",
            resolved=False,
            metadata={},
        )


class ExplicitContextBrowserContinuityResolver(BrowserContinuityResolver):
    def __init__(self, lookup_backend: Optional[BrowserContinuityLookupBackend] = None):
        self.lookup_backend = lookup_backend or DefaultBrowserContinuityLookupBackend()

    def resolve(
        self,
        request: RuntimeBrowserContinuityResolutionRequest,
    ) -> RuntimeBrowserContinuityResolutionResult:
        derived_resolution = dict(request.browser_continuity_resolution or {})
        invocation_metadata = (
            request.invocation_result.metadata
            if isinstance(request.invocation_result.metadata, dict)
            else {}
        )
        validated_arguments = (
            invocation_metadata.get("validated_arguments")
            if isinstance(invocation_metadata.get("validated_arguments"), dict)
            else {}
        )
        tool_family = invocation_metadata.get("tool_family")
        operation = invocation_metadata.get("operation")
        resolution_mode = derived_resolution.get("resolution_mode")

        if tool_family != "agent_browser":
            return RuntimeBrowserContinuityResolutionResult(
                resolver_id="explicit_context",
                status="not_applicable",
                resolved=False,
                metadata=derived_resolution,
            )

        if operation not in {"click", "type"}:
            return RuntimeBrowserContinuityResolutionResult(
                resolver_id="explicit_context",
                status="not_applicable",
                resolved=False,
                metadata=derived_resolution,
            )

        if resolution_mode != "session_tab_target_lookup":
            return RuntimeBrowserContinuityResolutionResult(
                resolver_id="explicit_context",
                status="not_applicable",
                resolved=False,
                metadata=derived_resolution,
            )

        session_id = _non_empty_string(validated_arguments.get("session_id"))
        tab_id = _non_empty_string(validated_arguments.get("tab_id"))
        element_ref = _non_empty_string(validated_arguments.get("element_ref"))

        missing_context = [
            *([] if session_id else ["session_id"]),
            *([] if tab_id else ["tab_id"]),
            *([] if element_ref else ["element_ref"]),
        ]
        if missing_context:
            lookup_result = self.lookup_backend.lookup(
                RuntimeBrowserContinuityLookupRequest(
                    invocation_request=request.invocation_request,
                    invocation_result=request.invocation_result,
                    request_id=request.request_id,
                    browser_continuity=request.browser_continuity,
                    browser_continuity_resolution=derived_resolution,
                    provided_context={
                        "session_id": session_id,
                        "tab_id": tab_id,
                        "element_ref": element_ref,
                    },
                    missing_context=missing_context,
                )
            )
            if lookup_result.resolved:
                resolved_resolution = dict(derived_resolution)
                resolved_resolution.update(lookup_result.metadata or {})
                resolved_resolution.setdefault("continuity_status", "resolved")
                resolved_resolution.setdefault("missing_context", [])
                resolved_resolution["lookup_backend"] = {
                    "backend_id": lookup_result.backend_id,
                    "status": lookup_result.status,
                    "resolved": lookup_result.resolved,
                }
                return RuntimeBrowserContinuityResolutionResult(
                    resolver_id="explicit_context",
                    status="resolved",
                    resolved=True,
                    metadata=resolved_resolution,
                )
            blocked_resolution = dict(derived_resolution)
            blocked_resolution["continuity_status"] = "blocked"
            blocked_resolution["missing_context"] = missing_context
            blocked_resolution["resolved_context"] = {}
            blocked_resolution["lookup_backend"] = {
                "backend_id": lookup_result.backend_id,
                "status": lookup_result.status,
                "resolved": lookup_result.resolved,
            }
            if lookup_result.metadata:
                blocked_resolution["lookup_metadata"] = dict(lookup_result.metadata)
            return RuntimeBrowserContinuityResolutionResult(
                resolver_id="explicit_context",
                status="blocked",
                resolved=False,
                metadata=blocked_resolution,
            )

        resolved_context = {
            "resolved_context_id": _build_resolved_browser_context_id(
                session_id=session_id,
                tab_id=tab_id,
                element_ref=element_ref,
                resolution_source="explicit_request_context",
            ),
            "session_id": session_id,
            "tab_id": tab_id,
            "element_ref": element_ref,
            "resolution_mode": "explicit_request_context",
            "resolution_source": "explicit_request_context",
            "resolved_target_kind": "authoritative_target",
        }
        resolved_resolution = dict(derived_resolution)
        resolved_resolution.update(
            {
                "resolution_mode": "explicit_request_context",
                "continuity_status": "resolved",
                "session_lookup_required": False,
                "tab_lookup_required": False,
                "target_lookup_required": False,
                "missing_context": [],
                "resolved_context": resolved_context,
            }
        )
        return RuntimeBrowserContinuityResolutionResult(
            resolver_id="explicit_context",
            status="resolved",
            resolved=True,
            metadata=resolved_resolution,
        )
