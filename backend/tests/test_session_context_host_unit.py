from __future__ import annotations

from datetime import datetime, timedelta
import os
import sqlite3
import shutil
import tempfile
import json
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.chat_service import ChatService, Message, ToolCall
from app.services.memory.session_context_host import (
    YueHostEventAdapter,
    YuePromptContextBridge,
    YueSessionContextResult,
    YueSessionContextService,
    _strengthen_prompt_context_with_authoritative_reference,
    build_session_context_inspection_payload,
    render_exported_prompt_context,
)
from midterm_memory import (
    ContextEvent,
    ContextResolutionAction,
    ContextResolutionConfig,
    ContextResolutionReason,
    ContextRetriever,
    InMemoryBM25Index,
    MemoryChunk,
    PromptContextBlock,
    ResolutionCandidate,
    SessionContextReplayCase,
    SessionContextManager,
    SessionContextPlan,
    export_prompt_context,
)


def _make_temp_chat_service():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_session_context.db")
    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return temp_dir, test_engine, testing_session_local


def _chunk(
    session_id: str,
    chunk_id: str,
    chunk_type: str,
    content: str,
    retrieval_text: str,
    *,
    turn_id: int,
) -> MemoryChunk:
    return MemoryChunk(
        chunk_id=chunk_id,
        session_id=session_id,
        chunk_type=chunk_type,
        content=content,
        retrieval_text=retrieval_text,
        source_event_ids=[f"evt-old-{chunk_id}"],
        start_turn_id=turn_id,
        end_turn_id=turn_id,
        priority=80,
    )


def _manager(memory_chunks: tuple[MemoryChunk, ...] = ()) -> SessionContextManager:
    index = InMemoryBM25Index()
    for chunk in memory_chunks:
        index.add_chunk(chunk)
    return SessionContextManager(context_retriever=ContextRetriever(index=index))


_SESSION_CONTEXT_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "session_context"


def _parse_fixture_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _load_transcript_fixture(name: str) -> dict[str, object]:
    return json.loads((_SESSION_CONTEXT_FIXTURE_DIR / name).read_text())


def _load_memory_chunks_from_fixture(payload: dict[str, object]) -> tuple[MemoryChunk, ...]:
    raw_chunks = payload.get("memory_chunks", [])
    if not isinstance(raw_chunks, list):
        return ()
    return tuple(MemoryChunk.from_dict(item) for item in raw_chunks if isinstance(item, dict))


def _load_config_overrides_from_fixture(payload: dict[str, object]) -> dict[str, object]:
    raw_config = payload.get("config_overrides", {})
    return dict(raw_config) if isinstance(raw_config, dict) else {}


def _host_records_from_transcript_fixture(payload: dict[str, object]) -> tuple[list[object], list[ToolCall]]:
    messages = [
        Message(
            role=str(item["role"]),
            content=str(item["content"]),
            timestamp=_parse_fixture_datetime(item.get("timestamp")),
            assistant_turn_id=item.get("assistant_turn_id"),
            run_id=item.get("run_id"),
        )
        for item in payload.get("messages", [])
    ]
    tool_calls = [
        ToolCall(
            session_id=str(item["session_id"]),
            call_id=str(item["call_id"]),
            tool_name=str(item["tool_name"]),
            assistant_turn_id=item.get("assistant_turn_id"),
            run_id=item.get("run_id"),
            args=item.get("args"),
            result=item.get("result"),
            error=item.get("error"),
            status=item.get("status"),
            started_ts=_parse_fixture_datetime(item.get("started_ts")),
            finished_ts=_parse_fixture_datetime(item.get("finished_ts")),
            created_at=_parse_fixture_datetime(item.get("created_at")),
            finished_at=_parse_fixture_datetime(item.get("finished_at")),
            duration_ms=item.get("duration_ms"),
        )
        for item in payload.get("tool_calls", [])
    ]
    return messages + list(tool_calls), tool_calls


@dataclass(frozen=True)
class YueReferenceReplayCase:
    name: str
    current_input: str
    host_records: tuple[object, ...]
    expected_action: ContextResolutionAction
    expected_reason: ContextResolutionReason
    expected_prompt_blocks: tuple[str, ...] = ()
    expected_selected_source: str | None = None
    expected_selected_content_type: str | None = None
    expected_signal_strength: str | None = None
    expected_should_retrieve: bool = False
    expected_trace_block_name: str | None = None
    memory_chunks: tuple[MemoryChunk, ...] = ()
    config_overrides: dict[str, object] = field(default_factory=dict)


def test_yue_reference_host_event_adapter_maps_messages_and_tools_to_ordered_context_events():
    adapter = YueHostEventAdapter()
    start = datetime(2026, 5, 23, 10, 0, 0)
    user_message = Message(role="user", content="Find the earlier command", timestamp=start)
    assistant_message = Message(
        role="assistant",
        content="I used rg to search the repo.",
        timestamp=start + timedelta(seconds=4),
        assistant_turn_id="turn-1",
        run_id="run-1",
    )
    tool_call = ToolCall(
        session_id="chat-1",
        call_id="call-1",
        tool_name="exec",
        assistant_turn_id="turn-1",
        run_id="run-1",
        args={"cmd": "rg session"},
        result="backend/app/services/chat_service.py",
        status="success",
        started_ts=start + timedelta(seconds=2),
        finished_ts=start + timedelta(seconds=3),
        created_at=start + timedelta(seconds=2),
    )

    events = adapter.build_recent_events(
        session_id="chat-1",
        host_records=[assistant_message, tool_call, user_message],
    )

    assert [event.event_type for event in events] == [
        "user_message",
        "tool_call",
        "tool_result",
        "assistant_message",
    ]
    assert events[1].source == "exec"
    assert events[1].source_ref == "call-1"
    assert events[2].content == "backend/app/services/chat_service.py"
    assert [event.turn_id for event in events] == [1, 2, 2, 2]
    assert events[1].event_type == "tool_call"
    assert events[2].event_type == "tool_result"


