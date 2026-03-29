from typing import Any, Dict, Optional

from app.services.skills.browser_continuity_contracts import (
    BrowserContinuityLookupBackend,
)
from app.services.skills.models import (
    RuntimeBrowserContinuityLookupRequest,
    RuntimeBrowserContinuityLookupResult,
)
from app.services.skills.runtime_contracts import (
    _build_resolved_browser_context_id,
    _non_empty_string,
)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_state_metadata(action_state: Any) -> Dict[str, Any]:
    payload = _as_dict(getattr(action_state, "payload", None))
    return _as_dict(payload.get("metadata"))


def _continuity_record_score(action_state: Any) -> tuple[int, int, int]:
    metadata = _extract_state_metadata(action_state)
    continuity_resolution = _as_dict(metadata.get("browser_continuity_resolution"))
    resolved_context = _as_dict(continuity_resolution.get("resolved_context"))
    validated_arguments = _as_dict(metadata.get("validated_arguments"))

    has_resolved_context = int(
        all(
            _non_empty_string(resolved_context.get(key))
            for key in ("session_id", "tab_id", "element_ref")
        )
    )
    has_argument_context = int(
        all(
            _non_empty_string(validated_arguments.get(key))
            for key in ("session_id", "tab_id", "element_ref")
        )
    )
    state_id = int(getattr(action_state, "id", 0) or 0)
    return (has_resolved_context, has_argument_context, state_id)


def _binding_source_for_state(action_state: Any) -> Optional[str]:
    metadata = _extract_state_metadata(action_state)
    validated_arguments = _as_dict(metadata.get("validated_arguments"))
    return _non_empty_string(validated_arguments.get("binding_source"))


def _record_source_metadata(*, request_id: str, action_state: Any) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "lifecycle_phase": getattr(action_state, "lifecycle_phase", None),
        "lifecycle_status": getattr(action_state, "lifecycle_status", None),
    }


class YueActionStateBrowserContinuityLookupBackend(BrowserContinuityLookupBackend):
    def __init__(self, chat_service: Any):
        self.chat_service = chat_service

    def lookup(
        self,
        request: RuntimeBrowserContinuityLookupRequest,
    ) -> RuntimeBrowserContinuityLookupResult:
        request_id = _non_empty_string(request.request_id)
        if request_id is None:
            return RuntimeBrowserContinuityLookupResult(
                backend_id="yue_action_state",
                status="not_found",
                resolved=False,
                metadata={"reason": "request_id_unavailable"},
            )

        action_states = self.chat_service.list_action_states_by_request_id(
            request_id,
            skill_name=request.invocation_result.skill_name,
            action_id=request.invocation_result.action_id,
        )
        if not action_states:
            return RuntimeBrowserContinuityLookupResult(
                backend_id="yue_action_state",
                status="not_found",
                resolved=False,
                metadata={
                    "reason": "action_state_not_found",
                    "lookup_request_id": request_id,
                },
            )
        current_arguments = _as_dict(
            _as_dict(request.invocation_result.metadata).get("validated_arguments")
        )
        current_binding_source = _non_empty_string(current_arguments.get("binding_source"))
        compatible_action_states = action_states
        if current_binding_source is not None:
            matching_action_states = [
                state
                for state in action_states
                if _binding_source_for_state(state) in {None, current_binding_source}
            ]
            if matching_action_states:
                compatible_action_states = matching_action_states
        else:
            distinct_binding_sources = sorted(
                {
                    binding_source
                    for binding_source in (
                        _binding_source_for_state(state) for state in action_states
                    )
                    if binding_source is not None
                }
            )
            if len(distinct_binding_sources) > 1:
                action_state = max(action_states, key=_continuity_record_score)
                return RuntimeBrowserContinuityLookupResult(
                    backend_id="yue_action_state",
                    status="blocked",
                    resolved=False,
                    metadata={
                        "reason": "binding_source_ambiguous",
                        "lookup_request_id": request_id,
                        "candidate_binding_sources": distinct_binding_sources,
                        "record_source": _record_source_metadata(
                            request_id=request_id,
                            action_state=action_state,
                        ),
                    },
                )

        action_state = max(compatible_action_states, key=_continuity_record_score)

        state_metadata = _extract_state_metadata(action_state)
        stored_resolution = _as_dict(state_metadata.get("browser_continuity_resolution"))
        stored_context = _as_dict(stored_resolution.get("resolved_context"))
        stored_arguments = _as_dict(state_metadata.get("validated_arguments"))
        provided_context = _as_dict(request.provided_context)

        resolved_session_id = (
            _non_empty_string(provided_context.get("session_id"))
            or _non_empty_string(stored_context.get("session_id"))
            or _non_empty_string(stored_arguments.get("session_id"))
            or _non_empty_string(stored_arguments.get("binding_session_id"))
        )
        resolved_tab_id = (
            _non_empty_string(provided_context.get("tab_id"))
            or _non_empty_string(stored_context.get("tab_id"))
            or _non_empty_string(stored_arguments.get("tab_id"))
            or _non_empty_string(stored_arguments.get("binding_tab_id"))
        )
        resolved_element_ref = (
            _non_empty_string(provided_context.get("element_ref"))
            or _non_empty_string(stored_context.get("element_ref"))
            or _non_empty_string(stored_arguments.get("element_ref"))
        )

        stored_binding_source = _non_empty_string(stored_arguments.get("binding_source"))
        if (
            stored_binding_source is not None
            and current_binding_source is not None
            and stored_binding_source != current_binding_source
        ):
            return RuntimeBrowserContinuityLookupResult(
                backend_id="yue_action_state",
                status="blocked",
                resolved=False,
                metadata={
                    "reason": "binding_source_mismatch",
                    "lookup_request_id": request_id,
                    "record_source": _record_source_metadata(
                        request_id=request_id,
                        action_state=action_state,
                    ),
                },
            )

        missing_context = [
            *([] if resolved_session_id else ["session_id"]),
            *([] if resolved_tab_id else ["tab_id"]),
            *([] if resolved_element_ref else ["element_ref"]),
        ]
        if missing_context:
            return RuntimeBrowserContinuityLookupResult(
                backend_id="yue_action_state",
                status="not_found",
                resolved=False,
                metadata={
                    "reason": "resolved_context_incomplete",
                    "lookup_request_id": request_id,
                    "missing_context": missing_context,
                    "record_source": _record_source_metadata(
                        request_id=request_id,
                        action_state=action_state,
                    ),
                },
            )

        resolved_context = {
            "resolved_context_id": _build_resolved_browser_context_id(
                session_id=resolved_session_id,
                tab_id=resolved_tab_id,
                element_ref=resolved_element_ref,
                resolution_source="yue_action_state_lookup",
            ),
            "session_id": resolved_session_id,
            "tab_id": resolved_tab_id,
            "element_ref": resolved_element_ref,
            "resolution_mode": "action_state_lookup",
            "resolution_source": "yue_action_state_lookup",
            "resolved_target_kind": "authoritative_target",
        }
        return RuntimeBrowserContinuityLookupResult(
            backend_id="yue_action_state",
            status="resolved",
            resolved=True,
            metadata={
                "resolution_mode": "action_state_lookup",
                "continuity_status": "resolved",
                "session_lookup_required": False,
                "tab_lookup_required": False,
                "target_lookup_required": False,
                "missing_context": [],
                "resolved_context": resolved_context,
                "record_source": _record_source_metadata(
                    request_id=request_id,
                    action_state=action_state,
                ),
            },
        )
