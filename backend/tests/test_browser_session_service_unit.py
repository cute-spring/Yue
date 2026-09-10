import pytest

from app.services.browser_session_service import (
    BrowserActionApprovalRequired,
    BrowserSessionStateError,
    BrowserSessionUnauthorized,
    browser_session_service,
)
from app.services.browser_policy_service import browser_policy_service


@pytest.fixture(autouse=True)
def reset_browser_sessions():
    browser_session_service.reset_for_tests()
    browser_policy_service.replace_origins_for_tests(
        [
            {"origin": "https://reports.example.com", "purpose": "business"},
            {"origin": "https://erp.example.com", "purpose": "business"},
            {"origin": "https://login.example-idp.com", "purpose": "sso_handoff"},
        ]
    )
    yield
    browser_session_service.reset_for_tests()
    browser_policy_service.replace_origins_for_tests([])


def register_example_tab():
    return browser_session_service.register_tab(
        tab_id="123",
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard",
    )


def test_registration_returns_secret_only_to_extension_and_public_list_redacts_it():
    session, token = register_example_tab()

    assert token
    assert "extension_token" not in browser_session_service.list_sessions()[0]
    assert browser_session_service.list_sessions()[0]["id"] == session.id


def test_snapshot_requires_extension_token_and_stays_within_authorized_origin():
    session, token = register_example_tab()

    with pytest.raises(BrowserSessionUnauthorized):
        browser_session_service.submit_snapshot(
            session_id=session.id,
            extension_token="wrong",
            title="Quarterly dashboard",
            url="https://reports.example.com/dashboard",
            visible_text="Revenue: 100",
        )

    with pytest.raises(BrowserSessionUnauthorized):
        browser_session_service.submit_snapshot(
            session_id=session.id,
            extension_token=token,
            title="Elsewhere",
            url="https://other.example.com/",
            visible_text="Should not be accepted",
        )


def test_reading_snapshot_truncates_and_resolves_chat_attachment():
    session, token = register_example_tab()
    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard?region=east",
        visible_text="x" * 800,
    )
    browser_session_service.attach_to_chat(session_id=session.id, chat_id="chat_1")

    snapshot = browser_session_service.read_snapshot(session_id=session.id, max_chars=500)

    assert snapshot["ok"] is True
    assert snapshot["truncated"] is True
    assert len(snapshot["visible_text"]) == 500
    assert browser_session_service.resolve_session_id(chat_id="chat_1", requested_session_id=None) == session.id


def test_paused_session_cannot_be_read_or_attached():
    session, token = register_example_tab()
    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard",
        visible_text="Revenue: 100",
    )
    browser_session_service.set_status(session_id=session.id, status="paused")

    with pytest.raises(BrowserSessionStateError):
        browser_session_service.read_snapshot(session_id=session.id)
    with pytest.raises(BrowserSessionStateError):
        browser_session_service.attach_to_chat(session_id=session.id, chat_id="chat_1")


def test_empty_page_snapshot_is_valid_and_readable():
    session, token = register_example_tab()

    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard",
        visible_text="",
    )

    assert browser_session_service.read_snapshot(session_id=session.id)["visible_text"] == ""


def test_session_auto_fills_but_submit_requires_explicit_approval():
    session, token = browser_session_service.register_tab(
        tab_id="123",
        title="Expense form",
        url="https://erp.example.com/expense",
        authorization_mode="session_auto",
    )

    fill = browser_session_service.request_action(
        session_id=session.id,
        action="fill",
        target="Taxi amount",
        value="42.50",
    )
    assert fill["status"] == "queued"

    with pytest.raises(BrowserActionApprovalRequired) as exc_info:
        browser_session_service.request_action(session_id=session.id, action="submit")

    pending = exc_info.value.pending_action
    assert pending["action"] == "submit"
    approved = browser_session_service.decide_action(
        session_id=session.id,
        action_id=pending["id"],
        approved=True,
    )
    assert approved["status"] == "queued"


def test_sso_handoff_policy_redacts_snapshot_after_cross_origin_navigation():
    session, token = register_example_tab()

    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Sign in",
        url="https://login.example-idp.com/sso",
        visible_text="Sign in with your company account",
    )

    assert browser_session_service.get_session(session.id).url == "https://login.example-idp.com"
    assert browser_session_service.read_snapshot(session_id=session.id)["visible_text"] == ""


def test_sso_handoff_redacts_page_identity_blocks_actions_and_disarms_auto_mode():
    session, token = browser_session_service.register_tab(
        tab_id="123",
        title="Expense form",
        url="https://erp.example.com/expense",
        authorization_mode="session_auto",
    )
    browser_session_service.submit_snapshot(
        session_id=session.id,
        extension_token=token,
        title="Sign in as alex@example.com?code=secret",
        url="https://login.example-idp.com/sso?code=secret",
        visible_text="One-time code 123456",
    )

    snapshot = browser_session_service.read_snapshot(session_id=session.id)
    assert snapshot["url"] == "https://login.example-idp.com"
    assert snapshot["title"] == "SSO handoff"
    assert browser_session_service.get_session(session.id).authorization_mode == "step_confirm"
    with pytest.raises(BrowserSessionStateError):
        browser_session_service.request_action(session_id=session.id, action="click", target="Continue")


def test_cross_origin_navigation_always_needs_approval():
    session, _ = register_example_tab()

    with pytest.raises(BrowserActionApprovalRequired) as exc_info:
        browser_session_service.request_action(
            session_id=session.id,
            action="navigate",
            target="https://erp.example.com/expense",
        )

    assert exc_info.value.pending_action["status"] == "awaiting_approval"


def test_revoked_origin_pauses_session_and_prevents_new_or_queued_actions():
    session, token = browser_session_service.register_tab(
        tab_id="123",
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard",
        authorization_mode="session_auto",
    )
    queued = browser_session_service.request_action(session_id=session.id, action="click", target="Refresh")
    browser_policy_service.replace_origins_for_tests([])

    with pytest.raises(BrowserSessionUnauthorized):
        browser_session_service.submit_snapshot(
            session_id=session.id,
            extension_token=token,
            title="Quarterly dashboard",
            url="https://reports.example.com/dashboard",
            visible_text="Revenue: 100",
        )

    assert browser_session_service.get_session(session.id).status == "paused"
    assert browser_session_service.get_session(session.id).actions[queued["id"]].status == "failed"
    with pytest.raises(BrowserSessionStateError):
        browser_session_service.request_action(session_id=session.id, action="click", target="Refresh")


def test_unapproved_redirect_pauses_session_and_cancels_queued_actions():
    session, token = browser_session_service.register_tab(
        tab_id="123",
        title="Quarterly dashboard",
        url="https://reports.example.com/dashboard",
        authorization_mode="session_auto",
    )
    queued = browser_session_service.request_action(session_id=session.id, action="click", target="Refresh")

    with pytest.raises(BrowserSessionUnauthorized):
        browser_session_service.submit_snapshot(
            session_id=session.id,
            extension_token=token,
            title="Unexpected page",
            url="https://untrusted.example.com/redirect",
            visible_text="Unexpected content",
        )

    assert browser_session_service.get_session(session.id).status == "paused"
    assert browser_session_service.get_session(session.id).actions[queued["id"]].status == "failed"


def test_registration_requires_a_locally_approved_business_origin():
    browser_policy_service.replace_origins_for_tests([])

    with pytest.raises(BrowserSessionUnauthorized):
        register_example_tab()
