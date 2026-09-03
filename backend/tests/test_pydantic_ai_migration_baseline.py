from importlib.metadata import version
from types import SimpleNamespace

from app.services.usage_service import calculate_usage


def test_pydantic_ai_v2_target_is_installed():
    """Keep the production migration target pinned rather than floating."""
    assert version("pydantic-ai-slim") == "2.37.0"


def test_usage_contract_translates_v2_fields_to_yue_field_names():
    raw_usage = SimpleNamespace(
        input_tokens=11,
        output_tokens=7,
        total_tokens=18,
    )

    usage = calculate_usage("openai", raw_usage, duration=0.5, finish_reason="stop")

    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 18
    assert usage.tps == 14.0
    assert usage.finish_reason == "stop"


def test_usage_contract_retains_v1_fields_as_a_compatibility_fallback():
    raw_usage = SimpleNamespace(
        request_tokens=11,
        response_tokens=7,
        total_tokens=18,
    )

    usage = calculate_usage("openai", raw_usage, duration=0.5, finish_reason="stop")

    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
