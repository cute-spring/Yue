import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import patch

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
