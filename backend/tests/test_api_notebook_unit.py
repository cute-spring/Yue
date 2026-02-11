import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.services.notebook_service import Note

@pytest.fixture
def client():
    return TestClient(app)

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
    
    response = client.post("/api/notebook/", json={"title": "New", "content": "Content"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"

def test_update_note_success(client, mock_notebook_service):
    mock_note = Note(title="Updated", content="Updated Content")
    mock_notebook_service.update_note.return_value = mock_note
    
    response = client.put("/api/notebook/123", json={"title": "Updated", "content": "Updated Content"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_update_note_not_found(client, mock_notebook_service):
    mock_notebook_service.update_note.return_value = None
    
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
