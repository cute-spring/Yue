from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic_ai import Agent, UsageLimits
from app.api.chat_stream_runner import (
    PromptRuntimeDeps,
    RetryRuntimeDeps,
    StreamRunnerDeps,
    build_chat_event_generator,
)
from app.api.chat_helpers import (
    build_runtime_meta_payload,
    iso_utc_now,
    resolve_reasoning_state,
    serialize_sse_payload,
)
from app.api.chat_schemas import (
    ActionStateResponse,
    ChatRequest,
    SummaryGenerateRequest,
    TruncateRequest,
)
from app.api.chat_tool_events import ToolEventTracker
from app.mcp.registry import tool_registry
from app.services.agent_store import agent_store
from app.services.model_factory import get_model, fetch_ollama_models
from app.services.chat_service import chat_service, ChatSession
from app.services.config_service import config_service
from app.services.prompt_service import build_system_prompt
from app.services.response_parser_service import get_parser
from app.services.usage_service import calculate_usage
from app.services.llm.utils import handle_llm_exception
from app.services.multimodal_service import MultimodalService, MultimodalValidationError
from app.services.session_meta_service import session_meta_service
from app.services.skill_service import skill_action_execution_service, skill_registry, skill_router
from app.services.skills import (
    SkillPolicyGate,
    MarkdownSkillAdapter,
    build_action_approval_message,
    build_action_execution_stub_message,
    build_action_preflight_message,
)
from app.services import doc_retrieval
from app.services.chat_prompting import (
    estimate_tokens,
    env_flag,
    env_flag_with_fallback,
    safe_int_env_with_fallback,
    build_scope_summary_block as prompting_build_scope_summary_block,
    build_history_from_chat as prompting_build_history_from_chat,
    resolve_skill_runtime_state as prompting_resolve_skill_runtime_state,
    assemble_runtime_prompt,
)
from app.services.chat_runtime import (
    build_chat_request_log_payload as runtime_build_chat_request_log_payload,
    build_chat_response_log_payload as runtime_build_chat_response_log_payload,
    safe_json_log,
    persist_validated_images,
    collect_tool_names,
    patch_model_settings,
    build_agent_deps,
    build_skill_effectiveness_payload,
    ensure_ollama_model_available,
    format_citations_suffix,
)
from app.services.chat_streaming import StreamEventEmitter, StreamState, stream_result_chunks
from app.services.chat_postprocess import (
    title_refinement_reason_distribution,
    record_title_refinement_reason,
    refine_title_once,
    normalize_finished_ts,
    append_continue_message_if_needed,
    append_citation_suffix_if_needed,
    persist_assistant_message,
)
from app.services.chat_retry_service import (
    should_handle_tool_call_mismatch,
    resolve_retry_targets,
    build_tool_call_retry_event,
    build_tool_call_retry_success_event,
    build_tool_call_retry_failed_event,
    build_tool_call_mismatch_event,
    build_tool_call_mismatch_message,
)
from app.utils.image_handler import save_base64_image, load_image_to_base64
import asyncio
import logging
from collections import defaultdict
from typing import List, Optional, Dict, Any, Tuple, AsyncIterator
from datetime import datetime

logger = logging.getLogger(__name__)

SKILL_BIND_MIN_SCORE = 2
SKILL_SWITCH_DELTA = 2
_TITLE_REFINEMENT_REASON_COUNTS: Dict[str, int] = defaultdict(int)

def _build_chat_request_log_payload(chat_id: str, request: "ChatRequest") -> Dict[str, Any]:
    return runtime_build_chat_request_log_payload(
        chat_id,
        request,
        env_flag_with_fallback=env_flag_with_fallback,
        safe_int_env_with_fallback=safe_int_env_with_fallback,
    )

def _build_chat_response_log_payload(
    chat_id: str,
    provider: Optional[str],
    model_name: Optional[str],
    finish_reason: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    ttft: Optional[float],
    total_duration: Optional[float],
    tool_call_started_count: int,
    tool_call_finished_count: int,
    full_response: str,
    error: Optional[str],
) -> Dict[str, Any]:
    return runtime_build_chat_response_log_payload(
        chat_id=chat_id,
        provider=provider,
        model_name=model_name,
        finish_reason=finish_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        ttft=ttft,
        total_duration=total_duration,
        tool_call_started_count=tool_call_started_count,
        tool_call_finished_count=tool_call_finished_count,
        full_response=full_response,
        error=error,
        safe_int_env_with_fallback=safe_int_env_with_fallback,
    )

def _build_scope_summary_block(agent_config: Any) -> Tuple[Optional[str], int]:
    return prompting_build_scope_summary_block(
        agent_config,
        config_service=config_service,
        doc_retrieval=doc_retrieval,
    )


