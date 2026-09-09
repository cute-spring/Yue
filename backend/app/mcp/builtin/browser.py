"""Read-only access to a page explicitly shared through the Yue extension."""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic_ai import RunContext

from app.services.browser_session_service import (
    BrowserActionApprovalRequired,
    BrowserSessionError,
    browser_session_service,
)

from ..base import BaseTool
from .registry import builtin_tool_registry


class BrowserReadTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="browser_read",
            description=(
                "Read the latest visible-text snapshot from the user-authorized browser tab. "
                "This tool is read-only and never opens pages, clicks controls, or exposes passwords."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum visible-text characters to return (500 to 50000).",
                    }
                },
            },
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        deps = getattr(ctx, "deps", None)
        deps = deps if isinstance(deps, dict) else {}
        session_id = browser_session_service.resolve_session_id(
            chat_id=deps.get("chat_id"),
            requested_session_id=deps.get("browser_session_id"),
        )
        if not session_id:
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "browser_session_not_attached",
                    "message": "No active browser tab is attached to this chat.",
                    "hint": "Ask the user to authorize a tab with the Yue Browser Companion and attach it to this chat.",
                },
                ensure_ascii=False,
            )
        try:
            return json.dumps(
                browser_session_service.read_snapshot(session_id=session_id, max_chars=args.get("max_chars", 12_000)),
                ensure_ascii=False,
            )
        except BrowserSessionError as exc:
            return json.dumps(
                {"ok": False, "error_code": "browser_snapshot_unavailable", "message": str(exc)},
                ensure_ascii=False,
            )


builtin_tool_registry.register(BrowserReadTool())


class BrowserInteractTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="browser_interact",
            description=(
                "Request a user-authorized browser action in the attached tab. Use fill/select/click/scroll/navigate "
                "for ordinary work. Never use click to submit a form; use submit instead, which always requires approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["click", "fill", "select", "scroll", "navigate", "download", "submit"],
                    },
                    "target": {"type": "string", "description": "Visible label, field name, or URL for navigate."},
                    "value": {"type": "string", "description": "Text or option value for fill/select."},
                },
                "required": ["action"],
            },
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        deps = getattr(ctx, "deps", None)
        deps = deps if isinstance(deps, dict) else {}
        session_id = browser_session_service.resolve_session_id(
            chat_id=deps.get("chat_id"), requested_session_id=deps.get("browser_session_id")
        )
        if not session_id:
            return json.dumps({"ok": False, "error_code": "browser_session_not_attached"}, ensure_ascii=False)
        try:
            action = browser_session_service.request_action(
                session_id=session_id,
                action=args.get("action"),
                target=args.get("target"),
                value=args.get("value"),
            )
            return json.dumps({"ok": True, "browser_session_id": session_id, "action": action}, ensure_ascii=False)
        except BrowserActionApprovalRequired as exc:
            return json.dumps(
                {"ok": False, "error_code": "browser_action_approval_required", "action": exc.pending_action},
                ensure_ascii=False,
            )
        except BrowserSessionError as exc:
            return json.dumps({"ok": False, "error_code": "browser_action_unavailable", "message": str(exc)}, ensure_ascii=False)


builtin_tool_registry.register(BrowserInteractTool())
