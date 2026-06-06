from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.api.chat_stream_runner import (
    build_chat_event_generator,
)
from app.api.chat_endpoint_helpers import (
    normalize_action_state_response as _normalize_action_state_response,
    require_chat,
    resolve_action_state_lookup,
)
from app.api.chat_schemas import (
    ActionStateResponse,
    ChatRequest,
    CaptureTelemetryRequest,
    SummaryGenerateRequest,
    TruncateRequest,
)
from app.services.chat_service import chat_service, ChatSession
from app.services.session_meta_service import session_meta_service
from app.api.chat_stream_deps import (
    MultimodalService,
    MultimodalValidationError,
    build_chat_request_log_payload as _build_chat_request_log_payload,
    build_history_from_chat as _build_history_from_chat,
    build_stream_runner_deps,
    config_service,
    env_flag,
    env_flag_with_fallback,
    persist_validated_images,
    record_title_refinement_reason_payload as _record_title_refinement_reason,
    safe_json_log,
    save_base64_image,
    title_refinement_reason_distribution_payload as _title_refinement_reason_distribution,
)
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/history", response_model=list[ChatSession])
async def list_chats(
    tags: Optional[str] = Query(default=None, description="Comma-separated tags to filter"),
    tag_mode: str = Query(default="any", pattern="^(any|all)$"),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
):
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else None
    return chat_service.list_chats(tags=parsed_tags, tag_mode=tag_mode, date_from=date_from, date_to=date_to)

@router.get("/{chat_id}", response_model=ChatSession)
async def get_chat(chat_id: str):
    return require_chat(chat_id, chat_service=chat_service)

@router.get("/{chat_id}/events")
async def get_chat_events(chat_id: str, assistant_turn_id: Optional[str] = None, after_sequence: Optional[int] = None):
    require_chat(chat_id, chat_service=chat_service)
    return chat_service.get_chat_events(chat_id, assistant_turn_id=assistant_turn_id, after_sequence=after_sequence)


@router.post("/{chat_id}/capture-events")
async def add_capture_event(chat_id: str, request: CaptureTelemetryRequest):
    require_chat(chat_id, chat_service=chat_service)
    payload = {
        "event": "workspace.capture.telemetry",
        "workspace_id": request.workspace_id,
        "event_type": request.event_type,
        "source": request.source,
        "assistant_message_id": request.assistant_message_id,
        "accepted": request.accepted,
        "note_id": request.note_id,
        "candidate_id": request.candidate_id,
        "metadata": request.metadata or {},
    }
    chat_service.add_action_event(
        chat_id,
        payload,
        assistant_turn_id=request.assistant_turn_id,
        run_id=request.run_id,
    )
    return {"status": "success"}

@router.get("/{chat_id}/trace/bundle")
async def get_chat_trace_bundle(chat_id: str, assistant_turn_id: Optional[str] = None, mode: str = Query(default="summary")):
    require_chat(chat_id, chat_service=chat_service)
    if mode == "raw":
        feature_flags = config_service.get_feature_flags()
        if not feature_flags.get("chat_trace_raw_enabled", False):
            raise HTTPException(status_code=403, detail="Raw trace mode is disabled")
    try:
        bundle = chat_service.get_chat_trace_bundle(chat_id, assistant_turn_id=assistant_turn_id, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if bundle is None:
        raise HTTPException(status_code=404, detail="Trace bundle not found")
    return bundle

@router.get("/{chat_id}/actions/state", response_model=ActionStateResponse)
async def get_action_state(
    chat_id: str,
    skill_name: Optional[str] = Query(default=None),
    action_id: Optional[str] = Query(default=None),
    invocation_id: Optional[str] = Query(default=None),
    approval_token: Optional[str] = Query(default=None),
):
    state = resolve_action_state_lookup(
        chat_id=chat_id,
        skill_name=skill_name,
        action_id=action_id,
        invocation_id=invocation_id,
        approval_token=approval_token,
        chat_service=chat_service,
    )
    return _normalize_action_state_response(state)

@router.get("/{chat_id}/actions/states", response_model=list[ActionStateResponse])
async def list_action_states(chat_id: str):
    require_chat(chat_id, chat_service=chat_service)
    states = chat_service.list_action_states(chat_id)
    return [_normalize_action_state_response(state) for state in states]

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    if not chat_service.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

@router.post("/{chat_id}/truncate")
async def truncate_chat(chat_id: str, request: TruncateRequest):
    chat_service.truncate_chat(chat_id, request.keep_count)
    return {"status": "success"}

@router.post("/{chat_id}/summary")
async def generate_chat_summary(chat_id: str, request: Optional[SummaryGenerateRequest] = None):
    chat = require_chat(chat_id, chat_service=chat_service)
    force = bool(request.force) if request else False
    existing_summary = chat.get("summary") if isinstance(chat, dict) else chat.summary
    if existing_summary and not force:
        return {"summary": existing_summary}
    summary = await session_meta_service.generate_session_meta(chat_id, task="summary")
    if not summary:
        return {"summary": existing_summary or ""}
    chat_service.update_chat_summary(chat_id, summary)
    return {"summary": summary}


@router.post("/{chat_id}/tags/generate")
async def generate_chat_tags(chat_id: str):
    require_chat(chat_id, chat_service=chat_service)
    tags = chat_service.generate_chat_tags(chat_id)
    return {"tags": tags or []}

@router.get("/{chat_id}/meta")
async def get_chat_meta(chat_id: str):
    chat = require_chat(chat_id, chat_service=chat_service)
    return {
        "id": chat.id,
        "title": chat.title,
        "summary": chat.summary,
        "updated_at": chat.updated_at
    }

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    # Initialize Chat Session
    chat_id = request.chat_id
    if not chat_id:
        chat = chat_service.create_chat(request.agent_id, workspace_id=request.workspace_id)
        chat_id = chat.id
    
    existing_chat = chat_service.get_chat(chat_id)
    history = _build_history_from_chat(existing_chat)

    multimodal_service = MultimodalService.from_config(config_service.get_config())
    try:
        validated_images = multimodal_service.validate_images(request.images)
    except MultimodalValidationError as image_err:
        raise HTTPException(status_code=400, detail={"code": image_err.code, "message": image_err.message})

    # Save User Message to DB
    # Save images to disk before DB
    stored_images = persist_validated_images(validated_images, save_base64_image=save_base64_image, logger=logger)

    if env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
        logger.info(
            "BACKLOG_CHAT_REQUEST %s",
            safe_json_log(_build_chat_request_log_payload(chat_id, request)),
        )

    attachments_payload = [item.model_dump(mode="json") for item in (request.attachments or [])]
    chat_service.add_message(
        chat_id,
        "user",
        request.message,
        images=stored_images if stored_images else None,
        attachments=attachments_payload if attachments_payload else None,
    )

    deps = build_stream_runner_deps()

    return StreamingResponse(
        build_chat_event_generator(
            chat_id=chat_id,
            request=request,
            history=history,
            validated_images=validated_images,
            multimodal_service=multimodal_service,
            deps=deps,
        ),
        media_type="text/event-stream",
    )

@router.get("/skill-effectiveness/report")
async def get_skill_effectiveness_report(hours: int = 24):
    if hours <= 0 or hours > 24 * 30:
        raise HTTPException(status_code=400, detail="hours_out_of_range")
    return chat_service.get_skill_effectiveness_report(hours=hours)

@router.get("/title-refinement/reasons")
async def get_title_refinement_reason_distribution():
    return _title_refinement_reason_distribution()
