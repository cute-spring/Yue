import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import workbench_modes as workbench_modes_module


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(workbench_modes_module.router, prefix="/api/workbench-modes")
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def test_api_lists_builtin_workbench_modes(client):
    response = client.get("/api/workbench-modes")

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [
        "clarify-mode",
        "session-handoff",
        "discovery-questionnaire",
        "deep-research",
        "workspace-glossary",
        "agent-instruction-review",
    ]
    for item in data:
        assert item["presentation"] == "workbench_mode"
        assert item["workflow_status"] == "contract_only"
        assert item["visible_entry_points"]
        assert item["expected_outputs"]
        assert item["safety_boundaries"]
        assert item["routing"]["target"]
        assert item["routing"]["prompt_policy"]
        assert item["routing"]["tool_policy"]


def test_api_gets_one_builtin_workbench_mode(client):
    response = client.get("/api/workbench-modes/deep-research")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "deep-research"
    assert data["optional_shortcuts"] == ["/research"]
    assert data["shortcuts"][0]["command"] == "/research"
    assert data["shortcuts"][0]["availability"] == "manual"
    assert "source_scope_required" in data["safety_labels"]
    assert data["routing"]["tool_policy"] == "source_scoped_read_only_for_mvp"
    assert data["expected_outputs"][0]["workspace_attachment"] == "required"
    assert data["expected_outputs"][0]["provenance"] == "required"


def test_api_returns_404_for_unknown_workbench_mode(client):
    response = client.get("/api/workbench-modes/not-real")

    assert response.status_code == 404
    assert response.json()["detail"] == "workbench_mode_not_found"
