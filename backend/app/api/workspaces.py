from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.chat_service import chat_service
from app.services.notebook_service import notebook_service
from app.services.workspace_service import workspace_service

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_agent_id: Optional[str] = None
    source_policy: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_agent_id: Optional[str] = None
    source_policy: Optional[Dict[str, Any]] = None


class WorkspaceSourceCreate(BaseModel):
    source_type: str
    source_ref: str
    display_name: Optional[str] = None
    mime_type: Optional[str] = None
    status: str = "ready"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceArtifactCreate(BaseModel):
    artifact_type: str
    title: str
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    action_state_id: Optional[int] = None
    artifact_path: Optional[str] = None
    content_ref: Optional[str] = None
    artifact_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceArtifactUpdate(BaseModel):
    artifact_type: Optional[str] = None
    title: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    action_state_id: Optional[int] = None
    artifact_path: Optional[str] = None
    content_ref: Optional[str] = None
    artifact_metadata: Optional[Dict[str, Any]] = None


class ResearchArtifactCreate(BaseModel):
    question: str
    summary: str = ""
    source_ids: list[str] = Field(default_factory=list)
    mode: str = "normal"
    findings: list[Dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    export_paths: list[str] = Field(default_factory=list)
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None


class NoteFromMessageCreate(BaseModel):
    chat_id: str
    message_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)
    citation_refs: list[Dict[str, Any]] = Field(default_factory=list)


class NoteFromSourceCreate(BaseModel):
    source_id: str
    title: Optional[str] = None
    content: str
    citation_refs: list[Dict[str, Any]] = Field(default_factory=list)


@router.get("/")
async def list_workspaces():
    return [workspace.model_dump(mode="json") for workspace in workspace_service.list_workspaces()]


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    workspace = workspace_service.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace.model_dump(mode="json")


@router.get("/{workspace_id}/sources")
async def list_workspace_sources(workspace_id: str):
    sources = workspace_service.list_sources(workspace_id)
    if sources is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [source.model_dump(mode="json") for source in sources]


@router.get("/{workspace_id}/artifacts")
async def list_workspace_artifacts(workspace_id: str):
    artifacts = workspace_service.list_artifacts(workspace_id)
    if artifacts is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [artifact.model_dump(mode="json") for artifact in artifacts]


@router.get("/{workspace_id}/research-artifacts")
async def list_research_artifacts(workspace_id: str):
    artifacts = workspace_service.list_artifacts(workspace_id)
    if artifacts is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [
        artifact.model_dump(mode="json")
        for artifact in artifacts
        if artifact.artifact_type == "research_report"
    ]


