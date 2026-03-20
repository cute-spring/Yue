import pytest
from app.services.llm.capabilities import infer_capabilities, CAP_VISION, CAP_REASONING, CAP_FUNCTION_CALLING

@pytest.mark.parametrize(
    "provider,model_name,explicit_caps,expected_caps",
    [
        # Explicit caps take priority
        ("openai", "gpt-4o", ["custom_cap"], ["custom_cap"]),
        
        # Inference for vision
        ("openai", "gpt-4o", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("openai", "gpt-4.5-preview", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("openai", "gpt-4o-mini", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("anthropic", "claude-3-5-sonnet", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("google", "gemini-1.5-pro", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("google", "gemini-1.5-flash", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("google", "gemini-1.0-pro", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        ("custom", "gemini-ultra", None, [CAP_FUNCTION_CALLING, CAP_VISION]), 
        ("zhipu", "glm-4v", None, [CAP_FUNCTION_CALLING, CAP_VISION]),
        
        # Inference for reasoning
        ("google", "gemini-2.0-flash-thinking-exp", None, [CAP_FUNCTION_CALLING, CAP_REASONING, CAP_VISION]),
        ("deepseek", "deepseek-reasoner", None, [CAP_REASONING]),
        ("deepseek", "deepseek-r1", None, [CAP_REASONING]),
        ("openai", "o1-mini", None, [CAP_FUNCTION_CALLING, CAP_REASONING]),
        
        # Text-only exclusions (should not have vision)
        ("openai", "gpt-4", None, [CAP_FUNCTION_CALLING]),  # Base GPT-4 is text-only
        ("openai", "gpt-4-0613", None, [CAP_FUNCTION_CALLING]),
        ("openai", "gpt-3.5-turbo-instruct", None, [CAP_FUNCTION_CALLING]),
    ],
)
def test_infer_capabilities(provider, model_name, explicit_caps, expected_caps):
    caps = infer_capabilities(provider, model_name, explicit_caps)
    # Check if all expected caps are exactly present
    assert set(caps) == set(expected_caps)
