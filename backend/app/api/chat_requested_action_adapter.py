import json
from typing import Any, Dict, List, Optional


def build_requested_action_blocked_payload(*, action_id: str) -> Dict[str, Any]:
    return {
        "event": "skill.action.result",
        "status": "blocked",
        "lifecycle_phase": "preflight",
        "lifecycle_status": "preflight_blocked",
        "skill_name": None,
        "skill_version": None,
        "action_id": action_id,
        "accepted": False,
        "approval_required": False,
        "approval_policy": None,
        "mapped_tool": None,
        "execution_mode": "tool_only",
        "request_id": None,
        "validation_errors": ["No skill selected for requested action"],
        "missing_requirements": [],
    }


def build_requested_action_blocked_message(*, action_id: str) -> str:
    return (
        f"[Action Preflight] `{action_id}` is blocked: no skill selected. "
        "Yue will only continue through approved platform tools, not a skill-owned runner."
    )


def build_requested_action_runtime_contract_metadata(preflight_result: Any) -> Dict[str, Any]:
    metadata = getattr(preflight_result, "metadata", None) or {}
    payload: Dict[str, Any] = {}
    for key in (
        "tool_family",
        "operation",
        "runtime_metadata_expectations",
        "runtime_metadata",
        "browser_continuity",
        "browser_continuity_resolution",
        "browser_continuity_resolver",
    ):
        value = metadata.get(key)
        if value not in (None, {}, []):
            payload[key] = value
    return payload


def should_execute_requested_action_tool(
    *,
    preflight_result: Any,
    approval_result: Optional[Any],
) -> bool:
    if preflight_result.lifecycle_status == "preflight_ready":
        return True
    return (
        preflight_result.lifecycle_status == "preflight_approval_required"
        and approval_result is not None
        and approval_result.lifecycle_status == "approved"
    )


def build_requested_action_transition_metadata(
    *,
    preflight_result: Any,
    approval_result: Optional[Any],
    reason: str,
    tool_args: Dict[str, Any],
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        **build_requested_action_runtime_contract_metadata(preflight_result),
        "reason": reason,
        "mapped_tool": preflight_result.invocation.mapped_tool,
        "approval_token": getattr(approval_result, "approval_token", None),
        "tool_args": tool_args,
        **(extra_metadata or {}),
    }


def _extract_artifact_summary(
    tool_result_payload: Optional[str],
    *,
    mapped_tool: Optional[str] = None,
) -> Optional[str]:
    if not isinstance(tool_result_payload, str) or not tool_result_payload.strip():
        return None
    try:
        payload = json.loads(tool_result_payload)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None

    artifact = payload.get("artifact")
    artifact_kind = ""
    if isinstance(artifact, dict):
        kind = artifact.get("kind")
        if isinstance(kind, str) and kind.strip():
            artifact_kind = kind.strip().lower()

    summary_prefix = "Artifact ready:"
    is_screenshot = artifact_kind == "screenshot" or mapped_tool == "builtin:browser_screenshot"
    if is_screenshot:
        summary_prefix = "Screenshot ready:"

    download_url = payload.get("download_url")
    filename = payload.get("filename")
    if is_screenshot and isinstance(download_url, str) and download_url.strip():
        alt_text = filename.strip() if isinstance(filename, str) and filename.strip() else "browser screenshot"
        return f"{summary_prefix}\n![{alt_text}]({download_url.strip()})"

    download_markdown = payload.get("download_markdown")
    if isinstance(download_markdown, str) and download_markdown.strip():
        return f"{summary_prefix} {download_markdown.strip()}"

    if isinstance(download_url, str) and download_url.strip():
        return f"{summary_prefix} {download_url.strip()}"

    return None


def build_requested_action_messages(
    *,
    preflight_result: Any,
    approval_result: Optional[Any],
    lifecycle_results: List[Any],
    prompt_deps: Any,
    tool_result_payload: Optional[str],
    tool_error_payload: Optional[str],
) -> List[str]:
    messages = [
        prompt_deps.action_preflight_message_builder(preflight_result),
    ]

    if approval_result is not None:
        messages.append(prompt_deps.action_approval_message_builder(approval_result))

    if lifecycle_results:
        messages.append(prompt_deps.action_execution_message_builder(lifecycle_results[-1]))

    if tool_result_payload is not None:
        messages.append(
            f"[Tool Result] `{preflight_result.invocation.mapped_tool}` returned:\n{tool_result_payload}"
        )
        artifact_summary = _extract_artifact_summary(
            tool_result_payload,
            mapped_tool=preflight_result.invocation.mapped_tool,
        )
        if artifact_summary is not None:
            messages.append(artifact_summary)

    if tool_error_payload is not None:
        messages.append(
            f"[Tool Error] `{preflight_result.invocation.mapped_tool}` failed:\n{tool_error_payload}"
        )

    return messages
