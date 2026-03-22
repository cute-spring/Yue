from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ImageUrl
from app.mcp.registry import tool_registry
from app.services.agent_store import agent_store
from app.services.model_factory import get_model, fetch_ollama_models
from app.services.chat_service import chat_service, ChatSession
from app.services.config_service import config_service
from app.services.prompt_service import build_system_prompt
from app.services.response_parser_service import get_parser
from app.services.contract_gate import validate_sse_payload
from app.services.usage_service import calculate_usage
from app.services.llm.utils import handle_llm_exception
from app.services.multimodal_service import MultimodalService, MultimodalValidationError
from app.services.session_meta_service import session_meta_service
from app.services.skill_service import skill_registry, skill_router, SkillPolicyGate, MarkdownSkillAdapter
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
    is_placeholder_title,
    refine_title_once,
    normalize_finished_ts,
    append_continue_message_if_needed,
    append_citation_suffix_if_needed,
    persist_assistant_message,
)
from app.utils.image_handler import save_base64_image, load_image_to_base64
import time
import asyncio
import uuid
import json
import logging
from collections import defaultdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

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

def _safe_json_log(payload: Dict[str, Any]) -> str:
    return safe_json_log(payload)


def _serialize_sse_payload(payload: Dict[str, Any]) -> str:
    try:
        validate_sse_payload(payload)
        return f"data: {json.dumps(payload)}\n\n"
    except Exception as err:
        logger.exception("SSE contract validation failed")
        safe_payload = {
            "error": f"stream_contract_violation: {err.__class__.__name__}"
        }
        return f"data: {json.dumps(safe_payload)}\n\n"

def _build_scope_summary_block(agent_config: Any) -> Tuple[Optional[str], int]:
    return prompting_build_scope_summary_block(
        agent_config,
        config_service=config_service,
        doc_retrieval=doc_retrieval,
    )


def _build_history_from_chat(existing_chat: Optional[ChatSession]) -> List[Any]:
    return prompting_build_history_from_chat(existing_chat, load_image_to_base64=load_image_to_base64, logger=logger)


def _persist_validated_images(validated_images: List[str]) -> List[str]:
    return persist_validated_images(validated_images, save_base64_image=save_base64_image, logger=logger)


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

def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _title_refinement_reason_distribution() -> Dict[str, Any]:
    return title_refinement_reason_distribution(_TITLE_REFINEMENT_REASON_COUNTS)

def _record_title_refinement_reason(reason: str) -> Dict[str, Any]:
    return record_title_refinement_reason(reason, _TITLE_REFINEMENT_REASON_COUNTS)

def _is_placeholder_title(chat: ChatSession) -> bool:
    return is_placeholder_title(chat)

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

class ChatRequest(BaseModel):
    message: str
    images: list[str] | None = None
    agent_id: str | None = None
    requested_skill: str | None = None
    chat_id: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    deep_thinking_enabled: bool = False

@router.get("/history", response_model=list[ChatSession])
async def list_chats():
    return chat_service.list_chats()

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

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    if not chat_service.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

class TruncateRequest(BaseModel):
    keep_count: int

