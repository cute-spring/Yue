from importlib.metadata import version
from types import SimpleNamespace

from app.services.usage_service import calculate_usage


def test_pydantic_ai_v1_compatibility_stage_is_installed():
    """Keep the warning-driven migration stage explicit before V2 work begins."""
    assert version("pydantic-ai-slim") == "1.107.4"


def test_usage_contract_preserves_yue_field_names_for_v1_runs():
    raw_usage = SimpleNamespace(
        request_tokens=11,
        response_tokens=7,
        total_tokens=18,
    )

    usage = calculate_usage("openai", raw_usage, duration=0.5, finish_reason="stop")

    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 18
    assert usage.tps == 14.0
    assert usage.finish_reason == "stop"