def test_yue_reference_host_session_context_service_reaches_manager_resolve_happy_path():
    temp_dir, test_engine, testing_session_local = _make_temp_chat_service()
    try:
        from unittest.mock import patch

        with patch("app.services.chat_service.engine", test_engine), patch(
            "app.services.chat_service.SessionLocal", testing_session_local
        ), patch("app.services.chat_service.DATA_DIR", temp_dir):
            service = ChatService()
            session = service.create_chat(title="Session context test")
            service.add_message(session.id, "user", "We chose option A for the adapter.")
            service.add_message(
                session.id,
                "assistant",
                "Option A keeps the integration thin.",
                assistant_turn_id="turn-1",
                run_id="run-1",
            )
            service.add_tool_call(
                session.id,
                call_id="call-1",
                tool_name="exec",
                args={"cmd": "rg adapter"},
                assistant_turn_id="turn-1",
                run_id="run-1",
            )
            service.update_tool_call(
                "call-1",
                status="success",
                result="adapter found in backend/app/services/memory/session_context_host.py",
            )
            service.add_message(session.id, "user", "What did we choose earlier?")

            manager = MagicMock(wraps=SessionContextManager())
            host_service = YueSessionContextService(manager=manager)
            result = host_service.build_prompt_context(
                session_id=session.id,
                current_input="What did we choose earlier?",
                chat_session=service.get_chat(session.id),
                tool_calls=service.get_tool_calls(session.id),
            )

            assert result is not None
            assert manager.resolve.call_count == 1
            assert result.prompt_context.rendered_prompt_block.startswith("### Session Context")
            assert "recent_conversation" in result.prompt_context.rendered_prompt_block
            assert result.plan.telemetry["action"] in {
                "use_recent_context",
                "use_recent_artifact",
                "retrieve_mid_session_memory",
                "no_context_needed",
            }
    finally:
        test_engine.dispose()
        shutil.rmtree(temp_dir)


def test_yue_reference_host_render_preserves_candidate_and_chunk_traceability():
    exported_context = export_prompt_context(
        [
            PromptContextBlock(
                name="mid_term_tool_results",
                content="adapter found in backend/app/services/memory/session_context_host.py",
                priority=90,
                token_count=8,
                source_chunk_ids=["chunk-1"],
            )
        ],
        selected_candidates=[
            ResolutionCandidate(
                candidate_id="cand-1",
                session_id="chat-1",
                source="mid_session_memory",
                content_type="tool_result",
                summary="adapter file location",
                content="adapter found in backend/app/services/memory/session_context_host.py",
                score=0.92,
                metadata={"chunk_id": "chunk-1"},
            )
        ],
        rendered_text="rendered",
    )
    bridge = render_exported_prompt_context(exported_context)

    assert bridge.selected_candidate_ids == ["cand-1"]
    assert bridge.source_chunk_ids == ["chunk-1"]
    assert bridge.block_names == ["mid_term_tool_results"]
    assert bridge.sections == ["mid_session_memory"]
    assert "mid_session_memory:mid_term_tool_results" in bridge.rendered_prompt_block
    assert "trace.selected_candidate_ids=cand-1" in bridge.rendered_prompt_block
    assert "trace.source_chunk_ids=chunk-1" in bridge.rendered_prompt_block
    assert "session_trace.selected_candidate_ids=cand-1" in bridge.rendered_prompt_block
    assert "session_trace.source_chunk_ids=chunk-1" in bridge.rendered_prompt_block
    assert "session_trace.sections=mid_session_memory" in bridge.rendered_prompt_block


def test_yue_reference_host_strengthens_numbered_option_reference_in_prompt_block():
    prompt_context = YuePromptContextBridge(
        exported_context=export_prompt_context([], selected_candidates=[], rendered_text="rendered"),
        rendered_prompt_block="### Session Context\n[mid_session_memory:mid_term_conversation_memory]\n方案B 是 Postgres + pgvector",
        selected_candidate_ids=["cand-2"],
        source_chunk_ids=["chunk-2"],
        block_names=["mid_term_conversation_memory"],
        sections=["mid_session_memory"],
    )
    plan = MagicMock(
        selected_candidates=[
            ResolutionCandidate(
                candidate_id="cand-2",
                session_id="chat-1",
                source="mid_session_memory",
                content_type="numbered_option",
                summary="方案B 是 Postgres + pgvector",
                content="方案B 是 Postgres + pgvector",
                score=0.98,
                metadata={"ordinal": 2},
            )
        ]
    )

    strengthened = _strengthen_prompt_context_with_authoritative_reference(prompt_context, plan)

    assert "resolver.authoritative_reference=numbered_option" in strengthened.rendered_prompt_block
    assert "resolver.selected_ordinal=2" in strengthened.rendered_prompt_block
    assert "resolver.selected_option_content=方案B 是 Postgres + pgvector" in strengthened.rendered_prompt_block


