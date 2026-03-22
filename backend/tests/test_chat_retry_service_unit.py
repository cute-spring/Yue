from app.services.chat_retry_service import (
    RetryTarget,
    should_handle_tool_call_mismatch,
    resolve_retry_targets,
    build_tool_call_retry_event,
    build_tool_call_retry_success_event,
    build_tool_call_retry_failed_event,
    build_tool_call_mismatch_event,
    build_tool_call_mismatch_message,
)


def test_should_handle_tool_call_mismatch():
    assert should_handle_tool_call_mismatch(finish_reason="tool_call", tool_call_started_count=0) is True
    assert should_handle_tool_call_mismatch(finish_reason="tool_call", tool_call_started_count=1) is False
    assert should_handle_tool_call_mismatch(finish_reason="stop", tool_call_started_count=0) is False
    assert should_handle_tool_call_mismatch(finish_reason=None, tool_call_started_count=0) is False


def test_resolve_retry_targets_dedup_and_provider_model_parse():
    mismatch_config = {
        "auto_retry_enabled": True,
        "fallback_models": [
            "gpt-4o",  # same as current -> skip
            "openai/gpt-4o",  # same as current -> skip
            "",
            "deepseek/deepseek-chat",
            "deepseek/deepseek-chat",  # duplicate -> skip
            "gpt-4o-mini",  # -> openai/gpt-4o-mini
            "openai/gpt-4o-mini",  # duplicate of previous normalized target -> skip
            "anthropic/claude-3-5-sonnet",
        ],
    }
    targets = resolve_retry_targets(
        mismatch_config=mismatch_config,
        provider="openai",
        model_name="gpt-4o",
    )
    assert targets == [
        RetryTarget(provider="deepseek", model_name="deepseek-chat"),
        RetryTarget(provider="openai", model_name="gpt-4o-mini"),
        RetryTarget(provider="anthropic", model_name="claude-3-5-sonnet"),
    ]


def test_resolve_retry_targets_uses_fallback_model_when_fallback_models_missing():
    mismatch_config = {
        "auto_retry_enabled": True,
        "fallback_model": "gpt-4o-mini",
    }
    targets = resolve_retry_targets(
        mismatch_config=mismatch_config,
        provider="openai",
        model_name="gpt-4o",
    )
    assert targets == [RetryTarget(provider="openai", model_name="gpt-4o-mini")]


def test_resolve_retry_targets_respects_auto_retry_disabled():
    mismatch_config = {
        "auto_retry_enabled": False,
        "fallback_models": ["gpt-4o-mini", "deepseek/deepseek-chat"],
    }
    targets = resolve_retry_targets(
        mismatch_config=mismatch_config,
        provider="openai",
        model_name="gpt-4o",
    )
    assert targets == []


def test_retry_event_payload_builders():
    assert build_tool_call_retry_event(
        from_provider="openai",
        from_model="gpt-4o",
        to_provider="deepseek",
        to_model="deepseek-chat",
    ) == {
        "event": "tool_call_retry",
        "from_provider": "openai",
        "from_model": "gpt-4o",
        "to_provider": "deepseek",
        "to_model": "deepseek-chat",
    }

    assert build_tool_call_retry_success_event(
        provider="deepseek",
        model="deepseek-chat",
        started=1,
        finished=1,
    ) == {
        "event": "tool_call_retry_success",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "started": 1,
        "finished": 1,
    }

    assert build_tool_call_retry_failed_event(
        provider="deepseek",
        model="deepseek-chat",
        error="network timeout",
    ) == {
        "event": "tool_call_retry_failed",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "error": "network timeout",
    }

    assert build_tool_call_mismatch_event(started=0, finished=0) == {
        "event": "tool_call_mismatch",
        "started": 0,
        "finished": 0,
    }


def test_build_tool_call_mismatch_message():
    message = build_tool_call_mismatch_message()
    assert "tool_call" in message
    assert "gpt-4o" in message

