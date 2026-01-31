import json
import os
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class NotebookService:
    def __init__(self):
        self._ensure_data_file()

    def _ensure_data_file(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'w') as f:
                json.dump([], f)

    def list_notes(self) -> List[Note]:
        with open(NOTES_FILE, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return []
            # Sort by updated_at desc
            notes = [Note(**item) for item in data]
            notes.sort(key=lambda x: x.updated_at, reverse=True)
            return notes

    def get_note(self, note_id: str) -> Optional[Note]:
        notes = self.list_notes()
        for note in notes:
            if note.id == note_id:
                return note
        return None

    def create_note(self, title: str, content: str) -> Note:
        notes = self.list_notes()
        note = Note(title=title, content=content)
        notes.append(note)
        self._save_notes(notes)
        return note

    def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> Optional[Note]:
        notes = self.list_notes()
        for i, note in enumerate(notes):
            if note.id == note_id:
                if title is not None:
                    note.title = title
                if content is not None:
                    note.content = content
                note.updated_at = datetime.now()
                notes[i] = note
                self._save_notes(notes)
                return note
        return None

    def delete_note(self, note_id: str) -> bool:
        notes = self.list_notes()
        initial_len = len(notes)
        notes = [n for n in notes if n.id != note_id]
        if len(notes) < initial_len:
            self._save_notes(notes)
            return True
        return False

    def _save_notes(self, notes: List[Note]):
        with open(NOTES_FILE, 'w') as f:
            json.dump([json.loads(n.model_dump_json()) for n in notes], f, indent=2)

notebook_service = NotebookService()