def test_yue_reference_host_builds_minimal_inspection_payload_contract():
    recent_events = [
        ContextEvent(
            event_id="message:chat-1:1:user_message",
            session_id="chat-1",
            turn_id=1,
            event_type="user_message",
            content="What did we choose earlier?",
        ),
        ContextEvent(
            event_id="tool_call:chat-1:call-1",
            session_id="chat-1",
            turn_id=2,
            event_type="tool_call",
            content="exec args={\"cmd\": \"rg adapter\"}",
            source="exec",
            source_ref="call-1",
        ),
        ContextEvent(
            event_id="tool_result:chat-1:call-1",
            session_id="chat-1",
            turn_id=2,
            event_type="tool_result",
            content="adapter found in backend/app/services/memory/session_context_host.py",
            source="exec",
            source_ref="call-1",
        ),
        ContextEvent(
            event_id="message:chat-1:2:assistant_message",
            session_id="chat-1",
            turn_id=2,
            event_type="assistant_message",
            content="Option A keeps the integration thin.",
            source_ref="turn-1",
        ),
    ]
    prompt_context = YuePromptContextBridge(
        exported_context=export_prompt_context(
            [
                PromptContextBlock(
                    name="recent_conversation",
                    content="Earlier we chose option A.",
                    priority=80,
                    token_count=6,
                    source_chunk_ids=[],
                )
            ],
            selected_candidates=[
                ResolutionCandidate(
                    candidate_id="cand-1",
                    session_id="chat-1",
                    source="recent_artifact",
                    content_type="decision",
                    summary="option A decision",
                    content="Earlier we chose option A.",
                    score=0.88,
                    metadata={},
                )
            ],
            rendered_text="rendered",
        ),
        rendered_prompt_block="### Session Context\n[recent_context:recent_conversation]\nEarlier we chose option A.",
        selected_candidate_ids=["cand-1"],
        source_chunk_ids=["chunk-1"],
        block_names=["recent_conversation"],
        sections=["recent_context"],
    )
    plan = MagicMock(
        telemetry={
            "action": "use_recent_artifact",
            "reason": "continuation_reference",
            "should_retrieve": False,
            "reference_signal_strength": "explicit",
            "matched_signals": ["刚才"],
        }
    )

    inspection = build_session_context_inspection_payload(
        session_id="chat-1",
        recent_events=recent_events,
        plan=plan,
        prompt_context=prompt_context,
    )

    assert inspection == {
        "session_id": "chat-1",
        "host": "yue",
        "recent_event_count": 4,
        "recent_event_types": [
            "user_message",
            "tool_call",
            "tool_result",
            "assistant_message",
        ],
        "event_counts": {
            "user_message": 1,
            "assistant_message": 1,
            "tool_call": 1,
            "tool_result": 1,
        },
        "action": "use_recent_artifact",
        "reason": "continuation_reference",
        "should_retrieve": False,
        "reference_signal_strength": "explicit",
        "matched_signals": ["刚才"],
        "selected_candidate_ids": ["cand-1"],
        "source_chunk_ids": ["chunk-1"],
        "block_names": ["recent_conversation"],
        "sections": ["recent_context"],
        "telemetry": {
            "action": "use_recent_artifact",
            "reason": "continuation_reference",
            "should_retrieve": False,
            "reference_signal_strength": "explicit",
            "matched_signals": ["刚才"],
        },
    }


def test_yue_reference_host_service_keeps_mid_session_boundary_and_host_metadata():
    manager = MagicMock(spec=SessionContextManager)
    manager.resolve.return_value = MagicMock(spec=SessionContextPlan, telemetry={"action": "no_context_needed"})
    manager.export_prompt_context.return_value = export_prompt_context(
        [
            PromptContextBlock(
                name="recent_conversation",
                content="Earlier we chose option A.",
                priority=80,
                token_count=6,
                source_chunk_ids=[],
            )
        ],
        selected_candidates=[],
        rendered_text="rendered",
    )
    service = YueSessionContextService(manager=manager)

    result = service.build_prompt_context(
        session_id="chat-1",
        current_input="What did we choose earlier?",
        chat_session=MagicMock(messages=[Message(role="user", content="Earlier we chose option A.", timestamp=datetime(2026, 5, 23, 10, 0, 0))]),
        tool_calls=[],
    )

    assert isinstance(result, YueSessionContextResult)
    manager.resolve.assert_called_once()
    assert result.inspection["host"] == "yue"
    assert result.inspection["action"] == "no_context_needed"
    assert result.inspection["recent_event_count"] == 1
    assert result.inspection["event_counts"]["user_message"] == 1
    resolve_kwargs = manager.resolve.call_args.kwargs
    assert isinstance(resolve_kwargs["config"], ContextResolutionConfig)
    assert resolve_kwargs["config"].metadata == {"host": "yue"}
    assert resolve_kwargs["config"].boundary_policy.allow_mid_session_retrieval is True
    assert resolve_kwargs["config"].boundary_policy.allow_cross_session_retrieval is False
    assert resolve_kwargs["config"].boundary_policy.allow_external_knowledge_retrieval is False


