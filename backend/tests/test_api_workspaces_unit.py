from datetime import datetime, timezone
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.chat import Workspace as WorkspaceModel
from app.models.chat import WorkspaceMemoryCandidate as WorkspaceMemoryCandidateModel
from app.models.chat import WorkspaceMemoryCard as WorkspaceMemoryCardModel
from app.services.notebook_service import Note

from app.api.workspaces import router
from app.services.workspace_understanding_service import (
    WORKSPACE_UNDERSTANDING_GROUPS,
    WorkspaceUnderstandingGroup,
    WorkspaceUnderstandingItem,
    WorkspaceUnderstandingSummary,
)


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


@pytest.fixture
def mock_workspace_understanding_service():
    with patch("app.api.workspaces.workspace_understanding_service") as mock:
        yield mock


@pytest.fixture
def api_temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue_api.db")
    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    with patch("app.services.workspace_understanding_service.SessionLocal", testing_session_local):
        yield testing_session_local

    test_engine.dispose()
    shutil.rmtree(temp_dir)


def test_list_workspaces(client, mock_workspace_service):
    mock_workspace_service.list_workspaces.return_value = []

    response = client.get("/api/workspaces/")

    assert response.status_code == 200
    assert response.json() == []


def test_get_workspace_not_found(client, mock_workspace_service):
    mock_workspace_service.get_workspace.return_value = None

    response = client.get("/api/workspaces/missing")

    assert response.status_code == 404


def test_get_workspace_understanding_returns_summary_contract(client, mock_workspace_understanding_service):
    summary = WorkspaceUnderstandingSummary(
        workspace_id="ws_1",
        groups=[
            WorkspaceUnderstandingGroup(
                group=definition.key,
                label=definition.label,
                total_count=1 if definition.key == "decisions" else 0,
                active_count=1 if definition.key == "decisions" else 0,
                pending_count=0,
                representative_items=[
                    WorkspaceUnderstandingItem(
                        id="mem_1",
                        kind="memory",
                        title="Use fixed groups",
                        content="Workspace Understanding uses fixed groups.",
                        status="active",
                        memory_type="decision",
                        source_session_id="chat_1",
                        source_message_id=42,
                        confidence=0.9,
                        updated_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
                    )
                ] if definition.key == "decisions" else [],
            )
            for definition in WORKSPACE_UNDERSTANDING_GROUPS
        ],
        applied_user_memory_preview=[],
    )
    mock_workspace_understanding_service.build_summary.return_value = summary

    response = client.get("/api/workspaces/ws_1/understanding")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "ws_1"
    assert [group["group"] for group in payload["groups"]] == [group.key for group in WORKSPACE_UNDERSTANDING_GROUPS]
    decisions_group = next(group for group in payload["groups"] if group["group"] == "decisions")
    assert decisions_group["representative_items"][0]["title"] == "Use fixed groups"
    assert decisions_group["representative_items"][0]["kind"] == "memory"
    assert payload["applied_user_memory_preview"] == []
    mock_workspace_understanding_service.build_summary.assert_called_once_with("ws_1")


def test_get_workspace_understanding_not_found(client, mock_workspace_understanding_service):
    mock_workspace_understanding_service.build_summary.return_value = None

    response = client.get("/api/workspaces/missing/understanding")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found"


