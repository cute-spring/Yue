from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RetryTarget:
    provider: str
    model_name: str


def should_handle_tool_call_mismatch(
    *,
    finish_reason: Optional[str],
    tool_call_started_count: int,
) -> bool:
    return finish_reason == "tool_call" and tool_call_started_count == 0


def resolve_retry_targets(
    *,
    mismatch_config: Dict[str, Any],
    provider: str,
    model_name: str,
) -> List[RetryTarget]:
    if not mismatch_config.get("auto_retry_enabled", True):
        return []

    retry_candidates_raw = mismatch_config.get("fallback_models") or [mismatch_config.get("fallback_model", "")]
    retry_candidates = [str(item).strip() for item in retry_candidates_raw if str(item).strip()]
    seen_retry_targets = set()
    current_target = f"{provider}/{model_name}".strip().lower()
    targets: List[RetryTarget] = []
    for retry_target in retry_candidates:
        retry_provider = provider
        retry_model_name = retry_target
        if "/" in retry_target:
            maybe_provider, maybe_model = retry_target.split("/", 1)
            if maybe_provider.strip() and maybe_model.strip():
                retry_provider = maybe_provider.strip()
                retry_model_name = maybe_model.strip()
        normalized_target = f"{retry_provider}/{retry_model_name}".strip().lower()
        if not retry_model_name or normalized_target == current_target or normalized_target in seen_retry_targets:
            continue
        seen_retry_targets.add(normalized_target)
        targets.append(RetryTarget(provider=retry_provider, model_name=retry_model_name))
    return targets


def build_tool_call_retry_event(*, from_provider: str, from_model: str, to_provider: str, to_model: str) -> Dict[str, Any]:
    return {
        "event": "tool_call_retry",
        "from_provider": from_provider,
        "from_model": from_model,
        "to_provider": to_provider,
        "to_model": to_model,
    }


def build_tool_call_retry_success_event(
    *,
    provider: str,
    model: str,
    started: int,
    finished: int,
) -> Dict[str, Any]:
    return {
        "event": "tool_call_retry_success",
        "provider": provider,
        "model": model,
        "started": started,
        "finished": finished,
    }


def build_tool_call_retry_failed_event(*, provider: str, model: str, error: str) -> Dict[str, Any]:
    return {
        "event": "tool_call_retry_failed",
        "provider": provider,
        "model": model,
        "error": error,
    }


def build_tool_call_mismatch_event(*, started: int, finished: int) -> Dict[str, Any]:
    return {
        "event": "tool_call_mismatch",
        "started": started,
        "finished": finished,
    }


def build_tool_call_mismatch_message() -> str:
    return (
        "\n\n> ⚠️ **[系统提示]** 模型返回了 `tool_call` 结束信号，但未产生可执行工具调用。"
        "这通常是当前模型与工具调用协议兼容性问题。"
        "建议切换到已验证支持工具调用的模型（例如 `gpt-4o`/`gpt-4o-mini`），"
        "或重试并明确要求“立即调用工具后再回答”。"
    )
