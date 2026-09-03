import asyncio
from unittest.mock import MagicMock

import pytest
from pydantic_ai.messages import ModelMessagesTypeAdapter

from app.services.chat_streaming import StreamEventEmitter, StreamState, stream_result_chunks


V1_HISTORY_FIXTURE = """[
  {"parts":[{"content":["Find the document",{"url":"data:image/png;base64,AA==","kind":"image-url"}],"part_kind":"user-prompt"}],"kind":"request"},
  {"parts":[{"tool_name":"docs_search","args":{"query":"migration"},"tool_call_id":"call-1","part_kind":"tool-call"}],"kind":"response"},
  {"parts":[{"tool_name":"docs_search","content":"matching document","tool_call_id":"call-1","part_kind":"tool-return"}],"kind":"request"},
  {"parts":[{"content":"I found the migration document.","part_kind":"text"}],"kind":"response"}
]"""


def test_serialized_history_replays_text_tool_and_multimodal_parts():
    """Keep the framework-history format isolated from Yue's persisted records."""
    restored = ModelMessagesTypeAdapter.validate_json(V1_HISTORY_FIXTURE)

    assert len(restored) == 4
    assert restored[0].parts[0].content[0] == "Find the document"
    assert restored[1].parts[0].tool_call_id == "call-1"
    assert restored[2].parts[0].tool_call_id == "call-1"
    assert restored[3].parts[0].content == "I found the migration document."


@pytest.mark.asyncio
async def test_streaming_drains_queued_tool_event_after_text_completion():
    async def text_stream():
        yield "hello"

    result = MagicMock()
    result.stream_text.return_value = text_stream()
    parser = MagicMock()
    parser.parse_chunk.return_value = [{"content": "hello"}]
    queue = asyncio.Queue()
    await queue.put({"event": "tool.call.finished", "tool_name": "docs_search"})
    emitter = StreamEventEmitter(
        event_v2_enabled=False,
        run_id="run-1",
        assistant_turn_id="turn-1",
        serialize_payload=lambda payload: payload,
        iso_utc_now=lambda: "2026-01-01T00:00:00Z",
    )
    state = StreamState()

    payloads = [
        payload async for payload in stream_result_chunks(
            result=result, parser=parser, tool_event_queue=queue, emitter=emitter,
            stream_state=state, serialize_payload=lambda payload: payload,
            logger=MagicMock(), log_label="test stream",
        )
    ]

    assert payloads == [{"content": "hello"}, {"event": "tool.call.finished", "tool_name": "docs_search"}]
    assert state.full_response == "hello"
    assert queue.empty()


@pytest.mark.asyncio
async def test_streaming_error_drains_queued_tool_event_and_cleans_up():
    async def failing_stream():
        raise RuntimeError("provider disconnected")
        yield "unreachable"

    result = MagicMock()
    result.stream_text.return_value = failing_stream()
    queue = asyncio.Queue()
    await queue.put({"event": "tool.call.finished", "tool_name": "docs_search"})
    logger = MagicMock()
    emitter = StreamEventEmitter(
        event_v2_enabled=False,
        run_id="run-1",
        assistant_turn_id="turn-1",
        serialize_payload=lambda payload: payload,
        iso_utc_now=lambda: "2026-01-01T00:00:00Z",
    )

    payloads = [
        payload async for payload in stream_result_chunks(
            result=result, parser=MagicMock(), tool_event_queue=queue, emitter=emitter,
            stream_state=StreamState(), serialize_payload=lambda payload: payload,
            logger=logger, log_label="test stream",
        )
    ]

    assert payloads == [{"event": "tool.call.finished", "tool_name": "docs_search"}]
    assert queue.empty()
    logger.exception.assert_called_once()