class SummaryGenerateRequest(BaseModel):
    force: bool = False

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
    stored_images = _persist_validated_images(validated_images)

    if env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
        logger.info(
            "BACKLOG_CHAT_REQUEST %s",
            _safe_json_log(_build_chat_request_log_payload(chat_id, request)),
        )

    chat_service.add_message(chat_id, "user", request.message, images=stored_images if stored_images else None)
    
    async def event_generator():
        feature_flags = config_service.get_feature_flags()
        event_v2_enabled = bool(feature_flags.get("transparency_event_v2_enabled", True))
        turn_binding_enabled = bool(feature_flags.get("transparency_turn_binding_enabled", True))
        reasoning_display_gated_enabled = bool(feature_flags.get("reasoning_display_gated_enabled", True))
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        assistant_turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        emitter = StreamEventEmitter(
            event_v2_enabled=event_v2_enabled,
            run_id=run_id,
            assistant_turn_id=assistant_turn_id,
            serialize_payload=_serialize_sse_payload,
            iso_utc_now=_iso_utc_now,
        )

        yield emitter.emit({"chat_id": chat_id})

        tool_event_queue = asyncio.Queue()
        tool_call_started_count = 0
        tool_call_finished_count = 0

        async def on_tool_event(event: Dict[str, Any]):
            nonlocal tool_call_started_count, tool_call_finished_count
            try:
                event_payload = emitter.event_payload(event)
                await tool_event_queue.put(event_payload)
                event_type = event_payload.get("event")
                if event_type == "tool.call.started":
                    tool_call_started_count += 1
                    chat_service.add_tool_call(
                        session_id=chat_id,
                        call_id=event_payload.get("call_id"),
                        tool_name=event_payload.get("tool_name"),
                        args=event_payload.get("args"),
                        assistant_turn_id=assistant_turn_id if turn_binding_enabled else None,
                        run_id=run_id if turn_binding_enabled else None,
                        event_id_started=event_payload.get("event_id"),
                        started_sequence=event_payload.get("sequence"),
                        started_ts=normalize_finished_ts(event_payload.get("ts"))
                    )
                elif event_type == "tool.call.finished":
                    tool_call_finished_count += 1
                    chat_service.update_tool_call(
                        call_id=event_payload.get("call_id"),
                        status="error" if "error" in event_payload else "success",
                        result=event_payload.get("result"),
                        error=event_payload.get("error"),
                        duration_ms=event_payload.get("duration_ms"),
                        event_id_finished=event_payload.get("event_id"),
                        finished_sequence=event_payload.get("sequence"),
                        finished_ts=normalize_finished_ts(event_payload.get("ts"))
                    )
            except Exception:
                logger.exception("Error in on_tool_event (streaming + persistence)")

        stream_state = StreamState()
        thought_duration = None
        ttft = None
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        finish_reason = None
        total_duration = None
        stream_error_message = None
        provider = request.provider
        model_name = request.model
        supports_reasoning = False
        reasoning_enabled = False

        try:
            # Get agent config if provided
            agent_config = None
            if request.agent_id:
                agent_config = agent_store.get_agent(request.agent_id)
            
            # Determine model and system prompt
            provider = request.provider
            model_name = request.model
            system_prompt = request.system_prompt
            
            # --- Markdown-Defined Skills (Phase 6.2) ---
            skill_runtime_state = _resolve_skill_runtime_state(
                agent_config=agent_config,
                feature_flags=feature_flags,
                chat_id=chat_id,
                request_message=request.message,
                requested_skill=request.requested_skill,
            )
            selected_skill_spec = skill_runtime_state["selected_skill_spec"]
            always_skill_specs = skill_runtime_state["always_skill_specs"]
            selection_reason_code = skill_runtime_state["selection_reason_code"]
            selection_source = skill_runtime_state["selection_source"]
            selection_score = skill_runtime_state["selection_score"]
            visible_skill_count = skill_runtime_state["visible_skill_count"]
            available_skill_count = skill_runtime_state["available_skill_count"]
            always_injected_count = skill_runtime_state["always_injected_count"]
            selected_group_ids = skill_runtime_state["selected_group_ids"]
            resolved_skill_count = skill_runtime_state["resolved_skill_count"]
            summary_block = skill_runtime_state["summary_block"]
                
            prompt_result = assemble_runtime_prompt(
                agent_config=agent_config,
                request_system_prompt=system_prompt,
                request_message=request.message,
                provider=provider,
                model_name=model_name,
                selected_skill_spec=selected_skill_spec,
                always_skill_specs=always_skill_specs,
                summary_block=summary_block,
                feature_flags=feature_flags,
                skill_registry=skill_registry,
                markdown_skill_adapter=MarkdownSkillAdapter,
                skill_policy_gate=SkillPolicyGate,
                build_scope_summary_block=_build_scope_summary_block,
            )
            selected_skill_spec = prompt_result.selected_skill_spec
            provider = prompt_result.provider
            model_name = prompt_result.model_name
            system_prompt = prompt_result.system_prompt
            final_tools_list = prompt_result.final_tools_list
            always_injected_count = prompt_result.always_injected_count
            summary_injected = prompt_result.summary_injected
            scope_summary_injected = prompt_result.scope_summary_injected
            effective_scope_count = prompt_result.effective_scope_count
            if prompt_result.emitted_event:
                logger.info("Skill %s selected. Tool intersection: %s", selected_skill_spec.name, final_tools_list)
                yield emitter.emit(prompt_result.emitted_event)

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
                request_message=request.message,
                estimate_tokens=estimate_tokens,
            )
            try:
                chat_service.add_skill_effectiveness_event(chat_id, skill_effectiveness_payload)
            except Exception:
                logger.exception("Failed to persist skill_effectiveness event")
            yield emitter.emit(skill_effectiveness_payload)

            model_name, ollama_error = await ensure_ollama_model_available(
                provider=provider,
                model_name=model_name,
                fetch_ollama_models=fetch_ollama_models,
            )
            if ollama_error:
                yield emitter.emit(ollama_error)
                return

            tools = await tool_registry.get_pydantic_ai_tools_for_agent(
                request.agent_id, 
                provider,
                on_event=on_tool_event,
                event_context=lambda: {
                    "run_id": run_id,
                    "assistant_turn_id": assistant_turn_id
                },
                enabled_tools=final_tools_list
            )

            tool_names = collect_tool_names(tools)

            model_capabilities = config_service.get_model_capabilities(provider, model_name)
            vision_decision = multimodal_service.decide_vision(
                model_capabilities=model_capabilities,
                request_has_images=bool(validated_images),
                fallback_enabled=bool(feature_flags.get("multimodal_vision_fallback_enabled", False)),
            )
            supports_vision = bool(vision_decision["supports_vision"])
            vision_enabled = bool(vision_decision["vision_enabled"])
            fallback_mode = str(vision_decision["fallback_mode"])
            if fallback_mode == "reject":
                yield emitter.emit({
                    "error": "当前模型不支持图片理解，请切换支持视觉的模型后重试。",
                    "error_code": "MODEL_VISION_UNSUPPORTED",
                    "supports_vision": supports_vision,
                    "vision_enabled": vision_enabled,
                })
                return
            supports_reasoning = "reasoning" in model_capabilities
            reasoning_disabled_reason_code = None
            if reasoning_display_gated_enabled:
                reasoning_enabled = bool(supports_reasoning and request.deep_thinking_enabled)
                if not reasoning_enabled:
                    if request.deep_thinking_enabled and not supports_reasoning:
                        reasoning_disabled_reason_code = "MODEL_CAPABILITY_MISSING"
                    elif not request.deep_thinking_enabled:
                        reasoning_disabled_reason_code = "DEEP_THINKING_DISABLED"
            else:
                reasoning_enabled = bool(supports_reasoning or request.deep_thinking_enabled)
                if not reasoning_enabled:
                    reasoning_disabled_reason_code = "LEGACY_DISABLED"
            meta_payload = {
                "meta": {
                    "provider": provider,
                    "model": model_name,
                    "tools": tool_names,
                    "context_id": chat_id,
                    "agent_id": request.agent_id,
                    "run_id": run_id,
                    "assistant_turn_id": assistant_turn_id if turn_binding_enabled else None,
                    "supports_reasoning": supports_reasoning,
                    "deep_thinking_enabled": bool(request.deep_thinking_enabled),
                    "reasoning_enabled": reasoning_enabled,
                    "reasoning_disabled_reason_code": reasoning_disabled_reason_code,
                    "supports_vision": supports_vision,
                    "vision_enabled": vision_enabled,
                    "image_count": len(validated_images),
                    "vision_fallback_mode": fallback_mode,
                }
            }
            yield emitter.emit(meta_payload)
            if request.deep_thinking_enabled and not reasoning_enabled and reasoning_disabled_reason_code:
                yield emitter.emit({
                    "event": "reasoning_toggle_ignored",
                    "reason_code": reasoning_disabled_reason_code
                })
            
            system_prompt = build_system_prompt(
                base_prompt=system_prompt,
                provider=provider,
                model_name=model_name,
                user_message=request.message,
                deep_thinking_enabled=reasoning_enabled
            )

            try:
                model = get_model(provider, model_name)
            except Exception as model_err:
                if env_flag("PYTEST_CURRENT_TEST", False):
                    model = object()
                else:
                    raise model_err

            # Create Pydantic AI Agent
            agent = Agent(
                model,
                system_prompt=system_prompt,
                tools=tools
            )
            deps = build_agent_deps(agent_config)
            
            # Retrieve model settings (max_tokens etc)
            model_settings = patch_model_settings(config_service.get_model_settings(provider, model_name))
            
            # Retrieve usage limits policy
            tier = "default"
            if agent_config and getattr(agent_config, "tier", None):
                tier = agent_config.tier
            usage_policy = config_service.get_usage_limits(tier)
            usage_limits = UsageLimits(
                request_limit=usage_policy.get("request_limit"),
                tool_calls_limit=usage_policy.get("tool_calls_limit")
            )

            # Prepare Parser (Adapter Pattern)
            parser = get_parser(provider, model_name, model_capabilities)
            
            start_time = time.time()
            
            try:
                user_input = multimodal_service.build_user_input(
                    message=request.message,
                    validated_images=validated_images,
                    vision_enabled=vision_enabled,
                )

                # Run with history and model settings
                async with agent.run_stream(user_input, message_history=history, deps=deps, model_settings=model_settings, usage_limits=usage_limits) as result:
                    async for payload in stream_result_chunks(
                        result=result,
                        parser=parser,
                        tool_event_queue=tool_event_queue,
                        emitter=emitter,
                        stream_state=stream_state,
                        serialize_payload=_serialize_sse_payload,
                        logger=logger,
                        log_label="stream_iter",
                    ):
                        yield payload

            except UsageLimitExceeded as limit_err:
                logger.warning(f"Usage limit exceeded for run {chat_id}: {limit_err}")
                # Emit run.limited event
                limit_info = {
                    "event": "run.limited",
                    "reason": str(limit_err),
                    "snapshot": {}
                }
                # Try to get usage snapshot from the result if it was already partially through
                try:
                    if 'result' in locals() and hasattr(result, "usage"):
                        raw_usage = result.usage()
                        if asyncio.iscoroutine(raw_usage):
                            raw_usage = await raw_usage
                        limit_info["snapshot"] = raw_usage.model_dump() if hasattr(raw_usage, "model_dump") else str(raw_usage)
                except:
                    pass
                
                yield emitter.emit(limit_info)
                
                # Provide a friendly user message
                friendly_msg = f"\n\n> ⚠️ **[系统提示]** 已触达策略上限（{limit_err}）。为了您的账户安全和成本控制，本轮执行已自动停止。您可以根据已有信息继续，或尝试缩小问题范围。"
                stream_state.full_response += friendly_msg
                yield emitter.emit({"content": friendly_msg})

            except Exception as stream_err:
                err_str = str(stream_err)
                if "status_code: 502" in err_str and provider == "ollama":
                    yield emitter.emit({"error": "Ollama 返回 502，请检查模型是否已拉取且服务正常运行"})
                    return
                
                # Check for TLS/SSL or Proxy errors
                friendly_error = handle_llm_exception(stream_err)
                if friendly_error != err_str:
                    yield emitter.emit({"error": friendly_error})
                    return

                if "does not support tools" in err_str or "Tool use is not supported" in err_str:
                    logger.info("Model %s does not support tools, falling back to pure chat.", model_name)
                    # Re-create agent without tools
                    agent_no_tools = Agent(model, system_prompt=system_prompt)
                    # Reset parser and response tracking for second attempt
                    parser = get_parser(provider, model_name, model_capabilities)
                    stream_state = StreamState()
                    
                    # Prepare input
                    user_input = request.message
                    if vision_enabled:
                        user_input = [request.message]
                        for img in validated_images:
                            user_input.append(ImageUrl(url=img))

                    async with agent_no_tools.run_stream(user_input, message_history=history, deps=deps, model_settings=model_settings) as result:
                        async for payload in stream_result_chunks(
                            result=result,
                            parser=parser,
                            tool_event_queue=tool_event_queue,
                            emitter=emitter,
                            stream_state=stream_state,
                            serialize_payload=_serialize_sse_payload,
                            logger=logger,
                            log_label="stream_iter (fallback)",
                        ):
                            yield payload
                else:
                    raise stream_err
            
            # Calculate duration
            total_end_time = time.time()
            total_duration = total_end_time - start_time
            if stream_state.first_token_time:
                ttft = stream_state.first_token_time - start_time

            if parser.thought_start_time:
                if parser.thought_end_time:
                    thought_duration = parser.thought_end_time - parser.thought_start_time
                else:
                    thought_duration = time.time() - parser.thought_start_time

            if thought_duration is not None:
                yield emitter.emit({"thought_duration": thought_duration})

            if ttft is not None:
                yield emitter.emit({"ttft": ttft})
            
            yield emitter.emit({"total_duration": total_duration})

            # Capture Usage and Finish Reason using UsageAdapter (Adapter Pattern)
            try:
                finish_reason_val = getattr(getattr(result, "response", None), "finish_reason", None)
                if not isinstance(finish_reason_val, str):
                    finish_reason_val = None
                raw_usage = result.usage()
                if asyncio.iscoroutine(raw_usage):
                    raw_usage = await raw_usage
                usage_stats = calculate_usage(
                    provider=provider,
                    raw_usage=raw_usage,
                    duration=total_duration,
                    finish_reason=finish_reason_val
                )
                
                # Update local variables for chat_service.add_message
                prompt_tokens = usage_stats.prompt_tokens
                completion_tokens = usage_stats.completion_tokens
                total_tokens = usage_stats.total_tokens
                finish_reason = usage_stats.finish_reason
                
                yield emitter.emit(usage_stats.model_dump())

                # Manual continuation guidance logic
                continue_payload = append_continue_message_if_needed(
                    finish_reason=finish_reason,
                    stream_state=stream_state,
                )
                if continue_payload:
                    yield emitter.emit(continue_payload)
                elif finish_reason == "tool_call" and tool_call_started_count == 0:
                    mismatch_resolved = False
                    mismatch_config = config_service.get_tool_call_mismatch_config()
                    if mismatch_config.get("auto_retry_enabled", True):
                        retry_candidates_raw = mismatch_config.get("fallback_models") or [mismatch_config.get("fallback_model", "")]
                        retry_candidates = [str(item).strip() for item in retry_candidates_raw if str(item).strip()]
                        seen_retry_targets = set()
                        current_target = f"{provider}/{model_name}".strip().lower()
                        for retry_target in retry_candidates:
                            retry_provider = provider
                            retry_model_name = retry_target
                            if "/" in retry_target:
                                maybe_provider, maybe_model = retry_target.split("/", 1)
                                if maybe_provider.strip() and maybe_model.strip():
                                    retry_provider = maybe_provider.strip()
                                    retry_model_name = maybe_model.strip()
                            normalized_target = f"{retry_provider}/{retry_model_name}".strip().lower()
                            if not retry_model_name or normalized_target == current_target or normalized_target in seen_retry_targets:
                                continue
                            seen_retry_targets.add(normalized_target)
                            try:
                                yield emitter.emit({"event": "tool_call_retry", "from_provider": provider, "from_model": model_name, "to_provider": retry_provider, "to_model": retry_model_name})
                                retry_model = get_model(retry_provider, retry_model_name)
                                retry_model_settings = patch_model_settings(config_service.get_model_settings(retry_provider, retry_model_name))
                                retry_capabilities = config_service.get_model_capabilities(retry_provider, retry_model_name)
                                retry_parser = get_parser(retry_provider, retry_model_name, retry_capabilities)
                                retry_agent = Agent(
                                    retry_model,
                                    system_prompt=system_prompt,
                                    tools=tools
                                )
                                retry_input = multimodal_service.build_user_input(
                                    message=request.message,
                                    validated_images=validated_images,
                                    vision_enabled=vision_enabled,
                                )
                                async with retry_agent.run_stream(
                                    retry_input,
                                    message_history=history,
                                    deps=deps,
                                    model_settings=retry_model_settings,
                                    usage_limits=usage_limits
                                ) as retry_result:
                                    async for payload in stream_result_chunks(
                                        result=retry_result,
                                        parser=retry_parser,
                                        tool_event_queue=tool_event_queue,
                                        emitter=emitter,
                                        stream_state=stream_state,
                                        serialize_payload=_serialize_sse_payload,
                                        logger=logger,
                                        log_label="retry stream_iter",
                                    ):
                                        yield payload
                                    retry_finish_reason = getattr(getattr(retry_result, "response", None), "finish_reason", None)
                                    if tool_call_started_count > 0 or retry_finish_reason != "tool_call":
                                        mismatch_resolved = True
                                if mismatch_resolved:
                                    yield emitter.emit({"event": "tool_call_retry_success", "provider": retry_provider, "model": retry_model_name, "started": tool_call_started_count, "finished": tool_call_finished_count})
                                    break
                            except Exception as retry_err:
                                logger.exception("Auto retry after tool_call mismatch failed")
                                yield emitter.emit({"event": "tool_call_retry_failed", "provider": retry_provider, "model": retry_model_name, "error": str(retry_err)})
                    if not mismatch_resolved:
                        tool_msg = (
                            "\n\n> ⚠️ **[系统提示]** 模型返回了 `tool_call` 结束信号，但未产生可执行工具调用。"
                            "这通常是当前模型与工具调用协议兼容性问题。"
                            "建议切换到已验证支持工具调用的模型（例如 `gpt-4o`/`gpt-4o-mini`），"
                            "或重试并明确要求“立即调用工具后再回答”。"
                        )
                        stream_state.full_response += tool_msg
                        yield emitter.emit({"event": "tool_call_mismatch", "started": tool_call_started_count, "finished": tool_call_finished_count})
                        yield emitter.emit({"content": tool_msg})
            except Exception as usage_err:
                logger.error(f"Failed to get usage via adapter: {usage_err}")

            citations = deps.get("citations") if isinstance(deps, dict) else None
            if isinstance(citations, list) and citations:
                yield emitter.emit({"citations": citations})

            require_citations = bool(getattr(agent_config, "require_citations", False)) if agent_config else False
            citation_payload = append_citation_suffix_if_needed(
                citations=citations,
                require_citations=require_citations,
                format_citations_suffix=format_citations_suffix,
                stream_state=stream_state,
            )
            if citation_payload:
                yield emitter.emit(citation_payload)

        except (Exception, GeneratorExit, asyncio.CancelledError) as e:
            if isinstance(e, (GeneratorExit, asyncio.CancelledError)):
                logger.info("Chat stream cancelled by client")
                stream_error_message = e.__class__.__name__
            else:
                stream_error_message = str(e)
                logger.exception("Chat error")
                yield emitter.emit({"error": handle_llm_exception(e)})
        finally:
            # Save Assistant Message after completion
            saved = persist_assistant_message(
                chat_service=chat_service,
                chat_id=chat_id,
                stream_state=stream_state,
                thought_duration=thought_duration,
                ttft=ttft,
                total_duration=total_duration,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
                current_exception=e if 'e' in locals() else None,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
                turn_binding_enabled=turn_binding_enabled,
                supports_reasoning=supports_reasoning,
                deep_thinking_enabled=bool(request.deep_thinking_enabled),
                reasoning_enabled=reasoning_enabled,
            )
            if saved:
                asyncio.create_task(_refine_title_once(chat_id, provider_override=provider, model_override=model_name))
            if env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
                logger.info(
                    "BACKLOG_CHAT_RESPONSE %s",
                    _safe_json_log(
                        _build_chat_response_log_payload(
                            chat_id=chat_id,
                            provider=provider,
                            model_name=model_name,
                            finish_reason=finish_reason or (e.__class__.__name__ if 'e' in locals() and isinstance(e, (GeneratorExit, asyncio.CancelledError)) else None),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            ttft=ttft,
                            total_duration=total_duration,
                            tool_call_started_count=tool_call_started_count,
                            tool_call_finished_count=tool_call_finished_count,
                            full_response=stream_state.full_response,
                            error=stream_error_message,
                        )
                    ),
                )

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/skill-effectiveness/report")
async def get_skill_effectiveness_report(hours: int = 24):
    if hours <= 0 or hours > 24 * 30:
        raise HTTPException(status_code=400, detail="hours_out_of_range")
    return chat_service.get_skill_effectiveness_report(hours=hours)

@router.get("/title-refinement/reasons")
async def get_title_refinement_reason_distribution():
    return _title_refinement_reason_distribution()
