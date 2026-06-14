import json
import os
import shutil
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.notebook_service import NotebookService


@pytest.fixture
def temp_notebook_service():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    notes_file = os.path.join(temp_dir, "notes.json")
    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with patch("app.services.notebook_service.engine", test_engine), \
         patch("app.services.notebook_service.SessionLocal", testing_session_local), \
         patch("app.services.notebook_service.DATA_DIR", temp_dir), \
         patch("app.services.notebook_service.NOTES_FILE", notes_file):
        service = NotebookService()
        yield service, db_file, notes_file

    test_engine.dispose()
    shutil.rmtree(temp_dir)


def test_ensure_storage_creates_workspace_notes_table(temp_notebook_service):
    _, db_file, _ = temp_notebook_service

    with sqlite3.connect(db_file) as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "workspace_notes" in tables


def test_create_and_list_notes(temp_notebook_service):
    service, _, _ = temp_notebook_service
    note = service.create_note(
        title=None,
        content="实现 Chat-to-Note 的结构化保存，并支持来源回链。",
        workspace_id="ws_1",
        capture_type="chat_capture",
        source_session_id="chat_1",
        source_message_id=7,
        source_metadata={"captured_from": "assistant_message"},
    )

    assert note.workspace_id == "ws_1"
    assert note.title
    assert note.summary
    assert note.note_type in {"insight", "summary", "decision", "fact", "preference", "reference", "todo"}
    assert note.capture_type == "chat_capture"
    assert note.source_session_id == "chat_1"
    assert note.source_message_id == 7

    notes = service.list_notes(workspace_id="ws_1")
    assert len(notes) == 1
    assert notes[0].id == note.id
    assert notes[0].summary == note.summary


def test_get_note(temp_notebook_service):
    service, _, _ = temp_notebook_service
    note = service.create_note(title="Test", content="Content")
    retrieved = service.get_note(note.id)
    assert retrieved is not None
    assert retrieved.id == note.id
    assert service.get_note("non-existent") is None


def test_update_note_regenerates_summary_and_tags(temp_notebook_service):
    service, _, _ = temp_notebook_service
    note = service.create_note(title="Old", content="Old Content")

    updated = service.update_note(
        note.id,
        content="新的工作区笔记需要自动摘要、标签和来源信息。",
        source_metadata={"captured_from": "assistant_message"},
    )

    assert updated is not None
    assert updated.title == "Old"
    assert updated.summary
    assert any(tag in updated.tags for tag in ["工作区", "笔记", "摘要", "标签", "来源"])
    assert updated.updated_at > note.updated_at
    assert service.update_note("non-existent", title="Fail") is None


def test_delete_note(temp_notebook_service):
    service, _, _ = temp_notebook_service
    note = service.create_note(title="Delete Me", content="...")
    assert service.delete_note(note.id) is True
    assert len(service.list_notes()) == 0
    assert service.delete_note("non-existent") is False


def test_list_notes_filters_by_tags_and_session(temp_notebook_service):
    service, _, _ = temp_notebook_service
    first = service.create_note(
        title="Memory Capture",
        content="memory capture plan with workspace note recall",
        source_session_id="chat_keep",
    )
    second = service.create_note(
        title="Other",
        content="frontend polish only",
        source_session_id="chat_skip",
    )

    filtered = service.list_notes(tags=["workspace"], source_session_id="chat_keep")
    assert [note.id for note in filtered] == [first.id]
    assert second.id not in [note.id for note in filtered]


def test_migrate_legacy_notes_json_into_database(temp_notebook_service):
    service, _, notes_file = temp_notebook_service
    assert service.list_notes() == []

    legacy_payload = [
        {
            "id": "legacy-1",
            "title": "Legacy Note",
            "content": "Old file-based notebook entry",
            "created_at": "2026-06-01T00:00:00",
            "updated_at": "2026-06-01T00:00:00",
        }
    ]
    with open(notes_file, "w", encoding="utf-8") as handle:
        json.dump(legacy_payload, handle)

    service._migrate_legacy_notes_if_needed()
    notes = service.list_notes()
    assert len(notes) == 1
    assert notes[0].id == "legacy-1"
    assert notes[0].title == "Legacy Note"


def test_build_prompt_context_recalls_relevant_unpromoted_workspace_notes(temp_notebook_service):
    service, _, _ = temp_notebook_service
    recalled = service.create_note(
        title="用户偏好",
        content="用户偏好：默认使用中文，并把结论整理成清晰摘要。",
        workspace_id="ws_recall",
        note_type="preference",
        tags=["偏好", "中文"],
    )
    service.create_note(
        title="已提升的旧笔记",
        content="这条已经变成 memory，不应该继续作为普通 note 召回。",
        workspace_id="ws_recall",
        note_type="decision",
        promoted_memory_id="mem_123",
    )
    service.create_note(
        title="其他工作区",
        content="不应跨工作区召回",
        workspace_id="ws_other",
    )

    context = service.build_prompt_context("ws_recall", current_query="请记住我的中文偏好")
    assert context is not None
    assert context.workspace_id == "ws_recall"
    assert context.loaded_note_ids == [recalled.id]
    assert context.loaded_notes[0].title == "用户偏好"
    assert "Relevant Workspace Notes" in context.prompt_block
