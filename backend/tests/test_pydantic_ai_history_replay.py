import asyncio
from unittest.mock import MagicMock
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessagesTypeAdapter

from app.main import app
from app.mcp.manager import McpManager
from app.services.chat_service import Message
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


def test_v1_persisted_history_replays_through_chat_execution_boundary():
    previous_chat = MagicMock()
    previous_chat.messages = [
        Message(
            role="user",
            content="Find the document",
            images=["data:image/png;base64,AA=="],
        ),
        Message(
            role="assistant",
            content="I found the migration document.",
            tool_calls=[
                {
                    "tool_name": "docs_search",
                    "args": {"query": "migration"},
                    "call_id": "call-1",
                    "result": "matching document",
                    "status": "success",
                }
            ],
        ),
    ]

    class ReplayStreamResult:
        def __init__(self, text):
            self._text = text

        async def stream_text(self):
            yield self._text

    class ReplayRunContext:
        def __init__(self, result):
            self._result = result

        async def __aenter__(self):
            return self._result

        async def __aexit__(self, *_args):
            return None

    class ReplayAgent:
        def __init__(self, *_args, **_kwargs):
            pass

        def run_stream(self, _user_input, **kwargs):
            serialized = ModelMessagesTypeAdapter.dump_json(kwargs["message_history"])
            required_fragments = (
                b"Find the document",
                b"image-url",
                b"docs_search",
                b"call-1",
                b"matching document",
                b"I found the migration document.",
            )
            replayed = all(fragment in serialized for fragment in required_fragments)
            text = "history replayed" if replayed else "history incomplete"
            return ReplayRunContext(ReplayStreamResult(text))

    chat_service = MagicMock()
    chat_service.get_chat.return_value = previous_chat
    tool_registry = MagicMock()
    tool_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

    with (
        patch("app.api.chat.chat_service", chat_service),
        patch("app.api.chat_stream_deps.chat_service", chat_service),
        patch("app.api.chat_stream_deps.agent_store") as agent_store,
        patch("app.api.chat_stream_deps.tool_registry", tool_registry),
        patch("app.api.chat_stream_deps.get_model", return_value=object()),
        patch("app.api.chat_stream_deps.Agent", ReplayAgent),
    ):
        agent_store.get_agent.return_value = None
        response = TestClient(app).post(
            "/api/chat/stream",
            json={"chat_id": "legacy-chat", "message": "Continue"},
        )

    assert response.status_code == 200
    assert "history replayed" in response.text


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


@pytest.mark.asyncio
async def test_repeated_streaming_and_mcp_cycles_leave_no_unfinished_runtime_work():
    current_task = asyncio.current_task()
    baseline_tasks = {
        task for task in asyncio.all_tasks()
        if task is not current_task and not task.done()
    }

    McpManager._instance = None
    manager = McpManager()
    transport = MagicMock()
    transport.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
    transport.__aexit__ = AsyncMock(return_value=None)
    session = AsyncMock()
    session.is_closed = False
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.mcp.manager.stdio_client", return_value=transport),
        patch("app.mcp.manager.ClientSession", return_value=session_context),
    ):
        for cycle in range(20):
            async def text_stream():
                yield f"chunk-{cycle}"

            result = MagicMock()
            result.stream_text.return_value = text_stream()
            parser = MagicMock()
            parser.parse_chunk.side_effect = lambda chunk: [{"content": chunk}]
            queue = asyncio.Queue()
            await queue.put({"event": "tool.call.finished", "cycle": cycle})
            emitter = StreamEventEmitter(
                event_v2_enabled=False,
                run_id=f"run-{cycle}",
                assistant_turn_id=f"turn-{cycle}",
                serialize_payload=lambda payload: payload,
                iso_utc_now=lambda: "2026-01-01T00:00:00Z",
            )

            payloads = [
                payload async for payload in stream_result_chunks(
                    result=result,
                    parser=parser,
                    tool_event_queue=queue,
                    emitter=emitter,
                    stream_state=StreamState(),
                    serialize_payload=lambda payload: payload,
                    logger=MagicMock(),
                    log_label="sustained release validation",
                )
            ]
            assert any(payload.get("cycle") == cycle for payload in payloads)
            await asyncio.wait_for(queue.join(), timeout=0.1)

            connected = await manager.connect_to_server(
                {
                    "name": f"server-{cycle}",
                    "transport": "stdio",
                    "command": "node",
                    "args": [],
                }
            )
            assert connected is session
            await manager.cleanup()
            assert manager.sessions == {}
            assert manager.server_info == {}

    leaked_tasks = [
        task for task in asyncio.all_tasks()
        if task is not current_task and task not in baseline_tasks and not task.done()
    ]
    assert leaked_tasks == []
