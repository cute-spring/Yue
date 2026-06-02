import uuid
from typing import Any, Optional


def safe_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def continuation_status_for_request(request: Any, finish_reason: Optional[str] = None) -> Optional[str]:
    continuation_of = safe_text(getattr(request, "continuation_of", None))
    if not continuation_of:
        return "truncated" if finish_reason == "length" else None
    if finish_reason == "length":
        return "truncated"
    if finish_reason in {"GeneratorExit", "TimeoutError"}:
        return "failed"
    return "continued"


def continuation_root_for_request(request: Any) -> Optional[str]:
    return safe_text(getattr(request, "continuation_root_id", None)) or safe_text(
        getattr(request, "continuation_of", None)
    )


def continuation_content_type_for_request(request: Any) -> Optional[str]:
    return safe_text(getattr(request, "continuation_content_type", None))


def safe_role_lookup(config_service: Any, role_name: str) -> Optional[dict[str, str]]:
    resolver = getattr(config_service, "resolve_model_role", None)
    if not callable(resolver):
        return None
    resolved = resolver(role_name)
    if not isinstance(resolved, dict):
        return None
    provider = safe_text(resolved.get("provider"))
    model = safe_text(resolved.get("model"))
    if not provider or not model:
        return None
    return {"provider": provider, "model": model}


def build_authoritative_session_context_user_hint(plan: Any) -> Optional[str]:
    selected_candidates = list(getattr(plan, "selected_candidates", []) or [])
    numbered_option = next(
        (
            candidate
            for candidate in selected_candidates
            if safe_text(getattr(candidate, "content_type", None)) == "numbered_option"
            and safe_text(getattr(candidate, "content", None))
        ),
        None,
    )
    if numbered_option is None:
        return None

    content = safe_text(getattr(numbered_option, "content", None))
    ordinal = getattr(numbered_option, "metadata", {}).get("ordinal") if hasattr(numbered_option, "metadata") else None
    if not content:
        return None

    ordinal_label = f"第{ordinal}个方案" if isinstance(ordinal, int) and ordinal > 0 else "所指方案"
    return (
        "[Authoritative earlier reference]\n"
        f"用户当前追问所指的{ordinal_label}是：{content}\n"
        "先直接依据这条 earlier reference 回答，再继续展开。"
    )


def split_skill_ref(skill_ref: str) -> tuple[str, Optional[str]]:
    if ":" in skill_ref:
        name, version = skill_ref.split(":", 1)
        return name, version or None
    return skill_ref, None


def resolve_requested_action_request_id(request: Any) -> str:
    approval_token = getattr(request, "requested_action_approval_token", None)
    if isinstance(approval_token, str) and approval_token:
        parts = approval_token.rsplit(":", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
    return uuid.uuid4().hex[:12]
