from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.api.note_enrichment import generate_note_enrichment
from app.services.notebook_service import notebook_service, Note
from app.services.workspace_service import workspace_service

router = APIRouter()


def _with_promotion_hint(note: Note, *, include: bool = True) -> Note:
    if not include or not note.workspace_id:
        return note
    hint = workspace_service.build_note_promotion_hint(note.workspace_id, note_id=note.id)
    return note.model_copy(update={"promotion_hint": hint or {}})

class NoteCreate(BaseModel):
    workspace_id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    content: str
    tags: List[str] = Field(default_factory=list)
    note_type: Optional[str] = None
    capture_type: str = "manual"
    status: str = "saved"
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    source_message_ids: List[int] = Field(default_factory=list)
    citation_refs: List[Dict[str, Any]] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    promoted_memory_id: Optional[str] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    note_type: Optional[str] = None
    capture_type: Optional[str] = None
    status: Optional[str] = None
    workspace_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    source_message_ids: Optional[List[int]] = None
    citation_refs: Optional[List[Dict[str, Any]]] = None
    source_metadata: Optional[Dict[str, Any]] = None
    promoted_memory_id: Optional[str] = None

@router.get("/", response_model=List[Note])
async def list_notes(
    workspace_id: Optional[str] = Query(default=None),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags to filter"),
    note_type: Optional[str] = Query(default=None),
    capture_type: Optional[str] = Query(default=None),
    source_session_id: Optional[str] = Query(default=None),
    include_promotion_hints: bool = Query(default=False),
):
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None
    notes = notebook_service.list_notes(
        workspace_id=workspace_id,
        tags=parsed_tags,
        note_type=note_type,
        capture_type=capture_type,
        source_session_id=source_session_id,
    )
    if not include_promotion_hints:
        return notes
    return [_with_promotion_hint(note) for note in notes]

@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str, include_promotion_hints: bool = Query(default=False)):
    note = notebook_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _with_promotion_hint(note, include=include_promotion_hints)

@router.post("/", response_model=Note)
async def create_note(note: NoteCreate):
    generated = await generate_note_enrichment(
        content=note.content,
        title=note.title,
        summary=note.summary,
        tags=note.tags,
        note_type=note.note_type,
        source_metadata=note.source_metadata,
    )
    created = notebook_service.create_note(
        note.title or generated.get("title"),
        note.content,
        workspace_id=note.workspace_id,
        summary=note.summary or generated.get("summary"),
        tags=note.tags or generated.get("tags") or [],
        note_type=note.note_type or generated.get("note_type"),
        capture_type=note.capture_type,
        status=note.status,
        source_session_id=note.source_session_id,
        source_message_id=note.source_message_id,
        source_message_ids=note.source_message_ids,
        citation_refs=note.citation_refs,
        source_metadata=note.source_metadata,
        promoted_memory_id=note.promoted_memory_id,
    )
    return _with_promotion_hint(created)

@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, update: NoteUpdate):
    current_note = notebook_service.get_note(note_id)
    if not current_note:
        raise HTTPException(status_code=404, detail="Note not found")
    next_content = update.content if update.content is not None else current_note.content
    merged_source_metadata = dict(current_note.source_metadata or {})
    if update.source_metadata is not None:
        merged_source_metadata.update(update.source_metadata)
    generated = await generate_note_enrichment(
        content=next_content,
        title=update.title or current_note.title,
        summary=update.summary,
        tags=update.tags,
        note_type=update.note_type,
        source_metadata=merged_source_metadata,
    )
    note = notebook_service.update_note(
        note_id,
        update.title,
        update.content,
        summary=update.summary or generated.get("summary"),
        tags=update.tags if update.tags is not None else generated.get("tags"),
        note_type=update.note_type or generated.get("note_type"),
        capture_type=update.capture_type,
        status=update.status,
        workspace_id=update.workspace_id,
        source_session_id=update.source_session_id,
        source_message_id=update.source_message_id,
        source_message_ids=update.source_message_ids,
        citation_refs=update.citation_refs,
        source_metadata=update.source_metadata,
        promoted_memory_id=update.promoted_memory_id,
    )
    return _with_promotion_hint(note)

@router.delete("/{note_id}")
async def delete_note(note_id: str):
    if not notebook_service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "success"}
