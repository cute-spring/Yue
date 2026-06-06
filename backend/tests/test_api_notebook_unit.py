import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.api.notebook import router
from app.services.notebook_service import Note

@pytest.fixture
def client():
    try:
        app = FastAPI()
        app.include_router(router, prefix="/api/notebook")
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")

@pytest.fixture
def mock_notebook_service():
    with patch("app.api.notebook.notebook_service") as mock:
        yield mock

def test_list_notes(client, mock_notebook_service):
    mock_note = Note(title="T1", content="C1")
    mock_notebook_service.list_notes.return_value = [mock_note]
    
    response = client.get("/api/notebook/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "T1"


def test_list_notes_with_filters(client, mock_notebook_service):
    mock_notebook_service.list_notes.return_value = []

    response = client.get(
        "/api/notebook/?workspace_id=ws_1&tags=memory,workspace&note_type=preference&capture_type=chat_capture&source_session_id=chat_1&include_promotion_hints=true"
    )

    assert response.status_code == 200
    mock_notebook_service.list_notes.assert_called_once_with(
        workspace_id="ws_1",
        tags=["memory", "workspace"],
        note_type="preference",
        capture_type="chat_capture",
        source_session_id="chat_1",
    )


def test_list_notes_can_attach_promotion_hints(client, mock_notebook_service):
    mock_note = Note(id="note_1", workspace_id="ws_1", title="T1", content="C1")
    mock_notebook_service.list_notes.return_value = [mock_note]

    with patch("app.api.notebook.workspace_service") as mock_workspace_service:
        mock_workspace_service.build_note_promotion_hint.return_value = {
            "eligible": True,
            "state": "ready",
            "reason_summary": "Looks durable enough to review as workspace memory.",
        }
        response = client.get("/api/notebook/?workspace_id=ws_1&include_promotion_hints=true")

    assert response.status_code == 200
    assert response.json()[0]["promotion_hint"]["state"] == "ready"
    mock_workspace_service.build_note_promotion_hint.assert_called_once_with("ws_1", note_id="note_1")

def test_get_note_success(client, mock_notebook_service):
    mock_note = Note(title="T1", content="C1")
    mock_notebook_service.get_note.return_value = mock_note
    
    response = client.get("/api/notebook/123")
    assert response.status_code == 200
    assert response.json()["title"] == "T1"

def test_get_note_not_found(client, mock_notebook_service):
    mock_notebook_service.get_note.return_value = None
    
    response = client.get("/api/notebook/non-existent")
    assert response.status_code == 404

def test_create_note(client, mock_notebook_service):
    mock_note = Note(title="New", content="Content")
    mock_notebook_service.create_note.return_value = mock_note

    with patch("app.api.notebook.generate_note_enrichment", new=AsyncMock(return_value={
        "title": "AI Note",
        "summary": "自动摘要",
        "tags": ["记忆", "笔记"],
        "note_type": "summary",
    })), patch("app.api.notebook.workspace_service") as mock_workspace_service:
        mock_workspace_service.build_note_promotion_hint.return_value = {"eligible": False, "state": "note_only"}
        response = client.post("/api/notebook/", json={"content": "Content"})

    assert response.status_code == 200
    assert response.json()["title"] == "New"
    mock_notebook_service.create_note.assert_called_once_with(
        "AI Note",
        "Content",
        workspace_id=None,
        summary="自动摘要",
        tags=["记忆", "笔记"],
        note_type="summary",
        capture_type="manual",
        status="saved",
        source_session_id=None,
        source_message_id=None,
        source_message_ids=[],
        citation_refs=[],
        source_metadata={},
        promoted_memory_id=None,
    )

def test_update_note_success(client, mock_notebook_service):
    mock_note = Note(title="Updated", content="Updated Content")
    existing_note = Note(title="Existing", content="Existing Content", summary="旧摘要", source_metadata={"captured_from": "manual"})
    mock_notebook_service.get_note.return_value = existing_note
    mock_notebook_service.update_note.return_value = mock_note

    with patch("app.api.notebook.generate_note_enrichment", new=AsyncMock(return_value={
        "summary": "新的自动摘要",
        "tags": ["工作区", "回链"],
        "note_type": "insight",
    })), patch("app.api.notebook.workspace_service") as mock_workspace_service:
        mock_workspace_service.build_note_promotion_hint.return_value = {"eligible": False, "state": "note_only"}
        response = client.put("/api/notebook/123", json={"content": "Updated Content"})

    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    mock_notebook_service.update_note.assert_called_once_with(
        "123",
        None,
        "Updated Content",
        summary="新的自动摘要",
        tags=["工作区", "回链"],
        note_type="insight",
        capture_type=None,
        status=None,
        workspace_id=None,
        source_session_id=None,
        source_message_id=None,
        source_message_ids=None,
        citation_refs=None,
        source_metadata=None,
        promoted_memory_id=None,
    )

def test_update_note_not_found(client, mock_notebook_service):
    mock_notebook_service.get_note.return_value = None
    
    response = client.put("/api/notebook/non-existent", json={"title": "fail"})
    assert response.status_code == 404

def test_delete_note_success(client, mock_notebook_service):
    mock_notebook_service.delete_note.return_value = True
    
    response = client.delete("/api/notebook/123")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_delete_note_not_found(client, mock_notebook_service):
    mock_notebook_service.delete_note.return_value = False
    
    response = client.delete("/api/notebook/non-existent")
    assert response.status_code == 404
