"""Ephemeral, user-authorized browser-tab sessions.

The browser extension owns the secret that proves control of a tab. Yue only
stores a redacted session record and the latest user-authorized page snapshot.
This is deliberately separate from general web fetching: it never opens a URL
or attempts to bypass a site's authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sqlite3
from threading import RLock
from typing import Any, Dict, Optional
from urllib.parse import urlsplit
from uuid import uuid4

from app.services.browser_policy_service import BrowserPolicyError, browser_policy_service


MAX_SNAPSHOT_TEXT_CHARS = 100_000
MIN_READ_CHARS = 500
MAX_READ_CHARS = 50_000
DEFAULT_COMMAND_LEASE_SECONDS = 30


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


class BrowserCommandLedger:
    """Durable local record of browser commands without sensitive field values."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS browser_command_ledger (
                    command_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    command_type TEXT NOT NULL,
                    target TEXT,
                    snapshot_id TEXT,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(browser_command_ledger)").fetchall()
            }
            if "snapshot_id" not in columns:
                self._connection.execute("ALTER TABLE browser_command_ledger ADD COLUMN snapshot_id TEXT")
            self._connection.execute(
                """
                UPDATE browser_command_ledger
                SET status = 'needs_reconciliation', updated_at = ?
                WHERE status = 'dispatched'
                """,
                (_utc_now().isoformat(),),
            )

    def record(self, *, session_id: str, command: "BrowserAction") -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO browser_command_ledger (
                    command_id, session_id, command_type, target, snapshot_id,
                    status, result_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(command_id) DO UPDATE SET
                    target = excluded.target,
                    snapshot_id = excluded.snapshot_id,
                    status = excluded.status,
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (
                    command.id,
                    session_id,
                    command.action,
                    command.target,
                    command.snapshot_id,
                    command.status,
                    json.dumps(command.result, ensure_ascii=False) if command.result is not None else None,
                    command.created_at.isoformat(),
                    command.updated_at.isoformat(),
                ),
            )

    def list_for_session(self, session_id: str) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT command_id, command_type, target, snapshot_id, status, result_json, created_at, updated_at
                FROM browser_command_ledger
                WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "id": row["command_id"],
                "action": row["command_type"],
                "target": row["target"],
                "snapshot_id": row["snapshot_id"],
                "status": row["status"],
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


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
    id: str
    url: str
    title: str
    visible_text: str
    captured_at: datetime = field(default_factory=_utc_now)

    def to_dict(self, *, max_chars: Optional[int] = None) -> Dict[str, Any]:
        limit = max_chars if max_chars is not None else len(self.visible_text)
        visible_text = self.visible_text[:limit]
        return {
            "id": self.id,
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
    snapshot_id: Optional[str] = None
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
            "snapshot_id": self.snapshot_id,
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
    pending_navigation_action_id: Optional[str] = None
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
            "pending_navigation": self.pending_navigation_action_id is not None,
            "snapshot_captured_at": self.snapshot.captured_at.isoformat() if self.snapshot else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BrowserSessionService:
    """In-memory session store for the first browser-collaboration milestone.

    Browser authorization is intentionally ephemeral. A backend restart removes
    every session and requires an explicit re-authorisation in the extension.
    """

    def __init__(
        self,
        *,
        ledger_path: str | Path | None = None,
        command_lease_seconds: int = DEFAULT_COMMAND_LEASE_SECONDS,
    ) -> None:
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = RLock()
        if command_lease_seconds < 0:
            raise ValueError("command_lease_seconds must not be negative.")
        self.command_lease_seconds = command_lease_seconds
        if ledger_path is None:
            data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
            ledger_path = data_dir / "browser-command-ledger.sqlite3"
        self.command_ledger = BrowserCommandLedger(ledger_path)

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
                session.pending_navigation_action_id = None
                self._fail_queued_actions(session, "The page changed origin and requires fresh confirmation.")
            if policy_purpose == "sso_handoff":
                visible_text = ""
                title = "SSO handoff"
                url = origin
            session.title = title
            session.url = url
            session.origin = origin
            previous_snapshot_id = session.snapshot.id if session.snapshot else None
            session.snapshot = BrowserSnapshot(
                id=f"browser_snapshot_{uuid4().hex}",
                url=url,
                title=title,
                visible_text=visible_text.strip(),
            )
            if previous_snapshot_id:
                self._cancel_stale_commands(session, previous_snapshot_id)
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
            if session.snapshot is None:
                raise BrowserSessionStateError("A current page snapshot is required before requesting a browser command.")
            if session.pending_navigation_action_id:
                raise BrowserSessionStateError("Browser navigation is awaiting page reconciliation.")
            current_origin = _origin_for_url(session.url)
            try:
                current_purpose = browser_policy_service.purpose_for(current_origin)
                target_purpose = browser_policy_service.purpose_for(target_origin) if target_origin else None
            except BrowserPolicyError as exc:
                raise BrowserSessionUnauthorized(str(exc)) from exc
            if current_purpose == "sso_handoff":
                raise BrowserSessionStateError("Browser actions are blocked during an SSO handoff.")
            if current_purpose != "business":
                self._pause_for_policy_violation(session, "The current origin is no longer approved for browser collaboration.")
                raise BrowserSessionUnauthorized("The current origin is no longer approved for browser collaboration.")
            if target_origin and target_purpose is None:
                raise BrowserSessionUnauthorized("Navigation requires a policy-approved destination origin.")
            if target_purpose == "sso_handoff":
                raise BrowserSessionStateError("Yue cannot navigate an SSO handoff. Complete it directly in the browser.")
            browser_action = BrowserAction(
                id=f"browser_action_{uuid4().hex}",
                action=action,
                target=target,
                value=value,
                snapshot_id=session.snapshot.id if session.snapshot else None,
                status="awaiting_approval"
                if self._requires_approval(session, action, bool(target_origin and target_origin != current_origin))
                else "queued",
            )
            session.actions[browser_action.id] = browser_action
            self.command_ledger.record(session_id=session.id, command=browser_action)
            session.updated_at = _utc_now()
            payload = browser_action.to_dict()
            if browser_action.status == "awaiting_approval":
                raise BrowserActionApprovalRequired(payload)
            return payload

    @staticmethod
    def _requires_approval(session: BrowserSession, action: str, crosses_origin: bool = False) -> bool:
        if action in {"click", "submit", "download", "navigate"} or crosses_origin:
            return True
        return session.authorization_mode == "step_confirm"

    def decide_action(self, *, session_id: str, action_id: str, approved: bool) -> Dict[str, Any]:
        with self._lock:
            session = self.get_session(session_id)
            browser_action = session.actions.get(action_id)
            if browser_action is None:
                raise BrowserSessionNotFound("Browser action not found.")
            if browser_action.status == "cancelled" and browser_action.result == {"error": "The page changed before approval."}:
                raise BrowserSessionStateError("The page changed before browser command approval.")
            if browser_action.status != "awaiting_approval":
                raise BrowserSessionStateError("Browser action is not awaiting approval.")
            if not session.snapshot or browser_action.snapshot_id != session.snapshot.id:
                browser_action.status = "cancelled"
                browser_action.result = {"error": "The page changed before approval."}
                browser_action.updated_at = _utc_now()
                self.command_ledger.record(session_id=session.id, command=browser_action)
                raise BrowserSessionStateError("The page changed before browser command approval.")
            browser_action.status = "queued" if approved else "rejected"
            if approved and browser_action.action == "navigate" and browser_action.target:
                if _origin_for_url(browser_action.target) != _origin_for_url(session.url):
                    session.pending_navigation_action_id = browser_action.id
            browser_action.updated_at = _utc_now()
            self.command_ledger.record(session_id=session.id, command=browser_action)
            session.updated_at = _utc_now()
            return browser_action.to_dict()

    def list_actions(self, *, session_id: str) -> list[Dict[str, Any]]:
        return self.command_ledger.list_for_session(session_id)

    def next_action(self, *, session_id: str, extension_token: Optional[str]) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.get_session(session_id)
            self._require_extension_token(session, extension_token)
            if session.status != "active":
                return None
            current_purpose = browser_policy_service.purpose_for(_origin_for_url(session.url))
            if current_purpose == "sso_handoff":
                return None
            if current_purpose != "business":
                self._pause_for_policy_violation(session, "The current origin is no longer approved for browser collaboration.")
                return None
            self._expire_dispatched_commands(session)
            if any(item.status in {"dispatched", "needs_reconciliation"} for item in session.actions.values()):
                return None
            queued = next(
                (
                    item
                    for item in session.actions.values()
                    if item.status == "queued"
                    and (not session.pending_navigation_action_id or item.id == session.pending_navigation_action_id)
                ),
                None,
            )
            if queued is None:
                return None
            queued.status = "dispatched"
            queued.updated_at = _utc_now()
            self.command_ledger.record(session_id=session.id, command=queued)
            session.updated_at = _utc_now()
            return queued.to_dict()

    def _pause_for_policy_violation(self, session: BrowserSession, message: str) -> None:
        session.status = "paused"
        self._fail_queued_actions(session, message)
        session.updated_at = _utc_now()

    def _fail_queued_actions(self, session: BrowserSession, message: str) -> None:
        for action in session.actions.values():
            if action.status == "queued":
                action.status = "failed"
                action.result = {"error": message}
                action.updated_at = _utc_now()
                self.command_ledger.record(session_id=session.id, command=action)

    def _cancel_stale_commands(self, session: BrowserSession, previous_snapshot_id: str) -> None:
        for command in session.actions.values():
            if command.snapshot_id != previous_snapshot_id or command.status not in {"awaiting_approval", "queued"}:
                continue
            command.status = "cancelled"
            command.result = {"error": "The page changed before approval."}
            command.updated_at = _utc_now()
            self.command_ledger.record(session_id=session.id, command=command)

    def _expire_dispatched_commands(self, session: BrowserSession) -> None:
        now = _utc_now()
        for command in session.actions.values():
            if command.status != "dispatched":
                continue
            if (now - command.updated_at).total_seconds() < self.command_lease_seconds:
                continue
            command.status = "needs_reconciliation"
            command.result = {"error": "The browser command lease expired without a completion receipt."}
            command.updated_at = now
            self.command_ledger.record(session_id=session.id, command=command)

    def complete_action(
        self,
        *,
        session_id: str,
        action_id: str,
        extension_token: Optional[str],
        succeeded: Optional[bool],
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
            current_purpose = browser_policy_service.purpose_for(_origin_for_url(session.url))
            if current_purpose != "business":
                browser_action.status = "failed"
                if current_purpose is None:
                    self._pause_for_policy_violation(session, "The current origin is no longer approved for browser collaboration.")
                browser_action.result = {"message": "Browser action result was discarded after an origin-policy change."}
            elif succeeded is None:
                browser_action.status = "needs_reconciliation"
                browser_action.result = {"message": "Browser command completion is uncertain and requires user reconciliation."}
            elif not succeeded:
                browser_action.status = "failed"
                browser_action.result = {"message": "Browser action failed."}
            elif not session.snapshot or session.snapshot.captured_at <= browser_action.updated_at:
                browser_action.status = "needs_reconciliation"
                browser_action.result = {
                    "message": "Browser command completion needs a fresh post-command page snapshot."
                }
            else:
                browser_action.status = "succeeded"
                browser_action.result = {"message": "Browser action completed."}
            if current_purpose == "sso_handoff":
                browser_action.result = {"message": "SSO handoff completed; no page data captured."}
            if not succeeded and session.pending_navigation_action_id == action_id:
                session.pending_navigation_action_id = None
            browser_action.updated_at = _utc_now()
            self.command_ledger.record(session_id=session.id, command=browser_action)
            session.updated_at = _utc_now()
            return browser_action.to_dict()

    def reconcile_action(self, *, session_id: str, action_id: str, outcome: str) -> Dict[str, Any]:
        if outcome not in {"completed", "not_applied"}:
            raise BrowserSessionError("Unsupported browser command reconciliation outcome.")
        with self._lock:
            session = self.get_session(session_id)
            browser_action = session.actions.get(action_id)
            if browser_action is None:
                raise BrowserSessionNotFound("Browser action not found.")
            if browser_action.status != "needs_reconciliation":
                raise BrowserSessionStateError("Browser action does not need reconciliation.")
            browser_action.status = "succeeded" if outcome == "completed" else "cancelled"
            browser_action.result = {
                "message": (
                    "The user confirmed that the browser command completed."
                    if outcome == "completed"
                    else "The user confirmed that the browser command was not applied."
                )
            }
            browser_action.updated_at = _utc_now()
            self.command_ledger.record(session_id=session.id, command=browser_action)
            if browser_action.snapshot_id:
                self._cancel_stale_commands(session, browser_action.snapshot_id)
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
