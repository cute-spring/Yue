import pytest
import os
import sqlite3
import json
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch
from app.services.chat_service import ChatService, Message, ChatSession

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    # Patch the module-level constants before creating ChatService
    with patch("app.services.chat_service.DB_FILE", db_file), \
         patch("app.services.chat_service.DATA_DIR", temp_dir):
        service = ChatService()
        yield service, db_file
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

def test_delete_chat(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
    assert service.delete_chat(chat.id) is True
    assert service.get_chat(chat.id) is None
    assert service.delete_chat(chat.id) is False

def test_skill_effectiveness_report(temp_db):
    service, _ = temp_db
    chat = service.create_chat()
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
    report = service.get_skill_effectiveness_report(hours=24)
    assert report["total_runs"] >= 2
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
    # Actually truncate_chat keeps the first keep_count messages and deletes the rest?
    # Wait, let's look at the code:
    # to_delete = [row['id'] for row in rows[keep_count:]]
    # It deletes messages AFTER the keep_count. So it keeps the FIRST keep_count messages.
    
    assert service.truncate_chat(chat.id, 1) is True
    updated = service.get_chat(chat.id)
    assert len(updated.messages) == 1
    assert updated.messages[0].content == "msg1"

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
    events = service.get_chat_events(chat.id)
    event_names = [item["event"] for item in events]
    assert "meta" in event_names
    assert "tool.call.started" in event_names
    assert "tool.call.finished" in event_names
    assert "content.final" in event_names

def test_migrate_from_json(temp_dir_with_json):
    temp_dir, json_file = temp_dir_with_json
    db_file = os.path.join(temp_dir, "yue.db")
    
    with patch("app.services.chat_service.DB_FILE", db_file), \
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