def test_yue_reference_host_service_materializes_live_chunks_for_mid_session_retrieval(monkeypatch):
    payload = _load_transcript_fixture("reviewed_traffic_deepseek_small_window_second_plan_recovery.json")
    session_id = str(payload["chat_id"])
    current_input = str(payload["current_input"])
    messages, tool_calls = _host_records_from_transcript_fixture(payload)
    chat_messages = [record for record in messages if isinstance(record, Message)]

    temp_dir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(temp_dir, "session_context_memory.db")
        monkeypatch.setenv("YUE_SESSION_CONTEXT_DB_PATH", db_path)
        monkeypatch.setenv("YUE_SESSION_CONTEXT_RECENT_WINDOW_TOKEN_BUDGET", "120")
        monkeypatch.setenv("YUE_SESSION_CONTEXT_RETRIEVAL_TOKEN_BUDGET", "120")
        monkeypatch.setenv("YUE_SESSION_CONTEXT_TOP_K", "3")

        service = YueSessionContextService()
        result = service.build_prompt_context(
            session_id=session_id,
            current_input=current_input,
            chat_session=MagicMock(messages=chat_messages),
            tool_calls=tool_calls,
        )

        assert result is not None
        assert result.plan.telemetry["action"] == "retrieve_mid_session_memory"
        assert result.plan.telemetry["retrieved_chunk_count"] >= 1
        assert result.inspection["materialized_chunk_count"] >= 1
        assert result.inspection["session_context_db_path"] == db_path
        assert "Postgres + pgvector" in result.prompt_context.rendered_prompt_block

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "select count(*) from session_memory_chunks where session_id = ?",
                (session_id,),
            ).fetchone()
        assert row is not None
        assert int(row[0]) >= 1
    finally:
        shutil.rmtree(temp_dir)


