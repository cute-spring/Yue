import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.function import FunctionModel

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


async def _stream_history_replay_verdict(messages, _info):
    serialized = ModelMessagesTypeAdapter.dump_json(messages)
    required_fragments = (
        b"Find the document",
        b"image-url",
        b"docs_search",
        b"call-1",
        b"matching document",
        b"I found the migration document.",
    )
    replayed = all(fragment in serialized for fragment in required_fragments)
    yield "history replayed" if replayed else "history incomplete"


@pytest.mark.asyncio
async def test_v1_serialized_history_replays_through_v2_agent():
    restored = ModelMessagesTypeAdapter.validate_json(V1_HISTORY_FIXTURE)
    agent = Agent(FunctionModel(stream_function=_stream_history_replay_verdict))

    async with agent.run_stream("Continue", message_history=restored) as result:
        output = "".join([chunk async for chunk in result.stream_text()])

    assert output == "history replayed"


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

    chat_service = MagicMock()
    chat_service.get_chat.return_value = previous_chat
    tool_registry = MagicMock()
    tool_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

    with (
        patch("app.api.chat.chat_service", chat_service),
        patch("app.api.chat_stream_deps.chat_service", chat_service),
        patch("app.api.chat_stream_deps.agent_store") as agent_store,
        patch("app.api.chat_stream_deps.tool_registry", tool_registry),
        patch(
            "app.api.chat_stream_deps.get_model",
            return_value=FunctionModel(stream_function=_stream_history_replay_verdict),
        ),
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
    manager.last_errors["server-0"] = "previous connection failure"
    transport_contexts = []
    http_client_contexts = []
    session_contexts = []

    def context_with(value, collection):
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=value)
        context.__aexit__ = AsyncMock(return_value=None)
        collection.append(context)
        return context

    def stdio_transport(*_args, **_kwargs):
        return context_with((AsyncMock(), AsyncMock()), transport_contexts)

    def http_client(*_args, **_kwargs):
        return context_with(AsyncMock(), http_client_contexts)

    def http_transport(*_args, **_kwargs):
        return context_with(
            (AsyncMock(), AsyncMock(), lambda: "session-id"),
            transport_contexts,
        )

    def client_session(*_args, **_kwargs):
        session = AsyncMock()
        session.is_closed = False
        session.initialize.return_value = SimpleNamespace()
        return context_with(session, session_contexts)

    async def run_stream_cycle(cycle):
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
        await asyncio.wait_for(queue.join(), timeout=0.1)
        return payloads, queue

    with (
        patch("app.mcp.manager.stdio_client", side_effect=stdio_transport),
        patch("app.mcp.manager.create_mcp_http_client", side_effect=http_client),
        patch("app.mcp.manager.streamable_http_client", side_effect=http_transport),
        patch("app.mcp.manager.ClientSession", side_effect=client_session),
    ):
        stream_results = await asyncio.gather(*(run_stream_cycle(cycle) for cycle in range(20)))
        for cycle, (payloads, queue) in enumerate(stream_results):
            assert any(payload.get("cycle") == cycle for payload in payloads)
            assert queue.empty()

        configs = [
            {
                "name": f"server-{cycle}",
                "transport": "stdio" if cycle % 2 == 0 else "streamable_http",
                "command": "node" if cycle % 2 == 0 else None,
                "args": [],
                "url": "https://mcp.example.test" if cycle % 2 else None,
            }
            for cycle in range(20)
        ]
        connected_sessions = await asyncio.gather(
            *(manager.connect_to_server(config) for config in configs)
        )
        assert len(connected_sessions) == 20
        assert len(manager.sessions) == 20
        assert manager.last_errors == {}

        await manager.cleanup()

    assert manager.sessions == {}
    assert manager.server_info == {}
    assert all(context.__aexit__.await_count == 1 for context in transport_contexts)
    assert all(context.__aexit__.await_count == 1 for context in http_client_contexts)
    assert all(context.__aexit__.await_count == 1 for context in session_contexts)

    leaked_tasks = [
        task for task in asyncio.all_tasks()
        if task is not current_task and task not in baseline_tasks and not task.done()
    ]
    assert leaked_tasks == []
