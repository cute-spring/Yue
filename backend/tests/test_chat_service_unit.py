import pytest
import os
import sqlite3
import json
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.services.chat_service import ChatService, Message, ChatSession

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    
    # Create test engine and session
    test_engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Patch dependencies in chat_service
    with patch("app.services.chat_service.engine", test_engine), \
         patch("app.services.chat_service.SessionLocal", TestingSessionLocal), \
         patch("app.services.chat_service.DATA_DIR", temp_dir):
        
        service = ChatService()
        yield service, db_file
        
    test_engine.dispose()
    shutil.rmtree(temp_dir)

def test_ensure_db_creates_tables(temp_db):
    service, db_file = temp_db
    assert os.path.exists(db_file)
    
    with sqlite3.connect(db_file) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "sessions" in tables
        assert "messages" in tables
        assert "skill_effectiveness_events" in tables

def test_create_chat(temp_db):
    service, _ = temp_db
    chat = service.create_chat(agent_id="test-agent", title="My Chat")
    assert chat.title == "My Chat"
    assert chat.agent_id == "test-agent"
    assert chat.messages == []

def test_add_message(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    
    updated = service.add_message(chat.id, "user", "Hello world", thought_duration=1.5, images=["img1.png"])
    assert updated is not None
    assert len(updated.messages) == 1
    msg = updated.messages[0]
    assert msg.role == "user"
    assert msg.content == "Hello world"
    assert msg.thought_duration == 1.5
    assert msg.images == ["img1.png"]
    
    # Check if title updated
    assert updated.title == "Hello world"

def test_update_chat_title_and_summary(temp_db):
    service, _ = temp_db
    chat = service.create_chat(title="Old")
    assert service.update_chat_title(chat.id, "New Title") is True
    assert service.update_chat_summary(chat.id, "Summary text") is True
    loaded = service.get_chat(chat.id)
    assert loaded is not None
    assert loaded.title == "New Title"
    assert loaded.summary == "Summary text"

def test_list_chats(temp_db):
    service, _ = temp_db
    service.create_chat(title="Chat 1")
    service.create_chat(title="Chat 2")
    
    chats = service.list_chats()
    assert len(chats) == 2
    assert chats[0].title == "Chat 2" # Ordered by updated_at DESC

def test_get_chat_not_found(temp_db):
    service, _ = temp_db
    assert service.get_chat("non-existent") is None

def test_get_session_skill(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    
    # Init state
    name, version = service.get_session_skill(chat.id)
    assert name is None
    assert version is None
    
    # Non-existent session
    name, version = service.get_session_skill("invalid_id")
    assert name is None
    assert version is None

def test_set_and_clear_session_skill(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    
    # Set skill
    service.set_session_skill(chat.id, "pdf-skill", "1.0.0")
    name, version = service.get_session_skill(chat.id)
    assert name == "pdf-skill"
    assert version == "1.0.0"
    
    # Clear skill
    service.clear_session_skill(chat.id)
    name, version = service.get_session_skill(chat.id)
    assert name is None
    assert version is None

def test_delete_chat(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    assert service.delete_chat(chat.id) is True
    assert service.get_chat(chat.id) is None
    assert service.delete_chat(chat.id) is False

def test_update_chat_title_and_summary_not_found(temp_db):
    service, _ = temp_db
    assert service.update_chat_title("invalid_id", "New") is False
    assert service.update_chat_summary("invalid_id", "Summary") is False

def test_add_message_chat_not_found(temp_db):
    service, _ = temp_db
    res = service.add_message("invalid_id", "user", "Hello")
    assert res is None

def test_skill_effectiveness_report(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    
    # Test with no data first to cover empty aggregations
    report_empty = service.get_skill_effectiveness_report(hours=24)
    assert report_empty["total_runs"] == 0
    assert report_empty["skill_hit_rate"] == 0.0
    
    service.add_skill_effectiveness_event(chat.id, {
        "reason_code": "skill_selected",
        "selection_source": "inferred",
        "fallback_used": False,
        "selected_skill": {"name": "pdf-insight-extractor", "version": "1.0.0"},
        "visible_skill_count": 4,
        "available_skill_count": 3,
        "always_injected_count": 1,
        "summary_injected": True,
        "summary_prompt_enabled": True,
        "lazy_full_load_enabled": True,
        "system_prompt_tokens_estimate": 120,
        "user_message_tokens_estimate": 30,
    })
    service.add_skill_effectiveness_event(chat.id, {
        "reason_code": "no_matching_skill",
        "selection_source": "none",
        "fallback_used": True,
        "selected_skill": None,
        "visible_skill_count": 4,
        "available_skill_count": 3,
        "always_injected_count": 0,
        "summary_injected": True,
        "summary_prompt_enabled": True,
        "lazy_full_load_enabled": True,
        "system_prompt_tokens_estimate": 80,
        "user_message_tokens_estimate": 20,
    })
    
    # Test case where missing keys in event payload
    service.add_skill_effectiveness_event(chat.id, {})
    
    report = service.get_skill_effectiveness_report(hours=24)
    assert report["total_runs"] >= 3
    assert report["fallback_rate"] > 0
    assert report["skill_hit_rate"] >= 0
    assert "reason_distribution" in report
    assert "top_selected_skills" in report

def test_truncate_chat(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_message(chat.id, "user", "msg1")
    service.add_message(chat.id, "assistant", "msg2")
    service.add_message(chat.id, "user", "msg3")
    
    # Truncate to keep first 1 message
    assert service.truncate_chat(chat.id, 1) is True
    updated = service.get_chat(chat.id)
    assert len(updated.messages) == 1
    assert updated.messages[0].content == "msg1"
    
    # Truncate to keep more messages than exist (should return False)
    assert service.truncate_chat(chat.id, 5) is False

def test_tool_calls_bound_to_assistant_turn(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_message(chat.id, "user", "u1")
    service.add_message(chat.id, "assistant", "a1", assistant_turn_id="turn_1", run_id="run_1")
    service.add_message(chat.id, "user", "u2")
    service.add_message(chat.id, "assistant", "a2", assistant_turn_id="turn_2", run_id="run_2")

    service.add_tool_call(
        session_id=chat.id,
        call_id="call_turn1",
        tool_name="docs_search",
        args={"q": "one"},
        assistant_turn_id="turn_1",
        run_id="run_1",
        event_id_started="evt_s_1",
        started_sequence=10
    )
    service.update_tool_call(
        call_id="call_turn1",
        status="success",
        result="ok1",
        event_id_finished="evt_f_1",
        finished_sequence=11
    )
    service.add_tool_call(
        session_id=chat.id,
        call_id="call_turn2",
        tool_name="docs_search",
        args={"q": "two"},
        assistant_turn_id="turn_2",
        run_id="run_2",
        event_id_started="evt_s_2",
        started_sequence=20
    )
    service.update_tool_call(
        call_id="call_turn2",
        status="success",
        result="ok2",
        event_id_finished="evt_f_2",
        finished_sequence=21
    )

    loaded = service.get_chat(chat.id)
    assistants = [m for m in loaded.messages if m.role == "assistant"]
    assert len(assistants) == 2
    assert len(assistants[0].tool_calls or []) == 1
    assert assistants[0].tool_calls[0]["call_id"] == "call_turn1"
    assert len(assistants[1].tool_calls or []) == 1
    assert assistants[1].tool_calls[0]["call_id"] == "call_turn2"

def test_chat_events_replay_consistency(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_message(
        chat.id,
        "assistant",
        "final answer",
        assistant_turn_id="turn_replay",
        run_id="run_replay",
        supports_reasoning=True,
        deep_thinking_enabled=True,
        reasoning_enabled=True
    )
    service.add_tool_call(
        session_id=chat.id,
        call_id="call_replay",
        tool_name="docs_search",
        args={"q": "abc"},
        assistant_turn_id="turn_replay",
        run_id="run_replay",
        event_id_started="evt_start_replay",
        started_sequence=2
    )
    service.update_tool_call(
        call_id="call_replay",
        status="success",
        result="done",
        event_id_finished="evt_finish_replay",
        finished_sequence=3
    )
    
    # Also add an uncompleted tool call and a tool call with no run_id
    service.add_tool_call(
        session_id=chat.id,
        call_id="call_uncompleted",
        tool_name="test_tool",
        assistant_turn_id="turn_replay",
        run_id="run_replay",
        started_sequence=4
    )
    
    service.add_tool_call(
        session_id=chat.id,
        call_id="call_norunid",
        tool_name="test_tool"
    )
    
    events = service.get_chat_events(chat.id)
    event_names = [item["event"] for item in events]
    assert "meta" in event_names
    assert "tool.call.started" in event_names
    assert "tool.call.finished" in event_names
    assert "content.final" in event_names
    
    # Test after_sequence filter
    events_after = service.get_chat_events(chat.id, after_sequence=2)
    assert len(events_after) < len(events)
    
    # Test get_chat_events with specific assistant_turn_id
    events_turn = service.get_chat_events(chat.id, assistant_turn_id="turn_replay")
    assert len(events_turn) > 0


def test_get_chat_trace_bundle_returns_summary_view(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_action_event(
        chat.id,
        {
            "event": "chat.request.snapshot",
            "request_id": "req-1",
            "run_id": "run-1",
            "assistant_turn_id": "turn-1",
            "snapshot": {
                "chat_id": chat.id,
                "assistant_turn_id": "turn-1",
                "request_id": "req-1",
                "run_id": "run-1",
                "created_at": datetime.utcnow().isoformat(),
                "provider": "openai",
                "model": "gpt-4o",
                "system_prompt": "secret prompt",
                "user_message": "hello",
                "message_history": [],
                "attachments": [],
                "tool_context": {"enabled_tools": ["docs_search"]},
                "skill_context": {},
                "runtime_flags": {},
                "redaction": {},
                "truncation": {},
            },
        },
        assistant_turn_id="turn-1",
        run_id="run-1",
    )
    service.add_action_event(
        chat.id,
        {
            "event": "tool.trace.record",
            "trace_id": "trace-1",
            "run_id": "run-1",
            "assistant_turn_id": "turn-1",
            "trace": {
                "chat_id": chat.id,
                "run_id": "run-1",
                "assistant_turn_id": "turn-1",
                "trace_id": "trace-1",
                "tool_name": "docs_search",
                "call_id": "call-1",
                "call_index": 1,
                "status": "success",
                "input_arguments": {"q": "hello"},
                "output_result": {"ok": True},
                "chain_depth": 0,
            },
        },
        assistant_turn_id="turn-1",
        run_id="run-1",
    )

    bundle = service.get_chat_trace_bundle(chat.id, mode="summary")

    assert bundle is not None
    assert bundle["mode"] == "summary"
    assert bundle["snapshot"]["user_message"] == "hello"
    assert bundle["snapshot"]["system_prompt"] is None
    assert bundle["snapshot"]["redaction"]["system_prompt"] is True
    assert len(bundle["tool_traces"]) == 1
    assert bundle["tool_traces"][0]["trace_id"] == "trace-1"
    assert bundle["tool_traces"][0]["input_arguments"] is None
    assert bundle["tool_traces"][0]["output_result"] is None


def test_get_chat_trace_bundle_returns_raw_view(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_action_event(
        chat.id,
        {
            "event": "chat.request.snapshot",
            "request_id": "req-1",
            "run_id": "run-1",
            "assistant_turn_id": "turn-1",
            "snapshot": {
                "chat_id": chat.id,
                "assistant_turn_id": "turn-1",
                "request_id": "req-1",
                "run_id": "run-1",
                "created_at": datetime.utcnow().isoformat(),
                "provider": "openai",
                "model": "gpt-4o",
                "system_prompt": "secret prompt",
                "user_message": "hello",
                "message_history": [],
                "attachments": [],
                "tool_context": {"enabled_tools": ["docs_search"]},
                "skill_context": {},
                "runtime_flags": {},
                "redaction": {},
                "truncation": {},
            },
        },
        assistant_turn_id="turn-1",
        run_id="run-1",
    )
    service.add_action_event(
        chat.id,
        {
            "event": "tool.trace.record",
            "trace_id": "trace-1",
            "run_id": "run-1",
            "assistant_turn_id": "turn-1",
            "trace": {
                "chat_id": chat.id,
                "run_id": "run-1",
                "assistant_turn_id": "turn-1",
                "trace_id": "trace-1",
                "tool_name": "docs_search",
                "call_id": "call-1",
                "call_index": 1,
                "status": "success",
                "input_arguments": {"q": "hello"},
                "output_result": {"ok": True},
                "chain_depth": 0,
            },
        },
        assistant_turn_id="turn-1",
        run_id="run-1",
    )

    bundle = service.get_chat_trace_bundle(chat.id, mode="raw")

    assert bundle is not None
    assert bundle["mode"] == "raw"
    assert bundle["snapshot"]["system_prompt"] == "secret prompt"
    assert bundle["tool_traces"][0]["input_arguments"] == {"q": "hello"}
    assert bundle["tool_traces"][0]["output_result"] == {"ok": True}


def test_get_chat_trace_bundle_returns_none_without_snapshot(temp_db):
    service, _ = temp_db
    chat = service.create_chat()

    bundle = service.get_chat_trace_bundle(chat.id, mode="summary")

    assert bundle is None


def test_get_chat_trace_bundle_rejects_unknown_mode(temp_db):
    service, _ = temp_db
    chat = service.create_chat()

    with pytest.raises(ValueError, match="Unsupported trace bundle mode"):
        service.get_chat_trace_bundle(chat.id, mode="invalid")

def test_chat_events_replay_includes_action_events(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_message(
        chat.id,
        "assistant",
        "action preflight summary",
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.preflight",
            "event_id": "evt_action_preflight",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 2,
            "ts": "2026-03-27T00:00:00Z",
            "lifecycle_phase": "preflight",
            "lifecycle_status": "preflight_evaluated",
            "skill_name": "action-skill",
            "action_id": "generate",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_result",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 3,
            "ts": "2026-03-27T00:00:01Z",
            "lifecycle_phase": "preflight",
            "lifecycle_status": "preflight_approval_required",
            "skill_name": "action-skill",
            "action_id": "generate",
            "status": "approval_required",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )

    events = service.get_chat_events(chat.id, assistant_turn_id="turn_action")
    event_names = [item["event"] for item in events]
    assert "skill.action.preflight" in event_names
    assert "skill.action.result" in event_names
    result_event = next(item for item in events if item["event"] == "skill.action.result")
    assert result_event["lifecycle_status"] == "preflight_approval_required"

def test_action_state_tracks_latest_lifecycle_from_action_events(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_preflight",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 3,
            "ts": "2026-03-28T00:00:01Z",
            "lifecycle_phase": "preflight",
            "lifecycle_status": "preflight_approval_required",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "status": "approval_required",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_execution",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 4,
            "ts": "2026-03-28T00:00:02Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "awaiting_approval",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "status": "awaiting_approval",
            "approval_token": "approval:action-skill:1.0.0:generate:req-approval",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )

    state = service.get_action_state(chat.id, skill_name="action-skill", action_id="generate")

    assert state is not None
    assert state.lifecycle_phase == "execution"
    assert state.lifecycle_status == "awaiting_approval"
    assert state.status == "awaiting_approval"
    assert state.approval_token == "approval:action-skill:1.0.0:generate:req-approval"
    assert state.payload["event"] == "skill.action.result"

def test_action_state_updates_after_approval_resume(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    approval_token = "approval:action-skill:1.0.0:generate:req-approval"
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.approval",
            "event_id": "evt_action_approval",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 4,
            "ts": "2026-03-28T00:00:02Z",
            "lifecycle_phase": "approval",
            "lifecycle_status": "approved",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "approved": True,
            "approval_token": approval_token,
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_queued",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 5,
            "ts": "2026-03-28T00:00:03Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "queued",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "status": "queued",
            "approval_token": approval_token,
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )

    state = service.get_action_state(chat.id, skill_name="action-skill", action_id="generate")
    all_states = service.list_action_states(chat.id)

    assert state is not None
    assert state.lifecycle_status == "queued"
    assert state.approval_token == approval_token
    assert len(all_states) == 1
    assert all_states[0].lifecycle_status == "queued"

def test_action_state_separates_multiple_invocations_for_same_action(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_one",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 4,
            "ts": "2026-03-28T00:00:02Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "skipped",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "invocation_id": "invoke:action-skill:1.0.0:generate:req-one",
            "request_id": "req-one",
            "status": "skipped",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_two",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 5,
            "ts": "2026-03-28T00:00:03Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "succeeded",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "invocation_id": "invoke:action-skill:1.0.0:generate:req-two",
            "request_id": "req-two",
            "status": "succeeded",
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )

    latest_state = service.get_action_state(chat.id, skill_name="action-skill", action_id="generate")
    first_invocation = service.get_action_state_by_invocation_id(
        chat.id,
        invocation_id="invoke:action-skill:1.0.0:generate:req-one",
    )
    all_states = service.list_action_states(chat.id)

    assert latest_state is not None
    assert latest_state.invocation_id == "invoke:action-skill:1.0.0:generate:req-two"
    assert latest_state.lifecycle_status == "succeeded"
    assert first_invocation is not None
    assert first_invocation.request_id == "req-one"
    assert len(all_states) == 2
    assert {state.invocation_id for state in all_states} == {
        "invoke:action-skill:1.0.0:generate:req-one",
        "invoke:action-skill:1.0.0:generate:req-two",
    }

def test_get_action_state_by_approval_token_returns_latest_state(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    approval_token = "approval:action-skill:1.0.0:generate:req-approval"
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_waiting",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 4,
            "ts": "2026-03-28T00:00:02Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "awaiting_approval",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "status": "awaiting_approval",
            "approval_token": approval_token,
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )
    service.add_action_event(
        chat.id,
        {
            "version": "v2",
            "event": "skill.action.result",
            "event_id": "evt_action_skipped",
            "run_id": "run_action",
            "assistant_turn_id": "turn_action",
            "sequence": 5,
            "ts": "2026-03-28T00:00:03Z",
            "lifecycle_phase": "execution",
            "lifecycle_status": "skipped",
            "skill_name": "action-skill",
            "skill_version": "1.0.0",
            "action_id": "generate",
            "status": "skipped",
            "approval_token": approval_token,
        },
        assistant_turn_id="turn_action",
        run_id="run_action",
    )

    state = service.get_action_state_by_approval_token(chat.id, approval_token=approval_token)

    assert state is not None
    assert state.skill_name == "action-skill"
    assert state.action_id == "generate"
    assert state.lifecycle_status == "skipped"
    assert state.approval_token == approval_token

def test_migrate_from_json(temp_dir_with_json):
    temp_dir, json_file = temp_dir_with_json
    db_file = os.path.join(temp_dir, "test_yue.db")
    
    test_engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    with patch("app.services.chat_service.engine", test_engine), \
         patch("app.services.chat_service.SessionLocal", TestingSessionLocal), \
         patch("app.services.chat_service.DATA_DIR", temp_dir), \
         patch("app.services.chat_service.OLD_CHATS_FILE", json_file):
        service = ChatService()
        chats = service.list_chats()
        assert len(chats) == 1
        assert chats[0].id == "old-id"
        assert len(chats[0].messages) == 1
        
        # Original file should be renamed
        assert not os.path.exists(json_file)
        assert os.path.exists(json_file + ".bak")
        
        # Test migration skips existing session
        # Restore json file to test the skip path
        shutil.copy(json_file + ".bak", json_file)
        service._migrate_from_json()
        chats_after = service.list_chats()
        assert len(chats_after) == 1 # still 1
        
    test_engine.dispose()

@pytest.fixture
def temp_dir_with_json():
    temp_dir = tempfile.mkdtemp()
    json_file = os.path.join(temp_dir, "chats.json")
    old_data = [{
        "id": "old-id",
        "title": "Old Chat",
        "agent_id": "agent1",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [{"role": "user", "content": "old msg", "timestamp": datetime.now().isoformat()}]
    }]
    with open(json_file, "w") as f:
        json.dump(old_data, f)
    yield temp_dir, json_file
    shutil.rmtree(temp_dir)