def test_get_workspace_understanding_uses_service_and_database(client, api_temp_db):
    now = datetime(2026, 9, 7, tzinfo=timezone.utc)
    with api_temp_db() as db:
        db.add(
            WorkspaceModel(
                id="ws_1",
                name="Workspace Understanding",
                description=None,
                default_agent_id=None,
                source_policy_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            WorkspaceMemoryCardModel(
                id="mem_1",
                workspace_id="ws_1",
                memory_type="decision",
                scope_type="workspace",
                scope_ref="ws_1",
                title="Use fixed groups",
                content="Keep the Workspace Understanding groups predictable.",
                status="active",
                confidence=0.88,
                created_by="user",
                memory_metadata_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            WorkspaceMemoryCandidateModel(
                id="cand_1",
                workspace_id="ws_1",
                memory_type="open_question",
                scope_type="workspace",
                scope_ref="ws_1",
                title="Choose detector type",
                content="Should high-signal detection start rule-based or LLM-assisted?",
                status="pending",
                score=0.74,
                suggested_action="create_new",
                candidate_metadata_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    response = client.get("/api/workspaces/ws_1/understanding")

    assert response.status_code == 200
    payload = response.json()
    by_group = {group["group"]: group for group in payload["groups"]}
    assert [group["group"] for group in payload["groups"]] == [group.key for group in WORKSPACE_UNDERSTANDING_GROUPS]
    assert by_group["decisions"]["total_count"] == 1
    assert by_group["decisions"]["active_count"] == 1
    assert by_group["decisions"]["representative_items"][0]["id"] == "mem_1"
    assert by_group["open_questions"]["total_count"] == 0
    assert by_group["open_questions"]["pending_count"] == 1
    assert by_group["open_questions"]["representative_items"][0]["id"] == "cand_1"


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
            "assumptions": ["Assume current workspace sources are sufficient."],
            "next_actions": ["Review unsupported claims."],
            "source_session_id": "chat_1",
            "source_message_id": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["artifact_type"] == "research_report"
    metadata = mock_workspace_service.create_artifact.call_args.kwargs["artifact_metadata"]
    assert metadata["evidence_contract"]["claim_states"]["source_supported"] == "Source-supported"
    assert metadata["evidence_contract"]["source_scope_preview"] == {
        "mode": "require_sources",
        "source_ids": ["src_1"],
        "source_count": 1,
        "unavailable_source_ids": [],
        "citation_requirement": "required",
    }
    assert metadata["assumptions"] == ["Assume current workspace sources are sufficient."]
    assert metadata["next_actions"] == ["Review unsupported claims."]
    assert metadata["durable_memory_write"] == "not_performed"


def test_create_research_artifact_tracks_cited_and_unsupported_claims(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_research",
        "workspace_id": "ws_1",
        "artifact_type": "research_report",
        "title": "What is supported?",
        "source_session_id": None,
        "source_message_id": None,
        "action_state_id": None,
        "artifact_path": None,
        "content_ref": "research:What is supported?",
        "artifact_metadata": {},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_workspace_service.get_source.return_value = object()
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": artifact_payload})()
    mock_workspace_service.create_artifact.return_value = mock_artifact

    response = client.post(
        "/api/workspaces/ws_1/research-artifacts",
        json={
            "question": "What is supported?",
            "source_ids": ["src_1"],
            "findings": [
                {
                    "claim": "Cited claim",
                    "evidence_state": "source_supported",
                    "citations": [{"source_id": "src_1", "quote": "Evidence"}],
                },
                {"claim": "Unsupported claim", "evidence_state": "unsupported"},
            ],
        },
    )

    assert response.status_code == 200
    metadata = mock_workspace_service.create_artifact.call_args.kwargs["artifact_metadata"]
    assert metadata["findings"][0]["evidence_state"] == "source_supported"
    assert metadata["findings"][1]["evidence_state"] == "unsupported"
    assert metadata["citation_warnings"] == []


def test_create_research_artifact_warns_for_missing_evidence(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_research",
        "workspace_id": "ws_1",
        "artifact_type": "research_report",
        "title": "What is missing?",
        "source_session_id": None,
        "source_message_id": None,
        "action_state_id": None,
        "artifact_path": None,
        "content_ref": "research:What is missing?",
        "artifact_metadata": {},
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    mock_workspace_service.create_artifact.return_value = type(
        "WorkspaceArtifactStub",
        (),
        {"model_dump": lambda self, mode="json": artifact_payload},
    )()

    response = client.post(
        "/api/workspaces/ws_1/research-artifacts",
        json={
            "question": "What is missing?",
            "mode": "require_sources",
            "findings": [{"claim": "Needs citation", "evidence_state": "source_supported"}],
            "missing_evidence": ["No source confirms launch date."],
            "unavailable_source_ids": ["src_missing"],
        },
    )

    assert response.status_code == 200
    metadata = mock_workspace_service.create_artifact.call_args.kwargs["artifact_metadata"]
    assert metadata["missing_evidence"] == ["No source confirms launch date."]
    assert metadata["unavailable_source_ids"] == ["src_missing"]
    assert metadata["citation_warnings"] == ["Finding 1 is source-supported but has no citation."]


def test_create_research_artifact_rejects_unknown_source(client, mock_workspace_service):
    mock_workspace_service.get_source.return_value = None

    response = client.post(
        "/api/workspaces/ws_1/research-artifacts",
        json={"question": "What changed?", "source_ids": ["missing"]},
    )

    assert response.status_code == 400


def test_create_chart_artifact_from_message(client, mock_workspace_service):
    artifact_payload = {
        "id": "art_chart",
        "workspace_id": "ws_1",
        "artifact_type": "chart",
        "title": "Revenue by Region",
        "source_session_id": "chat_1",
        "source_message_id": 10,
        "action_state_id": None,
        "artifact_path": None,
        "content_ref": "chart:chat_1:10:chart_1",
        "artifact_metadata": {"artifact_id": "chart_1"},
        "created_at": "2026-07-24T00:00:00Z",
        "updated_at": "2026-07-24T00:00:00Z",
    }
    mock_workspace_service.get_workspace.return_value = object()
    mock_artifact = type("WorkspaceArtifactStub", (), {"model_dump": lambda self, mode="json": artifact_payload})()
    mock_workspace_service.create_artifact.return_value = mock_artifact

    with patch("app.api.workspaces.chat_service") as mock_chat_service:
        mock_chat_service.get_chat.return_value = SimpleNamespace(
            id="chat_1",
            workspace_id="ws_1",
            messages=[
                SimpleNamespace(
                    id=10,
                    role="assistant",
                    chart_artifacts=[
                        {
                            "artifact_id": "chart_1",
                            "artifact_type": "chart",
                            "display_mode": "inline",
                            "assistant_turn_id": "turn_1",
                            "run_id": "run_1",
                            "sequence": 4,
                            "chart": {
                                "version": 1,
                                "kind": "chart",
                                "chartType": "bar",
                                "title": "Revenue by Region",
                                "data": [{"region": "APAC", "revenue": 120}],
                                "encoding": {
                                    "x": {"field": "region", "type": "category"},
                                    "y": {"field": "revenue", "type": "number"},
                                },
                            },
                        }
                    ],
                )
            ],
        )

        response = client.post(
            "/api/workspaces/ws_1/charts/from-message",
            json={"chat_id": "chat_1", "message_id": 10, "artifact_id": "chart_1"},
        )

    assert response.status_code == 200
    assert response.json()["artifact_type"] == "chart"
    mock_workspace_service.create_artifact.assert_called_once()
    _, kwargs = mock_workspace_service.create_artifact.call_args
    assert kwargs["artifact_type"] == "chart"
    assert kwargs["title"] == "Revenue by Region"
    assert kwargs["source_session_id"] == "chat_1"
    assert kwargs["source_message_id"] == 10
    assert kwargs["artifact_metadata"]["chart"]["chartType"] == "bar"


def test_create_chart_artifact_from_message_rejects_wrong_workspace_chat(client, mock_workspace_service):
    mock_workspace_service.get_workspace.return_value = object()
    with patch("app.api.workspaces.chat_service") as mock_chat_service:
        mock_chat_service.get_chat.return_value = SimpleNamespace(id="chat_1", workspace_id="ws_other", messages=[])

        response = client.post(
            "/api/workspaces/ws_1/charts/from-message",
            json={"chat_id": "chat_1", "artifact_id": "chart_1"},
        )

    assert response.status_code == 404


def test_create_chart_artifact_from_message_rejects_missing_chart(client, mock_workspace_service):
    mock_workspace_service.get_workspace.return_value = object()
    with patch("app.api.workspaces.chat_service") as mock_chat_service:
        mock_chat_service.get_chat.return_value = SimpleNamespace(
            id="chat_1",
            workspace_id="ws_1",
            messages=[SimpleNamespace(id=10, role="assistant", chart_artifacts=[])],
        )

        response = client.post(
            "/api/workspaces/ws_1/charts/from-message",
            json={"chat_id": "chat_1", "message_id": 10, "artifact_id": "chart_1"},
        )

    assert response.status_code == 404


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
