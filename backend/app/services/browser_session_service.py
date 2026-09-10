"""Ephemeral, user-authorized browser-tab sessions.

The browser extension owns the secret that proves control of a tab. Yue only
stores a redacted session record and the latest user-authorized page snapshot.
This is deliberately separate from general web fetching: it never opens a URL
or attempts to bypass a site's authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import secrets
from threading import RLock
from typing import Any, Dict, Optional
from urllib.parse import urlsplit
from uuid import uuid4

from app.services.browser_policy_service import BrowserPolicyError, browser_policy_service


MAX_SNAPSHOT_TEXT_CHARS = 100_000
MIN_READ_CHARS = 500
MAX_READ_CHARS = 50_000


class BrowserSessionError(ValueError):
    """Base error for browser-session operations safe to return to clients."""


class BrowserSessionNotFound(BrowserSessionError):
    pass


class BrowserSessionUnauthorized(BrowserSessionError):
    pass


class BrowserSessionStateError(BrowserSessionError):
    pass


class BrowserActionApprovalRequired(BrowserSessionError):
    def __init__(self, pending_action: Dict[str, Any]) -> None:
        super().__init__("This browser action requires user approval.")
        self.pending_action = pending_action


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _origin_for_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BrowserSessionError("Browser pages must use an http or https URL.")
    if parsed.username or parsed.password:
        raise BrowserSessionError("Browser page URLs must not contain credentials.")
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def _bounded_text(value: str, *, field_name: str, limit: int) -> str:
    text = value.strip()
    if not text:
        raise BrowserSessionError(f"{field_name} is required.")
    if len(text) > limit:
        raise BrowserSessionError(f"{field_name} exceeds the {limit}-character limit.")
    return text


@dataclass
class BrowserSnapshot:
    url: str
    title: str
    visible_text: str
    captured_at: datetime = field(default_factory=_utc_now)

    def to_dict(self, *, max_chars: Optional[int] = None) -> Dict[str, Any]:
        limit = max_chars if max_chars is not None else len(self.visible_text)
        visible_text = self.visible_text[:limit]
        return {
            "url": self.url,
            "title": self.title,
            "visible_text": visible_text,
            "captured_at": self.captured_at.isoformat(),
            "truncated": len(visible_text) < len(self.visible_text),
            "original_chars": len(self.visible_text),
        }


@dataclass
class BrowserAction:
    id: str
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    status: str = "queued"
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_public_dict(self) -> Dict[str, Any]:
        payload = self.to_dict()
        payload.pop("value", None)
        return payload


@dataclass
class BrowserSession:
    id: str
    extension_token: str
    tab_id: str
    title: str
    url: str
    origin: str
    browser_name: str
    authorization_mode: str
    status: str = "active"
    chat_id: Optional[str] = None
    snapshot: Optional[BrowserSnapshot] = None
    actions: Dict[str, BrowserAction] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tab_id": self.tab_id,
            "title": self.title,
            "url": self.url,
            "origin": self.origin,
            "browser_name": self.browser_name,
            "authorization_mode": self.authorization_mode,
            "status": self.status,
            "chat_id": self.chat_id,
            "has_snapshot": self.snapshot is not None,
            "snapshot_captured_at": self.snapshot.captured_at.isoformat() if self.snapshot else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BrowserSessionService:
    """In-memory session store for the first browser-collaboration milestone.

    Browser authorization is intentionally ephemeral. A backend restart removes
    every session and requires an explicit re-authorisation in the extension.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = RLock()

    def register_tab(
        self,
        *,
        tab_id: str,
        title: str,
        url: str,
        browser_name: str = "Chrome",
        authorization_mode: str = "step_confirm",
    ) -> tuple[BrowserSession, str]:
        tab_id = _bounded_text(tab_id, field_name="tab_id", limit=256)
        title = _bounded_text(title, field_name="title", limit=500)
        url = _bounded_text(url, field_name="url", limit=4096)
        browser_name = _bounded_text(browser_name, field_name="browser_name", limit=100)
        origin = _origin_for_url(url)
        try:
            browser_policy_service.require_business_origin(origin)
        except BrowserPolicyError as exc:
            raise BrowserSessionUnauthorized(str(exc)) from exc
        if authorization_mode not in {"step_confirm", "session_auto", "site_auto"}:
            raise BrowserSessionError("Unsupported authorization mode.")

        session = BrowserSession(
            id=f"browser_{uuid4().hex}",
            extension_token=secrets.token_urlsafe(32),
            tab_id=tab_id,
            title=title,
            url=url,
            origin=origin,
            browser_name=browser_name,
            authorization_mode=authorization_mode,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session, session.extension_token

    def list_sessions(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [session.to_public_dict() for session in sorted(self._sessions.values(), key=lambda item: item.updated_at, reverse=True)]

    def get_session(self, session_id: str) -> BrowserSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise BrowserSessionNotFound("Browser session not found.")
            return session

    def _require_extension_token(self, session: BrowserSession, token: Optional[str]) -> None:
        if not token or not secrets.compare_digest(token, session.extension_token):
            raise BrowserSessionUnauthorized("Browser session token is invalid.")

    def submit_snapshot(
        self,
        *,
        session_id: str,
        extension_token: Optional[str],
        title: str,
        url: str,
        visible_text: str,
    ) -> Dict[str, Any]:
        title = _bounded_text(title, field_name="title", limit=500)
        url = _bounded_text(url, field_name="url", limit=4096)
        if not isinstance(visible_text, str):
            raise BrowserSessionError("visible_text must be a string.")
        if len(visible_text) > MAX_SNAPSHOT_TEXT_CHARS:
            raise BrowserSessionError(f"visible_text exceeds the {MAX_SNAPSHOT_TEXT_CHARS}-character limit.")
        origin = _origin_for_url(url)
        with self._lock:
            session = self.get_session(session_id)
            self._require_extension_token(session, extension_token)
            if session.status != "active":
                raise BrowserSessionStateError("Browser session is not active.")
            try:
                policy_purpose = browser_policy_service.purpose_for(origin)
            except BrowserPolicyError as exc:
                self._pause_for_policy_violation(session, str(exc))
                raise BrowserSessionUnauthorized(str(exc)) from exc
            if policy_purpose not in {"business", "sso_handoff"}:
                self._pause_for_policy_violation(session, "The page is no longer policy-approved for browser collaboration.")
                raise BrowserSessionUnauthorized("The page is no longer policy-approved for browser collaboration.")
            if origin != _origin_for_url(session.url):
                session.authorization_mode = "step_confirm"
            if policy_purpose == "sso_handoff":
                visible_text = ""
                title = "SSO handoff"
                url = origin
            session.title = title
            session.url = url
            session.origin = origin
            session.snapshot = BrowserSnapshot(url=url, title=title, visible_text=visible_text.strip())
            session.updated_at = _utc_now()
            return session.to_public_dict()

    def request_action(
        self,
        *,
        session_id: str,
        action: str,
        target: Optional[str] = None,
        value: Optional[str] = None,
    ) -> Dict[str, Any]:
        if action not in {"click", "fill", "select", "scroll", "navigate", "download", "submit"}:
            raise BrowserSessionError("Unsupported browser action.")
        if action in {"click", "fill", "select", "navigate"} and not isinstance(target, str):
            raise BrowserSessionError(f"{action} requires a target.")
        if action in {"fill", "select"} and not isinstance(value, str):
            raise BrowserSessionError(f"{action} requires a value.")
        if action == "navigate":
            target_origin = _origin_for_url(target or "")
        else:
            target_origin = None
        with self._lock:
            session = self.get_session(session_id)
            if session.status != "active":
                raise BrowserSessionStateError("Browser session is not active.")
            current_origin = _origin_for_url(session.url)
            try:
                current_purpose = browser_policy_service.purpose_for(current_origin)
                target_purpose = browser_policy_service.purpose_for(target_origin) if target_origin else None
            except BrowserPolicyError as exc:
                raise BrowserSessionUnauthorized(str(exc)) from exc
            if current_purpose != "business":
                self._pause_for_policy_violation(session, "The current origin is no longer approved for browser collaboration.")
            if current_purpose == "sso_handoff":
                raise BrowserSessionStateError("Browser actions are blocked during an SSO handoff.")
            if current_purpose != "business":
                raise BrowserSessionUnauthorized("The current origin is no longer approved for browser collaboration.")
            if target_origin and target_purpose is None:
                raise BrowserSessionUnauthorized("Navigation requires a policy-approved destination origin.")
            browser_action = BrowserAction(
                id=f"browser_action_{uuid4().hex}",
                action=action,
                target=target,
                value=value,
                status="awaiting_approval" if self._requires_approval(session, action, target_origin != current_origin) else "queued",
            )
            session.actions[browser_action.id] = browser_action
            session.updated_at = _utc_now()
            payload = browser_action.to_dict()
            if browser_action.status == "awaiting_approval":
                raise BrowserActionApprovalRequired(payload)
            return payload

    @staticmethod
    def _requires_approval(session: BrowserSession, action: str, crosses_origin: bool = False) -> bool:
        if action in {"submit", "download"} or crosses_origin:
            return True
        return session.authorization_mode == "step_confirm"

    def decide_action(self, *, session_id: str, action_id: str, approved: bool) -> Dict[str, Any]:
        with self._lock:
            session = self.get_session(session_id)
            browser_action = session.actions.get(action_id)
            if browser_action is None:
                raise BrowserSessionNotFound("Browser action not found.")
            if browser_action.status != "awaiting_approval":
                raise BrowserSessionStateError("Browser action is not awaiting approval.")
            browser_action.status = "queued" if approved else "rejected"
            browser_action.updated_at = _utc_now()
            session.updated_at = _utc_now()
            return browser_action.to_dict()

    def list_actions(self, *, session_id: str) -> list[Dict[str, Any]]:
        with self._lock:
            session = self.get_session(session_id)
            return [
                item.to_public_dict()
                for item in sorted(session.actions.values(), key=lambda action: action.created_at, reverse=True)
            ]

    def next_action(self, *, session_id: str, extension_token: Optional[str]) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.get_session(session_id)
            self._require_extension_token(session, extension_token)
            if session.status != "active":
                return None
            if browser_policy_service.purpose_for(_origin_for_url(session.url)) != "business":
                self._pause_for_policy_violation(session, "The current origin is no longer approved for browser collaboration.")
                return None
            queued = next((item for item in session.actions.values() if item.status == "queued"), None)
            if queued is None:
                return None
            queued.status = "dispatched"
            queued.updated_at = _utc_now()
            session.updated_at = _utc_now()
            return queued.to_dict()

    @staticmethod
    def _pause_for_policy_violation(session: BrowserSession, message: str) -> None:
        session.status = "paused"
        for action in session.actions.values():
            if action.status == "queued":
                action.status = "failed"
                action.result = {"error": message}
                action.updated_at = _utc_now()
        session.updated_at = _utc_now()

    def complete_action(
        self,
        *,
        session_id: str,
        action_id: str,
        extension_token: Optional[str],
        succeeded: bool,
        result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            session = self.get_session(session_id)
            self._require_extension_token(session, extension_token)
            browser_action = session.actions.get(action_id)
            if browser_action is None:
                raise BrowserSessionNotFound("Browser action not found.")
            if browser_action.status != "dispatched":
                raise BrowserSessionStateError("Browser action was not dispatched.")
            browser_action.status = "succeeded" if succeeded else "failed"
            browser_action.result = dict(result or {})
            browser_action.updated_at = _utc_now()
            session.updated_at = _utc_now()
            return browser_action.to_dict()

    def attach_to_chat(self, *, session_id: str, chat_id: str) -> Dict[str, Any]:
        chat_id = _bounded_text(chat_id, field_name="chat_id", limit=256)
        with self._lock:
            session = self.get_session(session_id)
            if session.status != "active":
                raise BrowserSessionStateError("Only active browser sessions can be attached to a chat.")
            session.chat_id = chat_id
            session.updated_at = _utc_now()
            return session.to_public_dict()

    def set_status(self, *, session_id: str, status: str) -> Dict[str, Any]:
        if status not in {"active", "paused", "disconnected"}:
            raise BrowserSessionError("Unsupported browser session status.")
        with self._lock:
            session = self.get_session(session_id)
            session.status = status
            if status == "disconnected":
                session.chat_id = None
                session.extension_token = ""
            session.updated_at = _utc_now()
            return session.to_public_dict()

    def read_snapshot(self, *, session_id: str, max_chars: int = 12_000) -> Dict[str, Any]:
        if not isinstance(max_chars, int) or isinstance(max_chars, bool):
            raise BrowserSessionError("max_chars must be an integer.")
        max_chars = max(MIN_READ_CHARS, min(MAX_READ_CHARS, max_chars))
        with self._lock:
            session = self.get_session(session_id)
            if session.status != "active":
                raise BrowserSessionStateError("Browser session is not active.")
            if session.snapshot is None:
                raise BrowserSessionStateError("No page snapshot is available yet. Ask the user to refresh the extension snapshot.")
            payload = session.snapshot.to_dict(max_chars=max_chars)
            payload.update({"ok": True, "browser_session_id": session.id, "origin": session.origin})
            return payload

    def resolve_session_id(self, *, chat_id: Optional[str], requested_session_id: Optional[str]) -> Optional[str]:
        if requested_session_id:
            return requested_session_id
        if not chat_id:
            return None
        with self._lock:
            for session in self._sessions.values():
                if session.chat_id == chat_id and session.status == "active":
                    return session.id
        return None

    def reset_for_tests(self) -> None:
        with self._lock:
            self._sessions.clear()


browser_session_service = BrowserSessionService()
