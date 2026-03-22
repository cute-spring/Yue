import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.api.chat_helpers import (
    build_runtime_meta_payload,
    iso_utc_now,
    resolve_reasoning_state,
    serialize_sse_payload,
)
from app.api.chat_schemas import ChatRequest, SummaryGenerateRequest, TruncateRequest
from app.api.chat_stream_types import StreamRunContext, StreamRunMetrics
from app.api.chat_tool_events import ToolEventTracker
from app.services.chat_streaming import StreamEventEmitter


def test_chat_schema_models_round_trip():
    request = ChatRequest(message="hello", provider="openai", model="gpt-4o", deep_thinking_enabled=True)
    truncate = TruncateRequest(keep_count=3)
    summary = SummaryGenerateRequest(force=True)

    assert request.message == "hello"
    assert request.provider == "openai"
    assert request.model == "gpt-4o"
    assert request.deep_thinking_enabled is True
    assert truncate.keep_count == 3
    assert summary.force is True


def test_stream_run_types_have_expected_defaults():
    ctx = StreamRunContext(
        chat_id="chat-1",
        request=MagicMock(),
        history=[],
        validated_images=[],
        feature_flags={},
        run_id="run-1",
        assistant_turn_id="turn-1",
        event_v2_enabled=True,
        turn_binding_enabled=True,
        reasoning_display_gated_enabled=True,
        provider="openai",
        model_name="gpt-4o",
        system_prompt="system",
    )
    metrics = StreamRunMetrics()

    assert ctx.stream_state.full_response == ""
    assert ctx.tool_event_queue.empty()
    assert ctx.model_settings == {}
    assert ctx.result is None
    assert metrics.prompt_tokens == 0
    assert metrics.completion_tokens == 0
    assert metrics.total_tokens == 0
    assert metrics.supports_reasoning is False
    assert metrics.reasoning_enabled is False


def test_chat_helpers_preserve_expected_behavior():
    enabled, reason = resolve_reasoning_state(
        supports_reasoning=False,
        deep_thinking_enabled=True,
        reasoning_display_gated_enabled=True,
    )
    assert enabled is False
    assert reason == "MODEL_CAPABILITY_MISSING"

    legacy_enabled, legacy_reason = resolve_reasoning_state(
        supports_reasoning=False,
        deep_thinking_enabled=False,
        reasoning_display_gated_enabled=False,
    )
    assert legacy_enabled is False
    assert legacy_reason == "LEGACY_DISABLED"

    payload = build_runtime_meta_payload(
        provider="openai",
        model_name="gpt-4o",
        tool_names=["docs_search"],
        chat_id="chat-1",
        agent_id="agent-1",
        run_id="run-1",
        assistant_turn_id="turn-1",
        turn_binding_enabled=True,
        supports_reasoning=True,
        deep_thinking_enabled=True,
        reasoning_enabled=True,
        reasoning_disabled_reason_code=None,
        supports_vision=True,
        vision_enabled=True,
        validated_images=["/files/x.png"],
        fallback_mode="native",
    )
    assert payload["meta"]["provider"] == "openai"
    assert payload["meta"]["image_count"] == 1
    assert payload["meta"]["assistant_turn_id"] == "turn-1"

    serialized = serialize_sse_payload({"content": "ok"})
    assert serialized.startswith("data: ")
    assert "content" in serialized
    assert iso_utc_now().endswith("Z")


def test_tool_event_tracker_persists_started_and_finished_events():
    async def run_test():
        emitter = StreamEventEmitter(
            event_v2_enabled=True,
            run_id="run-1",
            assistant_turn_id="turn-1",
            serialize_payload=lambda payload: payload,
            iso_utc_now=lambda: "2026-03-22T00:00:00Z",
        )
        tool_event_queue = asyncio.Queue()
        chat_service = MagicMock()
        tracker = ToolEventTracker(
            chat_id="chat-1",
            assistant_turn_id="turn-1",
            run_id="run-1",
            turn_binding_enabled=True,
            emitter=emitter,
            tool_event_queue=tool_event_queue,
            chat_service=chat_service,
            normalize_finished_ts=lambda ts: ts,
        )

        await tracker.on_tool_event({
            "event": "tool.call.started",
            "call_id": "call-1",
            "tool_name": "docs_search",
            "args": {"q": "hello"},
        })
        await tracker.on_tool_event({
            "event": "tool.call.finished",
            "call_id": "call-1",
            "result": {"ok": True},
            "duration_ms": 12,
        })

        assert tracker.counts == {"started": 1, "finished": 1}
        assert tool_event_queue.qsize() == 2
        chat_service.add_tool_call.assert_called_once()
        chat_service.update_tool_call.assert_called_once()

    asyncio.run(run_test())
