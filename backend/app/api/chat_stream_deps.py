import asyncio
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from pydantic_ai import Agent, UsageLimits

from app.api.chat_helpers import (
    build_runtime_meta_payload,
    iso_utc_now,
    resolve_reasoning_state,
    serialize_sse_payload,
)
from app.api.chat_schemas import ChatRequest
from app.api.chat_stream_runner_types import PromptRuntimeDeps, RetryRuntimeDeps, StreamRunnerDeps
from app.services import doc_retrieval
from app.services.agent_store import agent_store
from app.services.chat_postprocess import (
    record_title_refinement_reason,
    refine_title_once,
    title_refinement_reason_distribution,
)
from app.services.chat_prompting import (
    assemble_runtime_prompt,
    build_history_from_chat as prompting_build_history_from_chat,
    build_scope_summary_block as prompting_build_scope_summary_block,
    env_flag,
    env_flag_with_fallback,
    estimate_tokens,
    resolve_skill_runtime_state as prompting_resolve_skill_runtime_state,
    safe_int_env_with_fallback,
)
from app.services.chat_retry_service import (
    build_tool_call_mismatch_event,
    build_tool_call_mismatch_message,
    build_tool_call_retry_event,
    build_tool_call_retry_failed_event,
    build_tool_call_retry_success_event,
    resolve_retry_targets,
    should_handle_tool_call_mismatch,
)
from app.services.chat_runtime import (
    build_agent_deps,
    build_chat_request_log_payload as runtime_build_chat_request_log_payload,
    build_chat_response_log_payload as runtime_build_chat_response_log_payload,
    build_skill_effectiveness_payload,
    collect_tool_names,
    ensure_ollama_model_available,
    format_citations_suffix,
    patch_model_settings,
    persist_validated_images,
    safe_json_log,
)
from app.services.chat_service import ChatSession, chat_service
from app.services.chat_streaming import StreamEventEmitter, StreamState, stream_result_chunks
from app.services.config_service import config_service
from app.services.llm.utils import handle_llm_exception
from app.services.memory.session_context_host import yue_session_context_service
from app.services.model_factory import fetch_ollama_models, get_model
from app.services.multimodal_service import MultimodalService, MultimodalValidationError
from app.services.prompt_service import build_system_prompt
from app.services.response_parser_service import get_parser
from app.services.session_meta_service import session_meta_service
from app.services.skill_service import (
    build_stage4_lite_runtime_seams,
    get_stage4_lite_runtime_context,
)
from app.services.skills import (
    MarkdownSkillAdapter,
    SkillPolicyGate,
    build_action_approval_message,
    build_action_execution_stub_message,
    build_action_preflight_message,
)
from app.services.usage_service import calculate_usage
from app.utils.image_handler import load_image_to_base64, save_base64_image
from app.mcp.registry import tool_registry
from app.api.chat_tool_events import ToolEventTracker
from app.services.chat_postprocess import (
    append_citation_suffix_if_needed,
    append_continue_message_if_needed,
    normalize_finished_ts,
    persist_assistant_message,
)


logger = logging.getLogger(__name__)
SKILL_BIND_MIN_SCORE = 2
SKILL_SWITCH_DELTA = 2
_TITLE_REFINEMENT_REASON_COUNTS: Dict[str, int] = defaultdict(int)


def build_chat_request_log_payload(chat_id: str, request: ChatRequest) -> Dict[str, Any]:
    return runtime_build_chat_request_log_payload(
        chat_id,
        request,
        env_flag_with_fallback=env_flag_with_fallback,
        safe_int_env_with_fallback=safe_int_env_with_fallback,
    )