def _build_history_from_chat(existing_chat: Optional[ChatSession]) -> List[Any]:
    return prompting_build_history_from_chat(existing_chat, load_image_to_base64=load_image_to_base64, logger=logger)


async def _yield_stream_chunks(
    *,
    result: Any,
    parser: Any,
    tool_event_queue: asyncio.Queue,
    emitter: StreamEventEmitter,
    stream_state: StreamState,
    log_label: str,
) -> AsyncIterator[str]:
    async for payload in stream_result_chunks(
        result=result,
        parser=parser,
        tool_event_queue=tool_event_queue,
        emitter=emitter,
        stream_state=stream_state,
        serialize_payload=serialize_sse_payload,
        logger=logger,
        log_label=log_label,
    ):
        yield payload


async def _run_agent_stream(
    *,
    agent: Agent,
    user_input: Any,
    history: List[Any],
    deps: Any,
    model_settings: Dict[str, Any],
    parser: Any,
    tool_event_queue: asyncio.Queue,
    emitter: StreamEventEmitter,
    stream_state: StreamState,
    log_label: str,
    result_holder: Dict[str, Any],
    usage_limits: Optional[UsageLimits] = None,
) -> AsyncIterator[str]:
    run_kwargs: Dict[str, Any] = {
        "message_history": history,
        "deps": deps,
        "model_settings": model_settings,
    }
    if usage_limits is not None:
        run_kwargs["usage_limits"] = usage_limits

    async with agent.run_stream(user_input, **run_kwargs) as stream_result:
        result_holder["result"] = stream_result
        async for payload in _yield_stream_chunks(
            result=stream_result,
            parser=parser,
            tool_event_queue=tool_event_queue,
            emitter=emitter,
            stream_state=stream_state,
            log_label=log_label,
        ):
            yield payload


def _emit_skill_effectiveness_event(
    *,
    chat_id: str,
    emitter: StreamEventEmitter,
    selection_reason_code: str,
    selection_source: str,
    selection_score: int,
    selected_skill_spec: Any,
    visible_skill_count: int,
    available_skill_count: int,
    always_injected_count: int,
    selected_group_ids: List[str],
    resolved_skill_count: int,
    summary_injected: bool,
    scope_summary_injected: bool,
    effective_scope_count: int,
    feature_flags: Dict[str, Any],
    system_prompt: str,
    request_message: str,
) -> str:
    skill_effectiveness_payload = build_skill_effectiveness_payload(
        selection_reason_code=selection_reason_code,
        selection_source=selection_source,
        selection_score=selection_score,
        selected_skill_spec=selected_skill_spec,
        visible_skill_count=visible_skill_count,
        available_skill_count=available_skill_count,
        always_injected_count=always_injected_count,
        selected_group_ids=selected_group_ids,
        resolved_skill_count=resolved_skill_count,
        summary_injected=summary_injected,
        scope_summary_injected=scope_summary_injected,
        effective_scope_count=effective_scope_count,
        feature_flags=feature_flags,
        system_prompt=system_prompt,
        request_message=request_message,
        estimate_tokens=estimate_tokens,
    )
    try:
        chat_service.add_skill_effectiveness_event(chat_id, skill_effectiveness_payload)
    except Exception:
        logger.exception("Failed to persist skill_effectiveness event")
    return emitter.emit(skill_effectiveness_payload)


def _resolve_skill_runtime_state(
    *,
    agent_config: Any,
    feature_flags: Dict[str, Any],
    chat_id: str,
    request_message: str,
    requested_skill: Optional[str],
) -> Dict[str, Any]:
    return prompting_resolve_skill_runtime_state(
        agent_config=agent_config,
        feature_flags=feature_flags,
        chat_id=chat_id,
        request_message=request_message,
        requested_skill=requested_skill,
        skill_router=skill_router,
        skill_registry=skill_registry,
        chat_service=chat_service,
        skill_bind_min_score=SKILL_BIND_MIN_SCORE,
        skill_switch_delta=SKILL_SWITCH_DELTA,
    ).__dict__

def _title_refinement_reason_distribution() -> Dict[str, Any]:
    return title_refinement_reason_distribution(_TITLE_REFINEMENT_REASON_COUNTS)


def _record_title_refinement_reason(reason: str) -> Dict[str, Any]:
    return record_title_refinement_reason(reason, _TITLE_REFINEMENT_REASON_COUNTS)


def _normalize_action_state_response(state: Any) -> ActionStateResponse:
    if hasattr(state, "model_dump"):
        return ActionStateResponse.model_validate(state.model_dump())
    return ActionStateResponse.model_validate(state)