YUE_REFERENCE_REPLAY_CASES = (
    YueReferenceReplayCase(
        name="ordinal_reference_after_numbered_options",
        current_input="刚才第二个方案继续展开一下",
        host_records=(
            Message(role="user", content="给我三个持久化方案", timestamp=datetime(2026, 5, 23, 10, 0, 0)),
            Message(
                role="assistant",
                content="方案一 Redis，方案二 SQLite 持久化，方案三 对象存储。",
                timestamp=datetime(2026, 5, 23, 10, 0, 4),
                assistant_turn_id="turn-1",
            ),
            Message(role="user", content="先说一下迁移成本", timestamp=datetime(2026, 5, 23, 10, 0, 8)),
            Message(
                role="assistant",
                content="Redis 迁移最轻，SQLite 次之。",
                timestamp=datetime(2026, 5, 23, 10, 0, 12),
                assistant_turn_id="turn-2",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.ORDINAL_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="numbered_option",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="recent_tool_followup_after_assistant_commentary",
        current_input="这个用户有什么权限？",
        host_records=(
            Message(role="user", content="查一下 Alice 的权限", timestamp=datetime(2026, 5, 23, 10, 1, 0)),
            ToolCall(
                session_id="chat-replay",
                call_id="call-roles",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-roles",
                status="success",
                result="Alice has Teams Communications Administrator",
                started_ts=datetime(2026, 5, 23, 10, 1, 1),
                finished_ts=datetime(2026, 5, 23, 10, 1, 2),
                created_at=datetime(2026, 5, 23, 10, 1, 1),
            ),
            Message(
                role="assistant",
                content="我查到了，下面是结果摘要。",
                timestamp=datetime(2026, 5, 23, 10, 1, 4),
                assistant_turn_id="turn-roles",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.TOOL_RESULT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="tool_result",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="mid_session_document_reference_after_topic_shift",
        current_input="刚才那个 runbook 链接再发我一下",
        host_records=(
            Message(
                role="assistant",
                content="我们先看另外一个问题。",
                timestamp=datetime(2026, 5, 23, 10, 2, 0),
                assistant_turn_id="turn-10",
            ),
            Message(role="user", content="那 PostgreSQL 呢？", timestamp=datetime(2026, 5, 23, 10, 2, 4)),
            Message(
                role="assistant",
                content="PostgreSQL 默认端口是 5432。",
                timestamp=datetime(2026, 5, 23, 10, 2, 8),
                assistant_turn_id="turn-11",
            ),
        ),
        memory_chunks=(
            _chunk(
                "chat-replay",
                "chunk-runbook",
                "document_reference",
                "https://example.com/runbook.md",
                "deployment runbook link",
                turn_id=3,
            ),
        ),
        expected_action=ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY,
        expected_reason=ContextResolutionReason.RECENT_CONTEXT_INSUFFICIENT,
        expected_prompt_blocks=("mid_term_conversation_memory",),
        expected_selected_source="mid_session_memory",
        expected_selected_content_type="document_reference",
        expected_should_retrieve=True,
        expected_signal_strength="explicit",
        expected_trace_block_name="mid_term_conversation_memory",
    ),
    YueReferenceReplayCase(
        name="standalone_new_request_after_dense_history",
        current_input="写一个新的 Python 函数解析 YAML",
        host_records=(
            Message(
                role="assistant",
                content="python export.py --user Bob --format csv",
                timestamp=datetime(2026, 5, 23, 10, 3, 0),
                assistant_turn_id="turn-20",
            ),
            ToolCall(
                session_id="chat-replay",
                call_id="call-noise",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-21",
                status="success",
                result="Alice has Teams Communications Administrator",
                started_ts=datetime(2026, 5, 23, 10, 3, 1),
                finished_ts=datetime(2026, 5, 23, 10, 3, 2),
                created_at=datetime(2026, 5, 23, 10, 3, 1),
            ),
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 3, 4),
                assistant_turn_id="turn-22",
            ),
        ),
        memory_chunks=(
            _chunk(
                "chat-replay",
                "chunk-noise",
                "command",
                "python export.py --all-users --format csv",
                "batch export command",
                turn_id=10,
            ),
        ),
        expected_action=ContextResolutionAction.NO_CONTEXT_NEEDED,
        expected_reason=ContextResolutionReason.NO_REFERENCE_SIGNAL,
        expected_signal_strength="none",
    ),
    YueReferenceReplayCase(
        name="ambiguity_same_action_requires_clarification",
        current_input="也这样做",
        host_records=(
            Message(
                role="assistant",
                content="python export.py --user Bob --format csv",
                timestamp=datetime(2026, 5, 23, 10, 4, 0),
                assistant_turn_id="turn-30",
            ),
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 4, 3),
                assistant_turn_id="turn-31",
            ),
            Message(
                role="assistant",
                content="如果你要的话我也可以再给 SQL 版本。",
                timestamp=datetime(2026, 5, 23, 10, 4, 6),
                assistant_turn_id="turn-32",
            ),
        ),
        config_overrides={
            "enable_semantic_adjudication": True,
            "prefer_recall_when_uncertain": False,
        },
        expected_action=ContextResolutionAction.ASK_CLARIFYING_QUESTION,
        expected_reason=ContextResolutionReason.MULTIPLE_CANDIDATES,
        expected_signal_strength="implicit_strong",
    ),
    YueReferenceReplayCase(
        name="recent_document_reference_without_retrieval",
        current_input="用那个文档里的约定",
        host_records=(
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 5, 0),
                assistant_turn_id="turn-50",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.DOCUMENT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="document_reference",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="recent_decision_continuation_reference",
        current_input="继续按刚才定的方案",
        host_records=(
            Message(
                role="assistant",
                content="结论：采用 SQLite 持久化并保留 Redis 热缓存。",
                timestamp=datetime(2026, 5, 23, 10, 6, 0),
                assistant_turn_id="turn-51",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.CONTINUATION_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="decision",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="explicit_deictic_command_carryover",
        current_input="这个也导出成 CSV",
        host_records=(
            Message(
                role="assistant",
                content="Get-EXOMailbox -Identity Alice | Export-Csv mailbox.csv",
                timestamp=datetime(2026, 5, 23, 10, 7, 0),
                assistant_turn_id="turn-52",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.CODE_OR_COMMAND_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="code_block",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="implicit_entity_lookup_after_tool_result",
        current_input="Bob 也查一下",
        host_records=(
            Message(role="user", content="查一下 Alice 的权限", timestamp=datetime(2026, 5, 23, 10, 8, 0)),
            ToolCall(
                session_id="chat-replay",
                call_id="call-lookup",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-53",
                status="success",
                result="Alice has Teams Communications Administrator",
                started_ts=datetime(2026, 5, 23, 10, 8, 1),
                finished_ts=datetime(2026, 5, 23, 10, 8, 2),
                created_at=datetime(2026, 5, 23, 10, 8, 1),
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.TOOL_RESULT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="tool_result",
        expected_signal_strength="implicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="implicit_format_followup_recent_artifact",
        current_input="CSV 版本",
        host_records=(
            Message(
                role="assistant",
                content="Get-EXOMailbox -Identity Alice | Export-Csv mailbox.csv",
                timestamp=datetime(2026, 5, 23, 10, 9, 0),
                assistant_turn_id="turn-54",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.CODE_OR_COMMAND_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="code_block",
        expected_signal_strength="implicit_strong",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="long_topic_shift_recovers_older_runbook_link",
        current_input="把刚才那个 runbook link 再贴一下",
        host_records=(
            Message(
                role="assistant",
                content="先看一下这次发布窗口。",
                timestamp=datetime(2026, 5, 23, 10, 10, 0),
                assistant_turn_id="turn-60",
            ),
            Message(role="user", content="数据库切换会影响多大？", timestamp=datetime(2026, 5, 23, 10, 10, 4)),
            Message(
                role="assistant",
                content="会有短暂只读窗口，但不需要全站停机。",
                timestamp=datetime(2026, 5, 23, 10, 10, 8),
                assistant_turn_id="turn-61",
            ),
            Message(role="user", content="回滚预案呢？", timestamp=datetime(2026, 5, 23, 10, 10, 12)),
            Message(
                role="assistant",
                content="回滚预案会先恢复旧连接串，再回放增量写入。",
                timestamp=datetime(2026, 5, 23, 10, 10, 16),
                assistant_turn_id="turn-62",
            ),
        ),
        memory_chunks=(
            _chunk(
                "chat-replay",
                "chunk-runbook-long",
                "document_reference",
                "https://example.com/release-runbook.md",
                "release runbook link rollback steps",
                turn_id=2,
            ),
        ),
        expected_action=ContextResolutionAction.RETRIEVE_MID_SESSION_MEMORY,
        expected_reason=ContextResolutionReason.RECENT_CONTEXT_INSUFFICIENT,
        expected_prompt_blocks=("mid_term_conversation_memory",),
        expected_selected_source="mid_session_memory",
        expected_selected_content_type="document_reference",
        expected_should_retrieve=True,
        expected_signal_strength="explicit",
        expected_trace_block_name="mid_term_conversation_memory",
    ),
    YueReferenceReplayCase(
        name="mixed_language_document_reference_stays_recent_artifact",
        current_input="按那个 doc 里的 naming convention 来",
        host_records=(
            Message(
                role="assistant",
                content="Spec 在 docs/specs/api_naming_convention.md，里面约定了 endpoint 和 field naming。",
                timestamp=datetime(2026, 5, 23, 10, 11, 0),
                assistant_turn_id="turn-63",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.DOCUMENT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="document_reference",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="multiple_tool_results_recent_followup_prefers_recent_artifact",
        current_input="那 Bob 呢？",
        host_records=(
            Message(role="user", content="先查 Alice 和 Bob 的权限", timestamp=datetime(2026, 5, 23, 10, 12, 0)),
            ToolCall(
                session_id="chat-replay",
                call_id="call-alice",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-64",
                status="success",
                result="Alice has Teams Communications Administrator",
                started_ts=datetime(2026, 5, 23, 10, 12, 1),
                finished_ts=datetime(2026, 5, 23, 10, 12, 2),
                created_at=datetime(2026, 5, 23, 10, 12, 1),
            ),
            ToolCall(
                session_id="chat-replay",
                call_id="call-bob",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-64",
                status="success",
                result="Bob has Exchange Administrator",
                started_ts=datetime(2026, 5, 23, 10, 12, 3),
                finished_ts=datetime(2026, 5, 23, 10, 12, 4),
                created_at=datetime(2026, 5, 23, 10, 12, 3),
            ),
            Message(
                role="assistant",
                content="我查到了两个人的权限，先给你摘要。",
                timestamp=datetime(2026, 5, 23, 10, 12, 6),
                assistant_turn_id="turn-64",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.TOOL_RESULT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="tool_result",
        expected_signal_strength="implicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="implicit_same_way_followup_after_recent_command_example",
        current_input="按同样方式处理 Alice",
        host_records=(
            Message(role="user", content="把 Bob 导出成 CSV", timestamp=datetime(2026, 5, 23, 10, 12, 40)),
            Message(
                role="assistant",
                content="python export.py --user Bob --format csv",
                timestamp=datetime(2026, 5, 23, 10, 12, 44),
                assistant_turn_id="turn-64b",
            ),
            Message(
                role="assistant",
                content="你也可以改成 JSON。",
                timestamp=datetime(2026, 5, 23, 10, 12, 48),
                assistant_turn_id="turn-64c",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.CODE_OR_COMMAND_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="code_block",
        expected_signal_strength="implicit_strong",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="implicit_batch_version_followup_after_recent_command_example",
        current_input="批量版本呢？",
        host_records=(
            Message(
                role="assistant",
                content="python export.py --user Bob --format csv",
                timestamp=datetime(2026, 5, 23, 10, 12, 52),
                assistant_turn_id="turn-64d",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.CODE_OR_COMMAND_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="code_block",
        expected_signal_strength="implicit_strong",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="direct_tool_result_reference_without_assistant_commentary",
        current_input="这个用户有什么权限？",
        host_records=(
            Message(role="user", content="查一下 Alice 的权限", timestamp=datetime(2026, 5, 23, 10, 12, 56)),
            ToolCall(
                session_id="chat-replay",
                call_id="call-direct-roles",
                tool_name="microsoft_graph",
                assistant_turn_id="turn-64e",
                status="success",
                result="Alice has Teams Communications Administrator",
                started_ts=datetime(2026, 5, 23, 10, 12, 57),
                finished_ts=datetime(2026, 5, 23, 10, 12, 58),
                created_at=datetime(2026, 5, 23, 10, 12, 57),
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.TOOL_RESULT_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="tool_result",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
    YueReferenceReplayCase(
        name="short_followup_standalone_negative_after_dense_context",
        current_input="另外写个 pytest fixture",
        host_records=(
            Message(
                role="assistant",
                content="Get-EXOMailbox -Identity Alice | Export-Csv mailbox.csv",
                timestamp=datetime(2026, 5, 23, 10, 13, 0),
                assistant_turn_id="turn-65",
            ),
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 13, 3),
                assistant_turn_id="turn-66",
            ),
            ToolCall(
                session_id="chat-replay",
                call_id="call-dense",
                tool_name="exec",
                assistant_turn_id="turn-67",
                status="success",
                result="backend/app/services/memory/session_context_host.py",
                started_ts=datetime(2026, 5, 23, 10, 13, 4),
                finished_ts=datetime(2026, 5, 23, 10, 13, 5),
                created_at=datetime(2026, 5, 23, 10, 13, 4),
            ),
        ),
        memory_chunks=(
            _chunk(
                "chat-replay",
                "chunk-dense-negative",
                "tool_result",
                "backend/app/services/memory/session_context_host.py",
                "session context host file path",
                turn_id=8,
            ),
        ),
        expected_action=ContextResolutionAction.NO_CONTEXT_NEEDED,
        expected_reason=ContextResolutionReason.NO_REFERENCE_SIGNAL,
        expected_signal_strength="none",
    ),
    YueReferenceReplayCase(
        name="standalone_factual_question_after_unrelated_document_reference",
        current_input="PostgreSQL 默认端口是多少？",
        host_records=(
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 13, 8),
                assistant_turn_id="turn-67b",
            ),
        ),
        expected_action=ContextResolutionAction.NO_CONTEXT_NEEDED,
        expected_reason=ContextResolutionReason.NO_REFERENCE_SIGNAL,
        expected_signal_strength="none",
    ),
    YueReferenceReplayCase(
        name="standalone_greeting_after_dense_history_keeps_no_context",
        current_input="你好",
        host_records=(
            Message(
                role="assistant",
                content="python export.py --user Bob --format csv",
                timestamp=datetime(2026, 5, 23, 10, 13, 12),
                assistant_turn_id="turn-67c",
            ),
            Message(
                role="assistant",
                content="文档在 docs/specs/session_context_api_spec_20260522.md",
                timestamp=datetime(2026, 5, 23, 10, 13, 16),
                assistant_turn_id="turn-67d",
            ),
        ),
        expected_action=ContextResolutionAction.NO_CONTEXT_NEEDED,
        expected_reason=ContextResolutionReason.GREETING_OR_SMALLTALK,
        expected_signal_strength="none",
    ),
    YueReferenceReplayCase(
        name="compare_options_reference_uses_recent_artifact",
        current_input="比较一下刚才第一种和第二种方案",
        host_records=(
            Message(role="user", content="给我三个持久化方案", timestamp=datetime(2026, 5, 23, 10, 14, 0)),
            Message(
                role="assistant",
                content="方案一 Redis，方案二 SQLite 持久化，方案三 对象存储。",
                timestamp=datetime(2026, 5, 23, 10, 14, 4),
                assistant_turn_id="turn-68",
            ),
        ),
        expected_action=ContextResolutionAction.USE_RECENT_ARTIFACT,
        expected_reason=ContextResolutionReason.ORDINAL_REFERENCE,
        expected_prompt_blocks=("recent_structured_artifacts",),
        expected_selected_source="recent_artifact",
        expected_selected_content_type="numbered_option",
        expected_signal_strength="explicit",
        expected_trace_block_name="recent_structured_artifacts",
    ),
)


def test_yue_reference_replay_case_count_covers_minimum_host_shapes():
    assert len(YUE_REFERENCE_REPLAY_CASES) >= 20


TRANSCRIPT_DERIVED_FIXTURE_FILES = (
    "browser_validation_session_context_flow.json",
    "browser_validation_mixed_language_doc_ref.json",
    "browser_validation_standalone_negative.json",
)

REVIEWED_TRAFFIC_FIXTURE_FILES = (
    "reviewed_traffic_explicit_path_access.json",
    "reviewed_traffic_json_canvas_preview.json",
    "reviewed_traffic_deepseek_small_window_second_plan_recovery.json",
)


def test_yue_transcript_derived_fixture_count_covers_browser_validation_seed_set():
    assert len(TRANSCRIPT_DERIVED_FIXTURE_FILES) >= 3


def test_yue_reviewed_traffic_fixture_count_covers_first_manual_promotion_pass():
    assert len(REVIEWED_TRAFFIC_FIXTURE_FILES) >= 2


@pytest.mark.parametrize("fixture_name", TRANSCRIPT_DERIVED_FIXTURE_FILES)
def test_yue_transcript_derived_replay_fixtures_validate_reference_host_seams(fixture_name: str):
    payload = _load_transcript_fixture(fixture_name)
    host_records, _ = _host_records_from_transcript_fixture(payload)
    expected = payload["expected"]
    manager = _manager()
    replay_case = SessionContextReplayCase.from_host_records(
        case_id=str(payload["case_id"]),
        session_id=str(payload["chat_id"]),
        current_input=str(payload["current_input"]),
        host_records=host_records,
        adapter=YueHostEventAdapter(),
        config=ContextResolutionConfig(session_id=str(payload["chat_id"])),
    )

    plan = replay_case.run(manager)

    assert plan.decision.action.value == expected["action"]
    assert plan.decision.reason.value == expected["reason"]
    assert plan.telemetry["reference_signal_strength"] == expected["signal_strength"]

    selected_source = expected.get("selected_source")
    if selected_source is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].source == selected_source

    selected_content_type = expected.get("selected_content_type")
    if selected_content_type is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].content_type == selected_content_type

    for block_name in expected.get("prompt_blocks", []):
        assert block_name in plan.telemetry["prompt_block_names"]


@pytest.mark.parametrize("fixture_name", REVIEWED_TRAFFIC_FIXTURE_FILES)
def test_yue_reviewed_traffic_replay_fixtures_validate_reference_host_seams(fixture_name: str):
    payload = _load_transcript_fixture(fixture_name)
    host_records, _ = _host_records_from_transcript_fixture(payload)
    memory_chunks = _load_memory_chunks_from_fixture(payload)
    config_overrides = _load_config_overrides_from_fixture(payload)
    expected = payload["expected"]
    manager = _manager(memory_chunks)
    replay_case = SessionContextReplayCase.from_host_records(
        case_id=str(payload["case_id"]),
        session_id=str(payload.get("chat_id") or payload["case_id"]),
        current_input=str(payload["current_input"]),
        host_records=host_records,
        adapter=YueHostEventAdapter(),
        config=ContextResolutionConfig(
            session_id=str(payload.get("chat_id") or payload["case_id"]),
            **config_overrides,
        ),
    )

    plan = replay_case.run(manager)

    assert plan.decision.action.value == expected["action"]
    assert plan.decision.reason.value == expected["reason"]
    assert plan.telemetry["reference_signal_strength"] == expected["signal_strength"]

    for block_name in expected.get("prompt_blocks", []):
        assert block_name in plan.telemetry["prompt_block_names"]

    selected_source = expected.get("selected_source")
    if selected_source is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].source == selected_source

    selected_content_type = expected.get("selected_content_type")
    if selected_content_type is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].content_type == selected_content_type


@pytest.mark.parametrize(
    "case",
    YUE_REFERENCE_REPLAY_CASES,
    ids=[case.name for case in YUE_REFERENCE_REPLAY_CASES],
)
def test_yue_reference_host_replay_corpus_validates_generic_seams(case: YueReferenceReplayCase):
    adapter = YueHostEventAdapter()
    manager = _manager(case.memory_chunks)
    replay_case = SessionContextReplayCase.from_host_records(
        case_id=case.name,
        session_id="chat-replay",
        current_input=case.current_input,
        host_records=case.host_records,
        adapter=adapter,
        config=ContextResolutionConfig(session_id="chat-replay", **case.config_overrides),
    )

    plan = replay_case.run(manager)

    assert plan.decision.action == case.expected_action
    assert plan.decision.reason == case.expected_reason
    assert plan.decision.should_retrieve is case.expected_should_retrieve

    if case.expected_selected_source is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].source == case.expected_selected_source

    if case.expected_selected_content_type is not None:
        assert plan.selected_candidates
        assert plan.selected_candidates[0].content_type == case.expected_selected_content_type

    if case.expected_signal_strength is not None:
        assert plan.telemetry["reference_signal_strength"] == case.expected_signal_strength

    for block_name in case.expected_prompt_blocks:
        assert block_name in plan.telemetry["prompt_block_names"]

    if case.expected_trace_block_name is not None:
        prompt_bridge = render_exported_prompt_context(export_prompt_context(plan.prompt_blocks, selected_candidates=plan.selected_candidates))
        assert case.expected_trace_block_name in prompt_bridge.block_names
        assert "session_trace.sections=" in prompt_bridge.rendered_prompt_block


def test_yue_reference_host_prompt_mode_comparison_preserves_selected_evidence_traceability():
    adapter = YueHostEventAdapter()
    manager = SessionContextManager()
    host_records = (
        Message(role="user", content="给我三个持久化方案", timestamp=datetime(2026, 5, 23, 10, 5, 0)),
        Message(
            role="assistant",
            content="方案一 Redis，方案二 SQLite 持久化，方案三 对象存储。",
            timestamp=datetime(2026, 5, 23, 10, 5, 4),
            assistant_turn_id="turn-40",
        ),
    )

    compatibility_case = SessionContextReplayCase.from_host_records(
        case_id="compatibility_mode",
        session_id="chat-mode",
        current_input="刚才第二个方案继续展开一下",
        host_records=host_records,
        adapter=adapter,
        config=ContextResolutionConfig(session_id="chat-mode"),
        current_tool_results=("tool output",),
    )
    strict_case = SessionContextReplayCase.from_host_records(
        case_id="strict_mode",
        session_id="chat-mode",
        current_input="刚才第二个方案继续展开一下",
        host_records=host_records,
        adapter=adapter,
        config=ContextResolutionConfig(
            session_id="chat-mode",
            selected_evidence_only=True,
            include_full_recent_conversation=False,
            include_current_tool_results=True,
        ),
        current_tool_results=("tool output",),
    )

    compatibility_plan = compatibility_case.run(manager)
    strict_plan = strict_case.run(manager)
    compatibility_bridge = render_exported_prompt_context(
        export_prompt_context(
            compatibility_plan.prompt_blocks,
            selected_candidates=compatibility_plan.selected_candidates,
        )
    )
    strict_bridge = render_exported_prompt_context(
        export_prompt_context(
            strict_plan.prompt_blocks,
            selected_candidates=strict_plan.selected_candidates,
        )
    )

    assert "recent_conversation" in compatibility_bridge.block_names
    assert "recent_structured_artifacts" in compatibility_bridge.block_names
    assert [block.name for block in strict_plan.prompt_blocks] == [
        "safety_statement",
        "current_tool_results",
        "recent_structured_artifacts",
    ]
    assert "recent_conversation" not in strict_bridge.block_names
    assert strict_bridge.selected_candidate_ids == compatibility_bridge.selected_candidate_ids
    assert "session_trace.selected_candidate_ids=" in strict_bridge.rendered_prompt_block
    assert "recent_context:recent_conversation" in compatibility_bridge.rendered_prompt_block
    assert "recent_artifacts:recent_structured_artifacts" in strict_bridge.rendered_prompt_block