def build_chat_response_log_payload(
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


def build_scope_summary_block(agent_config: Any) -> Tuple[Optional[str], int]:
    return prompting_build_scope_summary_block(
        agent_config,
        config_service=config_service,
        doc_retrieval=doc_retrieval,
    )


def build_history_from_chat(existing_chat: Optional[ChatSession]) -> List[Any]:
    return prompting_build_history_from_chat(
        existing_chat,
        load_image_to_base64=load_image_to_base64,
        logger=logger,
    )


async def yield_stream_chunks(
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


async def run_agent_stream(
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
        async for payload in yield_stream_chunks(
            result=stream_result,
            parser=parser,
            tool_event_queue=tool_event_queue,
            emitter=emitter,
            stream_state=stream_state,
            log_label=log_label,
        ):
            yield payload


def emit_skill_effectiveness_event(
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


def resolve_skill_runtime_state(
    *,
    agent_config: Any,
    feature_flags: Dict[str, Any],
    chat_id: str,
    request_message: str,
    requested_skill: Optional[str],
    runtime_seams: Any = None,
    runtime_context: Any = None,
) -> Dict[str, Any]:
    context = runtime_context or get_stage4_lite_runtime_context()
    runtime_seams = runtime_seams or build_stage4_lite_runtime_seams(
        import_store=context.skill_import_store,
        router=context.skill_router,
    )
    return prompting_resolve_skill_runtime_state(
        agent_config=agent_config,
        feature_flags=feature_flags,
        chat_id=chat_id,
        request_message=request_message,
        requested_skill=requested_skill,
        skill_router=context.skill_router,
        skill_registry=context.skill_registry,
        chat_service=chat_service,
        skill_bind_min_score=SKILL_BIND_MIN_SCORE,
        skill_switch_delta=SKILL_SWITCH_DELTA,
        runtime_seams=runtime_seams,
    ).__dict__


def assemble_runtime_prompt_with_context(*, runtime_seams: Any = None, runtime_context: Any = None, **kwargs: Any) -> Any:
    context = runtime_context or get_stage4_lite_runtime_context()
    runtime_seams = runtime_seams or build_stage4_lite_runtime_seams(
        import_store=context.skill_import_store,
        router=context.skill_router,
    )
    return assemble_runtime_prompt(runtime_seams=runtime_seams, **kwargs)


def bind_runtime_prompt_helpers(runtime_context: Any) -> Dict[str, Any]:
    def _resolve_bound(**kwargs: Any) -> Dict[str, Any]:
        return resolve_skill_runtime_state(runtime_context=runtime_context, **kwargs)

    def _assemble_bound(**kwargs: Any) -> Any:
        return assemble_runtime_prompt_with_context(runtime_context=runtime_context, **kwargs)

    return {
        "resolve_skill_runtime_state": _resolve_bound,
        "assemble_runtime_prompt": _assemble_bound,
    }


def title_refinement_reason_distribution_payload() -> Dict[str, Any]:
    return title_refinement_reason_distribution(_TITLE_REFINEMENT_REASON_COUNTS)


def record_title_refinement_reason_payload(reason: str) -> Dict[str, Any]:
    return record_title_refinement_reason(reason, _TITLE_REFINEMENT_REASON_COUNTS)


async def refine_title_once_for_chat(
    chat_id: str,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
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


def build_stream_runner_deps() -> StreamRunnerDeps:
    runtime_context = get_stage4_lite_runtime_context()
    prompt_helpers = bind_runtime_prompt_helpers(runtime_context)
    return StreamRunnerDeps(
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
            skill_registry=runtime_context.skill_registry,
            skill_action_execution_service=runtime_context.skill_action_execution_service,
            markdown_skill_adapter=MarkdownSkillAdapter,
            skill_policy_gate=SkillPolicyGate,
            assemble_runtime_prompt=prompt_helpers["assemble_runtime_prompt"],
            build_scope_summary_block=build_scope_summary_block,
            emit_skill_effectiveness_event=emit_skill_effectiveness_event,
            resolve_skill_runtime_state=prompt_helpers["resolve_skill_runtime_state"],
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
        run_agent_stream=run_agent_stream,
        refine_title_once_fn=refine_title_once_for_chat,
        build_chat_response_log_payload=build_chat_response_log_payload,
        safe_json_log=safe_json_log,
        env_flag=env_flag,
        env_flag_with_fallback=env_flag_with_fallback,
        agent_cls=Agent,
        usage_limits_cls=UsageLimits,
    )


__all__ = [
    "MultimodalService",
    "MultimodalValidationError",
    "build_chat_request_log_payload",
    "build_history_from_chat",
    "build_stream_runner_deps",
    "config_service",
    "env_flag",
    "env_flag_with_fallback",
    "logger",
    "persist_validated_images",
    "record_title_refinement_reason_payload",
    "safe_json_log",
    "save_base64_image",
    "title_refinement_reason_distribution_payload",
]