async def _refine_title_once(
    chat_id: str,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None
) -> None:
    await refine_title_once(
        chat_id=chat_id,
        provider_override=provider_override,
        model_override=model_override,
        chat_service=chat_service,
        session_meta_service=session_meta_service,
        config_service=config_service,
        logger=logger,
        reason_counts=_TITLE_REFINEMENT_REASON_COUNTS,
    )

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
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.get("/{chat_id}/events")
async def get_chat_events(chat_id: str, assistant_turn_id: Optional[str] = None, after_sequence: Optional[int] = None):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_service.get_chat_events(chat_id, assistant_turn_id=assistant_turn_id, after_sequence=after_sequence)

@router.get("/{chat_id}/trace/bundle")
async def get_chat_trace_bundle(chat_id: str, assistant_turn_id: Optional[str] = None, mode: str = Query(default="summary")):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
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
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if invocation_id:
        if skill_name or action_id or approval_token:
            raise HTTPException(
                status_code=400,
                detail="Use exactly one lookup mode: invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state_by_invocation_id(
            chat_id,
            invocation_id=invocation_id,
        )
    elif approval_token:
        if skill_name or action_id:
            raise HTTPException(
                status_code=400,
                detail="Use exactly one lookup mode: invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state_by_approval_token(
            chat_id,
            approval_token=approval_token,
        )
    else:
        if bool(skill_name) != bool(action_id):
            raise HTTPException(
                status_code=400,
                detail="skill_name and action_id are required together when approval_token is not provided",
            )
        if not skill_name or not action_id:
            raise HTTPException(
                status_code=400,
                detail="Provide invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state(
            chat_id,
            skill_name=skill_name,
            action_id=action_id,
        )

    if state is None:
        raise HTTPException(status_code=404, detail="Action state not found")
    return _normalize_action_state_response(state)

@router.get("/{chat_id}/actions/states", response_model=list[ActionStateResponse])
async def list_action_states(chat_id: str):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
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
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
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
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    tags = chat_service.generate_chat_tags(chat_id)
    return {"tags": tags or []}

@router.get("/{chat_id}/meta")
async def get_chat_meta(chat_id: str):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
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
        chat = chat_service.create_chat(request.agent_id)
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

    deps = StreamRunnerDeps(
        logger=logger,
        agent_store=agent_store,
        tool_registry=tool_registry,
        fetch_ollama_models=fetch_ollama_models,
        get_model=get_model,
        chat_service=chat_service,
        config_service=config_service,
        build_system_prompt=build_system_prompt,
        get_parser=get_parser,
        calculate_usage=calculate_usage,
        handle_llm_exception=handle_llm_exception,
        prompt=PromptRuntimeDeps(
            skill_registry=skill_registry,
            skill_action_execution_service=skill_action_execution_service,
            markdown_skill_adapter=MarkdownSkillAdapter,
            skill_policy_gate=SkillPolicyGate,
            assemble_runtime_prompt=assemble_runtime_prompt,
            build_scope_summary_block=_build_scope_summary_block,
            emit_skill_effectiveness_event=_emit_skill_effectiveness_event,
            resolve_skill_runtime_state=_resolve_skill_runtime_state,
            action_preflight_message_builder=build_action_preflight_message,
            action_approval_message_builder=build_action_approval_message,
            action_execution_message_builder=build_action_execution_stub_message,
        ),
        retry=RetryRuntimeDeps(
            resolve_retry_targets=resolve_retry_targets,
            build_tool_call_retry_event=build_tool_call_retry_event,
            build_tool_call_retry_success_event=build_tool_call_retry_success_event,
            build_tool_call_retry_failed_event=build_tool_call_retry_failed_event,
            build_tool_call_mismatch_event=build_tool_call_mismatch_event,
            build_tool_call_mismatch_message=build_tool_call_mismatch_message,
        ),
        collect_tool_names=collect_tool_names,
        patch_model_settings=patch_model_settings,
        build_agent_deps=build_agent_deps,
        ensure_ollama_model_available=ensure_ollama_model_available,
        format_citations_suffix=format_citations_suffix,
        append_continue_message_if_needed=append_continue_message_if_needed,
        append_citation_suffix_if_needed=append_citation_suffix_if_needed,
        persist_assistant_message=persist_assistant_message,
        should_handle_tool_call_mismatch=should_handle_tool_call_mismatch,
        tool_event_tracker_cls=ToolEventTracker,
        normalize_finished_ts=normalize_finished_ts,
        serialize_sse_payload=serialize_sse_payload,
        iso_utc_now=iso_utc_now,
        resolve_reasoning_state=resolve_reasoning_state,
        build_runtime_meta_payload=build_runtime_meta_payload,
        run_agent_stream=_run_agent_stream,
        refine_title_once_fn=_refine_title_once,
        build_chat_response_log_payload=_build_chat_response_log_payload,
        safe_json_log=safe_json_log,
        env_flag=env_flag,
        env_flag_with_fallback=env_flag_with_fallback,
        agent_cls=Agent,
        usage_limits_cls=UsageLimits,
    )

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
