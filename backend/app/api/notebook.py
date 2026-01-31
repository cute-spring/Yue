from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel
from app.services.notebook_service import notebook_service, Note

router = APIRouter()

class NoteCreate(BaseModel):
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

@router.get("/", response_model=List[Note])
async def list_notes():
    return notebook_service.list_notes()

@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str):
    note = notebook_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.post("/", response_model=Note)
async def create_note(note: NoteCreate):
    return notebook_service.create_note(note.title, note.content)

@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, update: NoteUpdate):
    note = notebook_service.update_note(note_id, update.title, update.content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.delete("/{note_id}")
async def delete_note(note_id: str):
    if not notebook_service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "success"}
