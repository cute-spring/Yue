import pytest
import os
import json
import tempfile
from datetime import datetime
from app.services.notebook_service import NotebookService, Note

@pytest.fixture
def temp_notebook_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        notes_file = os.path.join(tmpdir, "notes.json")
        with patch("app.services.notebook_service.DATA_DIR", tmpdir), \
             patch("app.services.notebook_service.NOTES_FILE", notes_file):
            service = NotebookService()
            yield service

from unittest.mock import patch

def test_ensure_data_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        notes_file = os.path.join(tmpdir, "subdir", "notes.json")
        with patch("app.services.notebook_service.DATA_DIR", os.path.join(tmpdir, "subdir")), \
             patch("app.services.notebook_service.NOTES_FILE", notes_file):
            service = NotebookService()
            assert os.path.exists(notes_file)
            with open(notes_file, 'r') as f:
                assert json.load(f) == []

def test_create_and_list_notes(temp_notebook_service):
    note = temp_notebook_service.create_note(title="Test", content="Content")
    assert note.title == "Test"
    assert note.content == "Content"
    
    notes = temp_notebook_service.list_notes()
    assert len(notes) == 1
    assert notes[0].id == note.id

def test_get_note(temp_notebook_service):
    note = temp_notebook_service.create_note(title="Test", content="Content")
    retrieved = temp_notebook_service.get_note(note.id)
    assert retrieved.id == note.id
    
    assert temp_notebook_service.get_note("non-existent") is None

def test_update_note(temp_notebook_service):
    note = temp_notebook_service.create_note(title="Old", content="Old Content")
    updated = temp_notebook_service.update_note(note.id, title="New", content="New Content")
    
    assert updated.title == "New"
    assert updated.content == "New Content"
    assert updated.updated_at > note.updated_at
    
    # Partial update
    updated2 = temp_notebook_service.update_note(note.id, title="Newer")
    assert updated2.title == "Newer"
    assert updated2.content == "New Content"
    
    assert temp_notebook_service.update_note("non-existent", title="Fail") is None

def test_delete_note(temp_notebook_service):
    note = temp_notebook_service.create_note(title="Delete Me", content="...")
    assert temp_notebook_service.delete_note(note.id) is True
    assert len(temp_notebook_service.list_notes()) == 0
    assert temp_notebook_service.delete_note("non-existent") is False

def test_list_notes_decode_error(temp_notebook_service):
    from app.services.notebook_service import NOTES_FILE
    with open(NOTES_FILE, 'w') as f:
        f.write("invalid json")
    
    notes = temp_notebook_service.list_notes()
    assert notes == []
