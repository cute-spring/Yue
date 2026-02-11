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
