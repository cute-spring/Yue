from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.browser import router
from app.mcp.builtin.browser import BrowserReadTool
from app.services.browser_session_service import browser_session_service
from app.services.browser_policy_service import browser_policy_service


@pytest.fixture(autouse=True)
def reset_browser_sessions():
    browser_session_service.reset_for_tests()
    browser_policy_service.replace_origins_for_tests([{ "origin": "https://app.example.com", "purpose": "business" }])
    yield
    browser_session_service.reset_for_tests()
    browser_policy_service.replace_origins_for_tests([])


@pytest.fixture
def client():
    try:
        app = FastAPI()
        app.include_router(router, prefix="/api/browser")
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def register_tab(client):
    response = client.post(
        "/api/browser/sessions/register",
        json={"tab_id": "5", "title": "Orders", "url": "https://app.example.com/orders"},
    )
    assert response.status_code == 200
    return response.json()


def upload_current_snapshot(client, session):
    response = client.post(
        f"/api/browser/sessions/{session['id']}/snapshot",
        headers={"X-Yue-Browser-Token": session["extension_token"]},
        json={"title": "Orders", "url": "https://app.example.com/orders", "visible_text": "Save changes"},
    )
    assert response.status_code == 200


def test_browser_api_registers_snapshot_and_never_lists_extension_token(client):
    session = register_tab(client)
    snapshot_response = client.post(
        f"/api/browser/sessions/{session['id']}/snapshot",
        headers={"X-Yue-Browser-Token": session["extension_token"]},
        json={
            "title": "Orders",
            "url": "https://app.example.com/orders?period=this-month",
            "visible_text": "Order count: 8",
        },
    )

    assert snapshot_response.status_code == 200
    listed = client.get("/api/browser/sessions")
    assert listed.status_code == 200
    assert listed.json()[0]["has_snapshot"] is True
    assert "extension_token" not in listed.json()[0]


def test_browser_api_rejects_snapshot_without_extension_token(client):
    session = register_tab(client)

    response = client.post(
        f"/api/browser/sessions/{session['id']}/snapshot",
        json={"title": "Orders", "url": "https://app.example.com/orders", "visible_text": "Order count: 8"},
    )

    assert response.status_code == 403


def test_browser_api_returns_pending_submit_then_allows_explicit_approval(client):
    session = client.post(
        "/api/browser/sessions/register",
        json={
            "tab_id": "5",
            "title": "Expense form",
            "url": "https://app.example.com/expense",
            "authorization_mode": "session_auto",
        },
    ).json()
    upload_current_snapshot(client, session)

    pending = client.post(f"/api/browser/sessions/{session['id']}/actions", json={"action": "submit"})

    assert pending.status_code == 202
    assert pending.json()["status"] == "awaiting_approval"
    action_id = pending.json()["action"]["id"]
    approved = client.post(
        f"/api/browser/sessions/{session['id']}/actions/{action_id}/decision",
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "queued"


def test_browser_api_lists_pending_actions_without_revealing_fill_values(client):
    session = register_tab(client)
    upload_current_snapshot(client, session)
    action = client.post(
        f"/api/browser/sessions/{session['id']}/actions",
        json={"action": "fill", "target": "Expense description", "value": "Private taxi receipt"},
    )

    assert action.status_code == 202
    listed = client.get(f"/api/browser/sessions/{session['id']}/actions")

    assert listed.status_code == 200
    assert listed.json()[0]["target"] == "Expense description"
    assert "value" not in listed.json()[0]


def test_browser_api_reconciles_an_uncertain_submitted_command(client):
    session = register_tab(client)
    upload_current_snapshot(client, session)
    pending = client.post(
        f"/api/browser/sessions/{session['id']}/actions",
        json={"action": "click", "target": "Save changes"},
    ).json()["action"]
    client.post(
        f"/api/browser/sessions/{session['id']}/actions/{pending['id']}/decision",
        json={"approved": True},
    )
    dispatched = client.get(
        f"/api/browser/sessions/{session['id']}/commands/next",
        headers={"X-Yue-Browser-Token": session["extension_token"]},
    ).json()

    uncertain = client.post(
        f"/api/browser/sessions/{session['id']}/actions/{dispatched['id']}/result",
        headers={"X-Yue-Browser-Token": session["extension_token"]},
        json={"succeeded": None, "result": {"error": "The browser response was lost."}},
    )

    assert uncertain.status_code == 200
    assert uncertain.json()["status"] == "needs_reconciliation"
    reconciled = client.post(
        f"/api/browser/sessions/{session['id']}/actions/{dispatched['id']}/reconciliation",
        json={"outcome": "not_applied"},
    )
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_browser_read_tool_uses_only_the_session_bound_in_context():
    session, token = browser_session_service.register_tab(
        tab_id="5",
        title="Orders",
        url="https://app.example.com/orders",
    )
    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Orders",
        url="https://app.example.com/orders",
        visible_text="Order count: 8",
    )

    result = await BrowserReadTool().execute(SimpleNamespace(deps={"browser_session_id": session.id}), {})

    assert '"ok": true' in result
    assert 'Order count: 8' in result


def test_browser_policy_api_requires_local_request_then_approval(client):
    request = client.post(
        "/api/browser/policy/origin-requests",
        json={"origin": "https://login.example-idp.com", "purpose": "sso_handoff"},
    )
    assert request.status_code == 202
    assert request.json()["status"] == "awaiting_approval"

    before = client.get("/api/browser/policy/origins")
    assert before.json() == [{"origin": "https://app.example.com", "purpose": "business", "approved_at": "test"}]

    approved = client.post(
        f"/api/browser/policy/origin-requests/{request.json()['id']}/decision",
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert client.get("/api/browser/policy/origins").json()[1]["purpose"] == "sso_handoff"


def test_browser_policy_api_rejects_wildcard_and_paths(client):
    response = client.post(
        "/api/browser/policy/origin-requests",
        json={"origin": "https://*.example.com/path", "purpose": "business"},
    )
    assert response.status_code == 400
