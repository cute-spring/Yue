import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.contract_gate import validate_sse_payload


logger = logging.getLogger(__name__)


def serialize_sse_payload(payload: Dict[str, Any]) -> str:
    try:
        validate_sse_payload(payload)
        return f"data: {json.dumps(payload)}\n\n"
    except Exception as err:
        logger.exception("SSE contract validation failed")
        safe_payload = {
            "error": f"stream_contract_violation: {err.__class__.__name__}"
        }
        return f"data: {json.dumps(safe_payload)}\n\n"


def resolve_reasoning_state(
    *,
    supports_reasoning: bool,
    deep_thinking_enabled: bool,
    reasoning_display_gated_enabled: bool,
) -> Tuple[bool, Optional[str]]:
    reasoning_disabled_reason_code = None
    if reasoning_display_gated_enabled:
        reasoning_enabled = bool(supports_reasoning and deep_thinking_enabled)
        if not reasoning_enabled:
            if deep_thinking_enabled and not supports_reasoning:
                reasoning_disabled_reason_code = "MODEL_CAPABILITY_MISSING"
            elif not deep_thinking_enabled:
                reasoning_disabled_reason_code = "DEEP_THINKING_DISABLED"
    else:
        reasoning_enabled = bool(supports_reasoning or deep_thinking_enabled)
        if not reasoning_enabled:
            reasoning_disabled_reason_code = "LEGACY_DISABLED"
    return reasoning_enabled, reasoning_disabled_reason_code


def build_runtime_meta_payload(
    *,
    provider: Optional[str],
    model_name: Optional[str],
    tool_names: List[str],
    chat_id: str,
    agent_id: Optional[str],
    run_id: str,
    assistant_turn_id: str,
    turn_binding_enabled: bool,
    supports_reasoning: bool,
    deep_thinking_enabled: bool,
    reasoning_enabled: bool,
    reasoning_disabled_reason_code: Optional[str],
    supports_vision: bool,
    vision_enabled: bool,
    validated_images: List[str],
    fallback_mode: str,
) -> Dict[str, Any]:
    return {
        "meta": {
            "provider": provider,
            "model": model_name,
            "tools": tool_names,
            "context_id": chat_id,
            "agent_id": agent_id,
            "run_id": run_id,
            "assistant_turn_id": assistant_turn_id if turn_binding_enabled else None,
            "supports_reasoning": supports_reasoning,
            "deep_thinking_enabled": deep_thinking_enabled,
            "reasoning_enabled": reasoning_enabled,
            "reasoning_disabled_reason_code": reasoning_disabled_reason_code,
            "supports_vision": supports_vision,
            "vision_enabled": vision_enabled,
            "image_count": len(validated_images),
            "vision_fallback_mode": fallback_mode,
        }
    }


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
