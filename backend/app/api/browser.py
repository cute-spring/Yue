from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.browser_session_service import (
    BrowserSessionError,
    BrowserSessionNotFound,
    BrowserSessionUnauthorized,
    BrowserActionApprovalRequired,
    browser_session_service,
)
from app.services.browser_policy_service import BrowserPolicyError, browser_policy_service


router = APIRouter()


class BrowserTabRegistration(BaseModel):
    tab_id: str
    title: str
    url: str
    browser_name: str = "Chrome"
    authorization_mode: Literal["step_confirm", "session_auto", "site_auto"] = "step_confirm"


class BrowserSnapshotUpload(BaseModel):
    title: str
    url: str
    visible_text: str


class BrowserChatAttachment(BaseModel):
    chat_id: str


class BrowserOriginPolicyRequest(BaseModel):
    origin: str
    purpose: Literal["sso_handoff", "business"]


class BrowserOriginPolicyDecision(BaseModel):
    approved: bool


class BrowserActionRequest(BaseModel):
    action: Literal["click", "fill", "select", "scroll", "navigate", "download", "submit"]
    target: str | None = None
    value: str | None = None


class BrowserActionDecision(BaseModel):
    approved: bool


class BrowserActionResult(BaseModel):
    succeeded: bool
    result: dict = Field(default_factory=dict)


def _raise_browser_error(exc: BrowserSessionError) -> None:
    if isinstance(exc, BrowserSessionNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, BrowserSessionUnauthorized):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def _raise_browser_policy_error(exc: BrowserPolicyError) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/policy/origins")
async def list_browser_policy_origins():
    return browser_policy_service.list_origins()


@router.post("/policy/origin-requests", status_code=202)
async def request_browser_policy_origin(request: BrowserOriginPolicyRequest):
    try:
        return browser_policy_service.request_origin(**request.model_dump())
    except BrowserPolicyError as exc:
        _raise_browser_policy_error(exc)


@router.post("/policy/origin-requests/{request_id}/decision")
async def decide_browser_policy_origin(request_id: str, request: BrowserOriginPolicyDecision):
    try:
        return browser_policy_service.decide_origin_request(request_id=request_id, approved=request.approved)
    except BrowserPolicyError as exc:
        _raise_browser_policy_error(exc)


@router.delete("/policy/origins/{origin:path}", status_code=204)
async def revoke_browser_policy_origin(origin: str):
    try:
        browser_policy_service.revoke_origin(origin=origin)
        return Response(status_code=204)
    except BrowserPolicyError as exc:
        _raise_browser_policy_error(exc)


@router.get("/sessions")
async def list_browser_sessions():
    return browser_session_service.list_sessions()


@router.post("/sessions/register")
async def register_browser_tab(request: BrowserTabRegistration):
    try:
        session, extension_token = browser_session_service.register_tab(**request.model_dump())
    except BrowserSessionError as exc:
        _raise_browser_error(exc)
    return {**session.to_public_dict(), "extension_token": extension_token}


@router.get("/sessions/{session_id}")
async def get_browser_session(session_id: str):
    try:
        return browser_session_service.get_session(session_id).to_public_dict()
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/snapshot")
async def upload_browser_snapshot(
    session_id: str,
    request: BrowserSnapshotUpload,
    x_yue_browser_token: Optional[str] = Header(default=None),
):
    try:
        return browser_session_service.submit_snapshot(
            session_id=session_id,
            extension_token=x_yue_browser_token,
            **request.model_dump(),
        )
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/attach")
async def attach_browser_session(session_id: str, request: BrowserChatAttachment):
    try:
        return browser_session_service.attach_to_chat(session_id=session_id, chat_id=request.chat_id)
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/actions", status_code=202)
async def request_browser_action(session_id: str, request: BrowserActionRequest):
    try:
        return browser_session_service.request_action(session_id=session_id, **request.model_dump())
    except BrowserActionApprovalRequired as exc:
        return {"status": "awaiting_approval", "action": exc.pending_action}
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.get("/sessions/{session_id}/actions")
async def list_browser_actions(session_id: str):
    try:
        return browser_session_service.list_actions(session_id=session_id)
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/actions/{action_id}/decision")
async def decide_browser_action(session_id: str, action_id: str, request: BrowserActionDecision):
    try:
        return browser_session_service.decide_action(
            session_id=session_id,
            action_id=action_id,
            approved=request.approved,
        )
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.get("/sessions/{session_id}/commands/next")
async def get_next_browser_command(
    session_id: str,
    x_yue_browser_token: Optional[str] = Header(default=None),
):
    try:
        command = browser_session_service.next_action(session_id=session_id, extension_token=x_yue_browser_token)
        return command if command is not None else Response(status_code=204)
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/actions/{action_id}/result")
async def complete_browser_action(
    session_id: str,
    action_id: str,
    request: BrowserActionResult,
    x_yue_browser_token: Optional[str] = Header(default=None),
):
    try:
        return browser_session_service.complete_action(
            session_id=session_id,
            action_id=action_id,
            extension_token=x_yue_browser_token,
            **request.model_dump(),
        )
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/pause")
async def pause_browser_session(session_id: str):
    try:
        return browser_session_service.set_status(session_id=session_id, status="paused")
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/resume")
async def resume_browser_session(session_id: str):
    try:
        return browser_session_service.set_status(session_id=session_id, status="active")
    except BrowserSessionError as exc:
        _raise_browser_error(exc)


@router.post("/sessions/{session_id}/disconnect")
async def disconnect_browser_session(session_id: str):
    try:
        return browser_session_service.set_status(session_id=session_id, status="disconnected")
    except BrowserSessionError as exc:
        _raise_browser_error(exc)