@router.get("/{workspace_id}/sources/{source_id}")
async def get_workspace_source(workspace_id: str, source_id: str):
    source = workspace_service.get_source(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Workspace source not found")
    return source.model_dump(mode="json")


@router.post("/{workspace_id}/sources/{source_id}/check")
async def check_workspace_source(workspace_id: str, source_id: str):
    result = workspace_service.check_source(workspace_id, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workspace source not found")
    return result.model_dump(mode="json")


@router.post("/{workspace_id}/sources/check")
async def check_workspace_sources(workspace_id: str):
    result = workspace_service.check_sources(workspace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [item.model_dump(mode="json") for item in result]


@router.get("/{workspace_id}/artifacts/{artifact_id}")
async def get_workspace_artifact(workspace_id: str, artifact_id: str):
    artifact = workspace_service.get_artifact(workspace_id, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Workspace artifact not found")
    return artifact.model_dump(mode="json")


@router.get("/{workspace_id}/research-artifacts/{artifact_id}")
async def get_research_artifact(workspace_id: str, artifact_id: str):
    artifact = workspace_service.get_artifact(workspace_id, artifact_id)
    if artifact is None or artifact.artifact_type != "research_report":
        raise HTTPException(status_code=404, detail="Research artifact not found")
    return artifact.model_dump(mode="json")


@router.post("/{workspace_id}/sources")
async def create_workspace_source(workspace_id: str, payload: WorkspaceSourceCreate):
    source_type = payload.source_type.strip()
    source_ref = payload.source_ref.strip()
    if not source_type:
        raise HTTPException(status_code=400, detail="source_type is required")
    if not source_ref:
        raise HTTPException(status_code=400, detail="source_ref is required")

    source = workspace_service.create_source(
        workspace_id,
        source_type=source_type,
        source_ref=source_ref,
        display_name=payload.display_name,
        mime_type=payload.mime_type,
        status=payload.status,
        source_metadata=payload.source_metadata,
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return source.model_dump(mode="json")


@router.post("/{workspace_id}/artifacts")
async def create_workspace_artifact(workspace_id: str, payload: WorkspaceArtifactCreate):
    artifact_type = payload.artifact_type.strip()
    title = payload.title.strip()
    if not artifact_type:
        raise HTTPException(status_code=400, detail="artifact_type is required")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    artifact = workspace_service.create_artifact(
        workspace_id,
        artifact_type=artifact_type,
        title=title,
        source_session_id=payload.source_session_id,
        source_message_id=payload.source_message_id,
        action_state_id=payload.action_state_id,
        artifact_path=payload.artifact_path,
        content_ref=payload.content_ref,
        artifact_metadata=payload.artifact_metadata,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return artifact.model_dump(mode="json")


@router.post("/{workspace_id}/research-artifacts")
async def create_research_artifact(workspace_id: str, payload: ResearchArtifactCreate):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    for source_id in payload.source_ids:
        if workspace_service.get_source(workspace_id, source_id) is None:
            raise HTTPException(status_code=400, detail=f"Invalid workspace source id: {source_id}")

    metadata = {
        "question": question,
        "source_ids": payload.source_ids,
        "mode": payload.mode,
        "summary": payload.summary,
        "findings": payload.findings,
        "open_questions": payload.open_questions,
        "export_paths": payload.export_paths,
    }
    artifact = workspace_service.create_artifact(
        workspace_id,
        artifact_type="research_report",
        title=question[:80],
        source_session_id=payload.source_session_id,
        source_message_id=payload.source_message_id,
        content_ref=f"research:{question[:48]}",
        artifact_metadata=metadata,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return artifact.model_dump(mode="json")


@router.post("/{workspace_id}/notes/from-message")
async def create_note_from_message(workspace_id: str, payload: NoteFromMessageCreate):
    workspace = workspace_service.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    chat = chat_service.get_chat(payload.chat_id)
    if chat is None or chat.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace chat not found")
    message = None
    if payload.message_id is not None:
        message = next((msg for msg in chat.messages if msg.id == payload.message_id), None)
    else:
        message = next((msg for msg in reversed(chat.messages) if msg.role == "assistant"), None)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    content = payload.content if payload.content is not None else message.content
    title = (payload.title or content[:60] or "Workspace note").strip()
    note_body = "\n\n".join(
        [
            content,
            f"Source chat: {chat.id}",
            f"Source message: {message.id}",
            f"Workspace sources: {', '.join(payload.source_ids) if payload.source_ids else 'none'}",
        ]
    )
    note = notebook_service.create_note(title=title, content=note_body)
    workspace_service.create_source(
        workspace_id,
        source_type="note",
        source_ref=note.id,
        display_name=note.title,
        status="ready",
        source_metadata={
            "note_id": note.id,
            "source_chat_id": chat.id,
            "source_message_id": message.id,
            "source_ids": payload.source_ids,
            "citation_refs": payload.citation_refs,
        },
    )
    return note.model_dump(mode="json")


@router.post("/{workspace_id}/notes/from-source")
async def create_note_from_source(workspace_id: str, payload: NoteFromSourceCreate):
    source = workspace_service.get_source(workspace_id, payload.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Workspace source not found")
    title = (payload.title or source.display_name or "Workspace source note").strip()
    note = notebook_service.create_note(title=title, content=payload.content)
    workspace_service.create_source(
        workspace_id,
        source_type="note",
        source_ref=note.id,
        display_name=note.title,
        status="ready",
        source_metadata={
            "note_id": note.id,
            "source_id": payload.source_id,
            "citation_refs": payload.citation_refs,
        },
    )
    return note.model_dump(mode="json")


@router.post("/")
async def create_workspace(payload: WorkspaceCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Workspace name is required")
    workspace = workspace_service.create_workspace(
        name=name,
        description=payload.description,
        default_agent_id=payload.default_agent_id,
        source_policy=payload.source_policy,
    )
    return workspace.model_dump(mode="json")


@router.put("/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate):
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=400, detail="Workspace name is required")
    updates: Dict[str, Any] = {}
    if "name" in payload.model_fields_set:
        updates["name"] = payload.name
    if "description" in payload.model_fields_set:
        updates["description"] = payload.description
    if "default_agent_id" in payload.model_fields_set:
        updates["default_agent_id"] = payload.default_agent_id
    if "source_policy" in payload.model_fields_set:
        updates["source_policy"] = payload.source_policy
    workspace = workspace_service.update_workspace(
        workspace_id,
        **updates,
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace.model_dump(mode="json")


@router.put("/{workspace_id}/artifacts/{artifact_id}")
async def update_workspace_artifact(workspace_id: str, artifact_id: str, payload: WorkspaceArtifactUpdate):
    if "artifact_type" in payload.model_fields_set and (payload.artifact_type is None or not payload.artifact_type.strip()):
        raise HTTPException(status_code=400, detail="artifact_type is required")
    if "title" in payload.model_fields_set and (payload.title is None or not payload.title.strip()):
        raise HTTPException(status_code=400, detail="title is required")

    updates: Dict[str, Any] = {}
    for field in (
        "artifact_type",
        "title",
        "source_session_id",
        "source_message_id",
        "action_state_id",
        "artifact_path",
        "content_ref",
        "artifact_metadata",
    ):
        if field in payload.model_fields_set:
            updates[field] = getattr(payload, field)

    artifact = workspace_service.update_artifact(workspace_id, artifact_id, **updates)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Workspace artifact not found")
    return artifact.model_dump(mode="json")


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, force: bool = Query(False)):
    try:
        deleted = workspace_service.delete_workspace(workspace_id, force=force)
    except ValueError as exc:
        if str(exc) == "workspace_not_empty":
            raise HTTPException(status_code=409, detail="Workspace is not empty")
        raise
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "success"}


@router.delete("/{workspace_id}/sources/{source_id}")
async def delete_workspace_source(workspace_id: str, source_id: str):
    deleted = workspace_service.delete_source(workspace_id, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace source not found")
    return {"status": "success"}


@router.delete("/{workspace_id}/artifacts/{artifact_id}")
async def delete_workspace_artifact(workspace_id: str, artifact_id: str):
    deleted = workspace_service.delete_artifact(workspace_id, artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace artifact not found")
    return {"status": "success"}
