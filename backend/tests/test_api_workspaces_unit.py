import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.services.notebook_service import Note

from app.api.workspaces import router


@pytest.fixture
def client():
    try:
        app = FastAPI()
        app.include_router(router, prefix="/api/workspaces")
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


@pytest.fixture
def mock_workspace_service():
    with patch("app.api.workspaces.workspace_service") as mock:
        yield mock


def test_list_workspaces(client, mock_workspace_service):
    mock_workspace_service.list_workspaces.return_value = []

    response = client.get("/api/workspaces/")

    assert response.status_code == 200
    assert response.json() == []


def test_get_workspace_not_found(client, mock_workspace_service):
    mock_workspace_service.get_workspace.return_value = None

    response = client.get("/api/workspaces/missing")

    assert response.status_code == 404


def test_create_workspace(client, mock_workspace_service):
    payload = {
        "id": "ws_1",
        "name": "Research",
        "description": "desc",
        "default_agent_id": "builtin-pdf-research",
        "source_policy": {"grounding_mode": "prefer_sources"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_workspace = type("WorkspaceStub", (), {"model_dump": lambda self, mode="json": payload})()
    mock_workspace_service.create_workspace.return_value = mock_workspace

    response = client.post(
        "/api/workspaces/",
        json={
            "name": "Research",
            "description": "desc",
            "default_agent_id": "builtin-pdf-research",
            "source_policy": {"grounding_mode": "prefer_sources"},
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "ws_1"
    mock_workspace_service.create_workspace.assert_called_once_with(
        name="Research",
        description="desc",
        default_agent_id="builtin-pdf-research",
        source_policy={"grounding_mode": "prefer_sources"},
    )


def test_list_workspace_sources(client, mock_workspace_service):
    source_payload = {
        "id": "src_1",
        "workspace_id": "ws_1",
        "source_type": "upload",
        "source_ref": "uploads/chat/2026/05/30/att_1.pdf",
        "display_name": "brief.pdf",
        "mime_type": "application/pdf",
        "status": "ready",
        "source_metadata": {"id": "att_1"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_source = type("WorkspaceSourceStub", (), {"model_dump": lambda self, mode="json": source_payload})()
    mock_workspace_service.list_sources.return_value = [mock_source]

    response = client.get("/api/workspaces/ws_1/sources")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "src_1"


def test_create_workspace_source(client, mock_workspace_service):
    source_payload = {
        "id": "src_1",
        "workspace_id": "ws_1",
        "source_type": "upload",
        "source_ref": "uploads/chat/2026/05/30/att_1.pdf",
        "display_name": "brief.pdf",
        "mime_type": "application/pdf",
        "status": "ready",
        "source_metadata": {"id": "att_1"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_source = type("WorkspaceSourceStub", (), {"model_dump": lambda self, mode="json": source_payload})()
    mock_workspace_service.create_source.return_value = mock_source

    response = client.post(
        "/api/workspaces/ws_1/sources",
        json={
            "source_type": "upload",
            "source_ref": "uploads/chat/2026/05/30/att_1.pdf",
            "display_name": "brief.pdf",
            "mime_type": "application/pdf",
            "status": "ready",
            "source_metadata": {"id": "att_1"},
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "src_1"
    mock_workspace_service.create_source.assert_called_once_with(
        "ws_1",
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/att_1.pdf",
        display_name="brief.pdf",
        mime_type="application/pdf",
        status="ready",
        source_metadata={"id": "att_1"},
    )


def test_check_workspace_source(client, mock_workspace_service):
    source_payload = {
        "id": "src_1",
        "workspace_id": "ws_1",
        "source_type": "upload",
        "source_ref": "uploads/chat/2026/05/30/att_1.pdf",
        "display_name": "brief.pdf",
        "mime_type": "application/pdf",
        "status": "ready",
        "source_metadata": {"available_tools": ["docs_read_pdf"], "citation_capable": True},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    payload = {
        "source": source_payload,
        "status": "ready",
        "readiness_metadata": source_payload["source_metadata"],
    }
    mock_result = type("WorkspaceReadinessStub", (), {"model_dump": lambda self, mode="json": payload})()
    mock_workspace_service.check_source.return_value = mock_result

    response = client.post("/api/workspaces/ws_1/sources/src_1/check")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_check_workspace_sources(client, mock_workspace_service):
    mock_workspace_service.check_sources.return_value = []

    response = client.post("/api/workspaces/ws_1/sources/check")

    assert response.status_code == 200
    assert response.json() == []


def test_list_workspace_artifacts(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_1",
        "workspace_id": "ws_1",
        "artifact_type": "export",
        "title": "brief.docx",
        "source_session_id": "chat_1",
        "source_message_id": None,
        "action_state_id": 12,
        "artifact_path": "/exports/brief.docx",
        "content_ref": "invocation-1",
        "artifact_metadata": {"download_url": "/exports/brief.docx"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": artifact_payload})()
    mock_workspace_service.list_artifacts.return_value = [mock_artifact]

    response = client.get("/api/workspaces/ws_1/artifacts")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "art_1"


def test_create_workspace_artifact(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_1",
        "workspace_id": "ws_1",
        "artifact_type": "export",
        "title": "brief.docx",
        "source_session_id": "chat_1",
        "source_message_id": None,
        "action_state_id": 12,
        "artifact_path": "/exports/brief.docx",
        "content_ref": "invocation-1",
        "artifact_metadata": {"download_url": "/exports/brief.docx"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": artifact_payload})()
    mock_workspace_service.create_artifact.return_value = mock_artifact

    response = client.post(
        "/api/workspaces/ws_1/artifacts",
        json={
            "artifact_type": "export",
            "title": "brief.docx",
            "source_session_id": "chat_1",
            "action_state_id": 12,
            "artifact_path": "/exports/brief.docx",
            "content_ref": "invocation-1",
            "artifact_metadata": {"download_url": "/exports/brief.docx"},
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "art_1"
    mock_workspace_service.create_artifact.assert_called_once_with(
        "ws_1",
        artifact_type="export",
        title="brief.docx",
        source_session_id="chat_1",
        source_message_id=None,
        action_state_id=12,
        artifact_path="/exports/brief.docx",
        content_ref="invocation-1",
        artifact_metadata={"download_url": "/exports/brief.docx"},
    )


def test_create_note_from_message_builds_structured_note(client, mock_workspace_service):
    workspace_payload = {
        "id": "ws_1",
        "name": "Research",
        "description": None,
        "default_agent_id": None,
        "source_policy": {},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_workspace = type("WorkspaceStub", (), {"model_dump": lambda self, mode="json": workspace_payload})()
    mock_workspace_service.get_workspace.return_value = mock_workspace

    chat_stub = type(
        "ChatStub",
        (),
        {
            "id": "chat_1",
            "workspace_id": "ws_1",
            "messages": [
                type("Msg", (), {"id": 42, "role": "assistant", "content": "请把这段设计沉淀成结构化笔记"})(),
            ],
        },
    )()

    created_note = Note(
        workspace_id="ws_1",
        title="结构化笔记",
        summary="保存为带标签和回链的工作区笔记。",
        content="请把这段设计沉淀成结构化笔记",
        tags=["笔记", "工作区"],
        note_type="insight",
        capture_type="chat_capture",
        source_session_id="chat_1",
        source_message_id=42,
        source_message_ids=[42],
        source_metadata={"captured_from": "assistant_message"},
    )

    with patch("app.api.workspaces.chat_service") as mock_chat_service, patch(
        "app.api.workspaces.notebook_service"
    ) as mock_notebook_service, patch(
        "app.api.workspaces.generate_note_enrichment",
        new=AsyncMock(return_value={
            "title": "AI 结构化笔记",
            "summary": "自动补全摘要和标签。",
            "tags": ["工作区", "回链"],
            "note_type": "insight",
        }),
    ):
        mock_chat_service.get_chat.return_value = chat_stub
        mock_notebook_service.create_note.return_value = created_note
        mock_workspace_service.build_note_promotion_hint.return_value = {
            "eligible": True,
            "state": "ready",
            "memory_type": "project_fact",
            "confidence": 0.72,
        }

        response = client.post(
            "/api/workspaces/ws_1/notes/from-message",
            json={
                "chat_id": "chat_1",
                "message_id": 42,
                "source_ids": ["src_1"],
                "citation_refs": [{"source_id": "src_1"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["title"] == "结构化笔记"
    assert response.json()["promotion_hint"]["state"] == "ready"
    mock_notebook_service.create_note.assert_called_once()
    kwargs = mock_notebook_service.create_note.call_args.kwargs
    assert kwargs["workspace_id"] == "ws_1"
    assert kwargs["summary"] == "自动补全摘要和标签。"
    assert kwargs["tags"] == ["工作区", "回链"]
    assert kwargs["note_type"] == "insight"
    assert kwargs["capture_type"] == "chat_capture"
    assert kwargs["source_session_id"] == "chat_1"
    assert kwargs["source_message_id"] == 42
    assert kwargs["source_message_ids"] == [42]
    assert kwargs["source_metadata"]["captured_from"] == "assistant_message"
    mock_workspace_service.build_note_promotion_hint.assert_called_once_with("ws_1", note_id=created_note.id)
    mock_workspace_service.create_source.assert_called_once()


def test_suggest_memory_candidate_from_note(client, mock_workspace_service):
    payload = {
        "id": "cand_1",
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "title": "默认中文输出",
        "content": "默认使用中文回复。",
        "status": "pending",
        "score": 0.82,
        "suggested_action": "create_new",
        "conflict_memory_id": None,
        "source_session_id": "chat_1",
        "source_message_id": 42,
        "reviewed_at": None,
        "candidate_metadata": {"note_id": "note_1", "suggested_from": "workspace_note"},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_candidate = type("WorkspaceMemoryCandidateStub", (), {"model_dump": lambda self, mode="json": payload})()
    mock_workspace_service.suggest_memory_candidate_from_note.return_value = mock_candidate

    response = client.post("/api/workspaces/ws_1/notes/note_1/memory-candidates")

    assert response.status_code == 200
    assert response.json()["id"] == "cand_1"
    mock_workspace_service.suggest_memory_candidate_from_note.assert_called_once_with(
        "ws_1",
        note_id="note_1",
    )


def test_list_workspace_memory(client, mock_workspace_service):
    memory_payload = {
        "id": "mem_1",
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "title": "Default Chinese",
        "content": "Reply in Chinese by default.",
        "status": "active",
        "confidence": 0.9,
        "created_by": "user",
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "last_used_at": None,
        "memory_metadata": {"source_ids": ["src_1"]},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_memory = type("WorkspaceMemoryStub", (), {"model_dump": lambda self, mode="json": memory_payload})()
    mock_workspace_service.list_memories.return_value = [mock_memory]

    response = client.get("/api/workspaces/ws_1/memory")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "mem_1"
    mock_workspace_service.list_memories.assert_called_once_with("ws_1", include_disabled=True)


def test_create_workspace_memory(client, mock_workspace_service):
    memory_payload = {
        "id": "mem_1",
        "workspace_id": "ws_1",
        "memory_type": "decision",
        "scope_type": "project",
        "scope_ref": "ws_1",
        "title": "Use Postgres",
        "content": "The workspace default DB is Postgres + pgvector.",
        "status": "active",
        "confidence": 0.8,
        "created_by": "user",
        "why_saved": "这是当前项目的长期架构决策。",
        "pinned": True,
        "editable": True,
        "revocable": True,
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "last_used_at": None,
        "expires_at": "2026-12-31T00:00:00Z",
        "memory_metadata": {"source_ids": ["src_1"]},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_memory = type("WorkspaceMemoryStub", (), {"model_dump": lambda self, mode="json": memory_payload})()
    mock_workspace_service.create_memory.return_value = mock_memory

    response = client.post(
        "/api/workspaces/ws_1/memory",
        json={
            "memory_type": "decision",
            "scope_type": "project",
            "scope_ref": "ws_1",
            "title": "Use Postgres",
            "content": "The workspace default DB is Postgres + pgvector.",
            "status": "active",
            "confidence": 0.8,
            "created_by": "user",
            "why_saved": "这是当前项目的长期架构决策。",
            "pinned": True,
            "editable": True,
            "revocable": True,
            "source_session_id": "chat_1",
            "source_message_id": 4,
            "expires_at": "2026-12-31T00:00:00Z",
            "memory_metadata": {"source_ids": ["src_1"]},
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "mem_1"
    mock_workspace_service.create_memory.assert_called_once_with(
        "ws_1",
        memory_type="decision",
        scope_type="project",
        scope_ref="ws_1",
        title="Use Postgres",
        content="The workspace default DB is Postgres + pgvector.",
        status="active",
        confidence=0.8,
        created_by="user",
        why_saved="这是当前项目的长期架构决策。",
        pinned=True,
        editable=True,
        revocable=True,
        source_session_id="chat_1",
        source_message_id=4,
        supersedes_memory_id=None,
        expires_at="2026-12-31T00:00:00Z",
        memory_metadata={"source_ids": ["src_1"]},
    )


def test_suggest_workspace_memory_from_message(client, mock_workspace_service):
    draft_payload = {
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "title": "Default Chinese",
        "content": "Reply in Chinese by default.",
        "confidence": 0.7,
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "memory_metadata": {"source_ids": ["src_1"]},
    }
    mock_draft = type("WorkspaceMemoryDraftStub", (), {"model_dump": lambda self, mode="json": draft_payload})()
    mock_workspace_service.suggest_memory_from_message.return_value = mock_draft

    response = client.post(
        "/api/workspaces/ws_1/memory/suggest-from-message",
        json={"chat_id": "chat_1", "message_id": 4, "source_ids": ["src_1"], "citation_refs": []},
    )

    assert response.status_code == 200
    assert response.json()["memory_type"] == "preference"
    mock_workspace_service.suggest_memory_from_message.assert_called_once_with(
        "ws_1",
        chat_id="chat_1",
        message_id=4,
        source_ids=["src_1"],
        citation_refs=[],
    )


def test_list_workspace_memory_candidates(client, mock_workspace_service):
    candidate_payload = {
        "id": "cand_1",
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "title": "默认中文输出",
        "content": "默认用中文输出，先给结论。",
        "status": "pending",
        "score": 0.82,
        "suggested_action": "replace_existing",
        "conflict_memory_id": "mem_1",
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "reviewed_at": None,
        "candidate_metadata": {"score_reasons": ["High-value durable memory type."]},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_candidate = type("WorkspaceMemoryCandidateStub", (), {"model_dump": lambda self, mode="json": candidate_payload})()
    mock_workspace_service.list_memory_candidates.return_value = [mock_candidate]

    response = client.get("/api/workspaces/ws_1/memory-candidates")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "cand_1"
    mock_workspace_service.list_memory_candidates.assert_called_once_with("ws_1", include_reviewed=False)


def test_suggest_workspace_memory_candidate_from_message(client, mock_workspace_service):
    candidate_payload = {
        "id": "cand_1",
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "title": "默认中文输出",
        "content": "默认用中文输出，先给结论。",
        "status": "pending",
        "score": 0.82,
        "suggested_action": "replace_existing",
        "conflict_memory_id": "mem_1",
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "reviewed_at": None,
        "candidate_metadata": {"score_reasons": ["High-value durable memory type."]},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_candidate = type("WorkspaceMemoryCandidateStub", (), {"model_dump": lambda self, mode="json": candidate_payload})()
    mock_workspace_service.suggest_memory_candidate_from_message.return_value = mock_candidate

    response = client.post(
        "/api/workspaces/ws_1/memory-candidates/suggest-from-message",
        json={"chat_id": "chat_1", "message_id": 4, "source_ids": ["src_1"], "citation_refs": []},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "cand_1"
    mock_workspace_service.suggest_memory_candidate_from_message.assert_called_once_with(
        "ws_1",
        chat_id="chat_1",
        message_id=4,
        source_ids=["src_1"],
        citation_refs=[],
    )


def test_approve_workspace_memory_candidate(client, mock_workspace_service):
    memory_payload = {
        "id": "mem_2",
        "workspace_id": "ws_1",
        "memory_type": "preference",
        "scope_type": "user",
        "scope_ref": None,
        "title": "默认中文输出",
        "content": "默认用中文输出，先给结论。",
        "status": "active",
        "confidence": 0.82,
        "created_by": "user",
        "why_saved": "这是用户稳定表达偏好。",
        "pinned": True,
        "editable": True,
        "revocable": True,
        "source_session_id": "chat_1",
        "source_message_id": 4,
        "supersedes_memory_id": "mem_1",
        "last_used_at": None,
        "expires_at": None,
        "memory_metadata": {"approved_from_candidate_id": "cand_1"},
        "created_at": "2026-06-03T00:00:00Z",
        "updated_at": "2026-06-03T00:00:00Z",
    }
    mock_memory = type("WorkspaceMemoryStub", (), {"model_dump": lambda self, mode="json": memory_payload})()
    mock_workspace_service.approve_memory_candidate.return_value = mock_memory

    response = client.post(
        "/api/workspaces/ws_1/memory-candidates/cand_1/approve",
        json={
            "approval_mode": "replace_existing",
            "target_memory_id": "mem_1",
            "memory_type": "preference",
            "scope_type": "user",
            "why_saved": "这是用户稳定表达偏好。",
            "pinned": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "mem_2"
    mock_workspace_service.approve_memory_candidate.assert_called_once_with(
        "ws_1",
        "cand_1",
        approval_mode="replace_existing",
        target_memory_id="mem_1",
        memory_type="preference",
        scope_type="user",
        scope_ref=None,
        title=None,
        content=None,
        confidence=None,
        why_saved="这是用户稳定表达偏好。",
        expires_at=None,
        pinned=True,
    )


def test_reject_workspace_memory_candidate(client, mock_workspace_service):
    mock_workspace_service.reject_memory_candidate.return_value = True

    response = client.post(
        "/api/workspaces/ws_1/memory-candidates/cand_1/reject",
        json={"reason": "Not durable enough"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_workspace_service.reject_memory_candidate.assert_called_once_with(
        "ws_1",
        "cand_1",
        reason="Not durable enough",
    )


def test_bulk_update_workspace_memory_status(client, mock_workspace_service):
    mock_workspace_service.bulk_update_memory_status_by_type.return_value = 3

    response = client.post(
        "/api/workspaces/ws_1/memory/bulk-status",
        json={"memory_type": "historical_conclusion", "status": "disabled"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success", "updated_count": 3}
    mock_workspace_service.bulk_update_memory_status_by_type.assert_called_once_with(
        "ws_1",
        memory_type="historical_conclusion",
        status="disabled",
    )


def test_create_research_artifact(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_research",
        "workspace_id": "ws_1",
        "artifact_type": "research_report",
        "title": "What changed?",
        "source_session_id": "chat_1",
        "source_message_id": 10,
        "action_state_id": None,
        "artifact_path": None,
        "content_ref": "research:What changed?",
        "artifact_metadata": {
            "question": "What changed?",
            "source_ids": ["src_1"],
            "mode": "require_sources",
            "summary": "Summary",
            "findings": [],
            "open_questions": [],
            "export_paths": [],
        },
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_source = object()
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": artifact_payload})()
    mock_workspace_service.get_source.return_value = mock_source
    mock_workspace_service.create_artifact.return_value = mock_artifact

    response = client.post(
        "/api/workspaces/ws_1/research-artifacts",
        json={
            "question": "What changed?",
            "summary": "Summary",
            "source_ids": ["src_1"],
            "mode": "require_sources",
            "source_session_id": "chat_1",
            "source_message_id": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["artifact_type"] == "research_report"


def test_create_research_artifact_rejects_unknown_source(client, mock_workspace_service):
    mock_workspace_service.get_source.return_value = None

    response = client.post(
        "/api/workspaces/ws_1/research-artifacts",
        json={"question": "What changed?", "source_ids": ["missing"]},
    )

    assert response.status_code == 400


def test_update_workspace(client, mock_workspace_service):
    payload = {
        "id": "ws_1",
        "name": "Research V2",
        "description": "updated",
        "default_agent_id": None,
        "source_policy": {},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_workspace = type("WorkspaceStub", (), {"model_dump": lambda self, mode="json": payload})()
    mock_workspace_service.update_workspace.return_value = mock_workspace

    response = client.put("/api/workspaces/ws_1", json={"name": "Research V2", "description": "updated"})

    assert response.status_code == 200
    assert response.json()["name"] == "Research V2"


def test_update_workspace_artifact(client, mock_workspace_service):
    payload = {
        "id": "art_1",
        "workspace_id": "ws_1",
        "artifact_type": "generated_file",
        "title": "brief-v2.docx",
        "source_session_id": "chat_1",
        "source_message_id": None,
        "action_state_id": 12,
        "artifact_path": "/exports/brief.docx",
        "content_ref": "invocation-1",
        "artifact_metadata": {"download_url": "/exports/brief-v2.docx"},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": payload})()
    mock_workspace_service.update_artifact.return_value = mock_artifact

    response = client.put(
        "/api/workspaces/ws_1/artifacts/art_1",
        json={"artifact_type": "generated_file", "title": "brief-v2.docx"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "brief-v2.docx"


def test_update_workspace_memory_conflict_when_locked(client, mock_workspace_service):
    mock_workspace_service.update_memory.side_effect = ValueError("memory_not_editable")

    response = client.put(
        "/api/workspaces/ws_1/memory/mem_1",
        json={"content": "Attempted update"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Workspace memory is locked for editing"


def test_approve_workspace_memory_candidate_conflict_when_target_protected(client, mock_workspace_service):
    mock_workspace_service.approve_memory_candidate.side_effect = ValueError("memory_not_revocable")

    response = client.post(
        "/api/workspaces/ws_1/memory-candidates/cand_1/approve",
        json={"approval_mode": "replace_existing", "target_memory_id": "mem_1"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Workspace memory cannot be deleted or replaced"


def test_delete_workspace_conflict(client, mock_workspace_service):
    mock_workspace_service.delete_workspace.side_effect = ValueError("workspace_not_empty")

    response = client.delete("/api/workspaces/ws_1")

    assert response.status_code == 409


def test_delete_workspace_source_not_found(client, mock_workspace_service):
    mock_workspace_service.delete_source.return_value = False

    response = client.delete("/api/workspaces/ws_1/sources/src_missing")

    assert response.status_code == 404


def test_delete_workspace_artifact_not_found(client, mock_workspace_service):
    mock_workspace_service.delete_artifact.return_value = False

    response = client.delete("/api/workspaces/ws_1/artifacts/art_missing")

    assert response.status_code == 404


def test_delete_workspace_memory_conflict_when_protected(client, mock_workspace_service):
    mock_workspace_service.delete_memory.side_effect = ValueError("memory_not_revocable")

    response = client.delete("/api/workspaces/ws_1/memory/mem_1")

    assert response.status_code == 409
    assert response.json()["detail"] == "Workspace memory cannot be deleted or replaced"
