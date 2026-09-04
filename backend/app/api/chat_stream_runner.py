import asyncio
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic_ai.exceptions import UsageLimitExceeded

from app.api.chat_stream_types import StreamRunContext, StreamRunMetrics
from app.api.chat_stream_runner_preparation import (
    create_stream_runtime as _create_stream_runtime,
    prepare_runtime_dependencies as _prepare_runtime_dependencies,
)
from app.api.chat_stream_runner_types import (
    PreparedRuntime,
    PromptRuntimeDeps,
    RetryRuntimeDeps,
    StreamRunnerDeps,
)
from app.api.chat_stream_runner_actions import (
    build_requested_action_content as _build_requested_action_content,
    drain_tool_event_queue as _drain_tool_event_queue,
    emit_jira_action_preview_events as _emit_jira_action_preview_events,
    resolve_requested_action_request_id as _resolve_requested_action_request_id,
    resolve_requested_action_service as _resolve_requested_action_service,
    resolve_requested_action_skill_fallback as _resolve_requested_action_skill_fallback,
    resolve_requested_action_tool_args as _resolve_requested_action_tool_args,
    split_skill_ref as _split_skill_ref,
    invoke_requested_action_platform_tool as _invoke_requested_action_platform_tool,
)
from app.api.chat_stream_runner_helpers import (
    build_authoritative_session_context_user_hint as _build_authoritative_session_context_user_hint,
    continuation_content_type_for_request as _continuation_content_type_for_request,
    continuation_root_for_request as _continuation_root_for_request,
    continuation_status_for_request as _continuation_status_for_request,
    safe_int as _safe_int,
    safe_role_lookup as _safe_role_lookup,
    safe_text as _safe_text,
)
from app.services.chat_streaming import StreamEventEmitter, StreamState


async def _resolve_result_usage(result: Any) -> Any:
    raw_usage = getattr(result, "usage", None)
    if callable(raw_usage):
        raw_usage = raw_usage()
    if asyncio.iscoroutine(raw_usage):
        raw_usage = await raw_usage
    return raw_usage


async def _handle_tool_call_mismatch_retry(
    *,
    ctx: StreamRunContext,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    mismatch_resolved = False
    mismatch_config = deps.config_service.get_tool_call_mismatch_config()
    retry_targets = deps.retry.resolve_retry_targets(
        mismatch_config=mismatch_config,
        provider=ctx.provider,
        model_name=ctx.model_name,
    )
    for retry_target in retry_targets:
        retry_provider = retry_target.provider
        retry_model_name = retry_target.model_name
        try:
            yield prepared.emitter.emit(
                deps.retry.build_tool_call_retry_event(
                    from_provider=ctx.provider,
                    from_model=ctx.model_name,
                    to_provider=retry_provider,
                    to_model=retry_model_name,
                )
            )
            retry_model = deps.get_model(retry_provider, retry_model_name)
            retry_model_settings = deps.patch_model_settings(
                deps.config_service.get_model_settings(retry_provider, retry_model_name)
            )
            retry_capabilities = deps.config_service.get_model_capabilities(retry_provider, retry_model_name)
            retry_parser = deps.get_parser(retry_provider, retry_model_name, retry_capabilities)
            retry_input = prepared.multimodal_service.build_user_input(
                message=prepared.request.message,
                validated_images=prepared.validated_images,
                vision_enabled=prepared.vision_enabled,
            )
            retry_result_holder = {}
            async for payload in deps.run_agent_stream(
                agent=deps.agent_cls(
                    retry_model,
                    system_prompt=ctx.system_prompt,
                    tools=prepared.tools,
                ),
                user_input=retry_input,
                history=ctx.history,
                deps=ctx.deps,
                model_settings=retry_model_settings,
                parser=retry_parser,
                tool_event_queue=ctx.tool_event_queue,
                emitter=prepared.emitter,
                stream_state=ctx.stream_state,
                log_label="retry stream_iter",
                result_holder=retry_result_holder,
                usage_limits=ctx.usage_limits,
            ):
                yield payload
            retry_result = retry_result_holder.get("result")
            retry_finish_reason = getattr(getattr(retry_result, "response", None), "finish_reason", None)
            if prepared.tool_tracker.counts["started"] > 0 or retry_finish_reason != "tool_call":
                mismatch_resolved = True
            if mismatch_resolved:
                yield prepared.emitter.emit(
                    deps.retry.build_tool_call_retry_success_event(
                        provider=retry_provider,
                        model=retry_model_name,
                        started=prepared.tool_tracker.counts["started"],
                        finished=prepared.tool_tracker.counts["finished"],
                    )
                )
                break
        except Exception as retry_err:
            deps.logger.exception("Auto retry after tool_call mismatch failed")
            yield prepared.emitter.emit(
                deps.retry.build_tool_call_retry_failed_event(
                    provider=retry_provider,
                    model=retry_model_name,
                    error=str(retry_err),
                )
            )
    if not mismatch_resolved:
        tool_msg = deps.retry.build_tool_call_mismatch_message()
        ctx.stream_state.full_response += tool_msg
        yield prepared.emitter.emit(
            deps.retry.build_tool_call_mismatch_event(
                started=prepared.tool_tracker.counts["started"],
                finished=prepared.tool_tracker.counts["finished"],
            )
        )
        yield prepared.emitter.emit({"content": tool_msg})


async def _execute_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    start_time = time.time()
    try:
        user_input = prepared.multimodal_service.build_user_input(
            message=prepared.request.message,
            validated_images=prepared.validated_images,
            vision_enabled=prepared.vision_enabled,
        )

        result_holder: Dict[str, Any] = {}
        async for payload in deps.run_agent_stream(
            agent=deps.agent_cls(
                prepared.model,
                system_prompt=ctx.system_prompt,
                tools=prepared.tools,
            ),
            user_input=user_input,
            history=ctx.history,
            deps=ctx.deps,
            model_settings=ctx.model_settings,
            parser=ctx.parser,
            tool_event_queue=ctx.tool_event_queue,
            emitter=prepared.emitter,
            stream_state=ctx.stream_state,
            log_label="stream_iter",
            result_holder=result_holder,
            usage_limits=ctx.usage_limits,
        ):
            yield payload
        ctx.result = result_holder.get("result")

    except UsageLimitExceeded as limit_err:
        deps.logger.warning("Usage limit exceeded for run %s: %s", ctx.chat_id, limit_err)
        limit_info = {"event": "run.limited", "reason": str(limit_err), "snapshot": {}}
        try:
            if ctx.result is not None and hasattr(ctx.result, "usage"):
                raw_usage = await _resolve_result_usage(ctx.result)
                limit_info["snapshot"] = raw_usage.model_dump() if hasattr(raw_usage, "model_dump") else str(raw_usage)
        except Exception:
            pass
        yield prepared.emitter.emit(limit_info)
        friendly_msg = f"\n\n> ⚠️ **[系统提示]** 已触达策略上限（{limit_err}）。为了您的账户安全和成本控制，本轮执行已自动停止。您可以根据已有信息继续，或尝试缩小问题范围。"
        ctx.stream_state.full_response += friendly_msg
        yield prepared.emitter.emit({"content": friendly_msg})

    except Exception as stream_err:
        err_str = str(stream_err)
        if "status_code: 502" in err_str and ctx.provider == "ollama":
            yield prepared.emitter.emit({"error": "Ollama 返回 502，请检查模型是否已拉取且服务正常运行"})
            return

        friendly_error = deps.handle_llm_exception(stream_err)
        if friendly_error != err_str:
            yield prepared.emitter.emit({"error": friendly_error})
            return

        if "does not support tools" in err_str or "Tool use is not supported" in err_str:
            deps.logger.info("Model %s does not support tools, falling back to pure chat.", ctx.model_name)
            ctx.parser = deps.get_parser(ctx.provider, ctx.model_name, prepared.model_capabilities)
            ctx.stream_state = StreamState()
            user_input = prepared.multimodal_service.build_user_input(
                message=prepared.request.message,
                validated_images=prepared.validated_images,
                vision_enabled=prepared.vision_enabled,
            )
            result_holder = {}
            async for payload in deps.run_agent_stream(
                agent=deps.agent_cls(prepared.model, system_prompt=ctx.system_prompt),
                user_input=user_input,
                history=ctx.history,
                deps=ctx.deps,
                model_settings=ctx.model_settings,
                parser=ctx.parser,
                tool_event_queue=ctx.tool_event_queue,
                emitter=prepared.emitter,
                stream_state=ctx.stream_state,
                log_label="stream_iter (fallback)",
                result_holder=result_holder,
            ):
                yield payload
            ctx.result = result_holder.get("result")
        else:
            raise stream_err

    total_end_time = time.time()
    metrics.total_duration = total_end_time - start_time
    if ctx.stream_state.first_token_time:
        metrics.ttft = ctx.stream_state.first_token_time - start_time
    if ctx.parser and ctx.parser.thought_start_time:
        if ctx.parser.thought_end_time:
            metrics.thought_duration = ctx.parser.thought_end_time - ctx.parser.thought_start_time
        else:
            metrics.thought_duration = time.time() - ctx.parser.thought_start_time
    if metrics.thought_duration is not None:
        yield prepared.emitter.emit({"thought_duration": metrics.thought_duration})
    if metrics.ttft is not None:
        yield prepared.emitter.emit({"ttft": metrics.ttft})
    yield prepared.emitter.emit({"total_duration": metrics.total_duration})


async def _postprocess_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    prepared: PreparedRuntime,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    try:
        finish_reason_val = getattr(getattr(ctx.result, "response", None), "finish_reason", None)
        if not isinstance(finish_reason_val, str):
            finish_reason_val = None
        raw_usage = await _resolve_result_usage(ctx.result)
        usage_stats = deps.calculate_usage(
            provider=ctx.provider,
            raw_usage=raw_usage,
            duration=metrics.total_duration,
            finish_reason=finish_reason_val,
        )
        metrics.prompt_tokens = usage_stats.prompt_tokens
        metrics.completion_tokens = usage_stats.completion_tokens
        metrics.total_tokens = usage_stats.total_tokens
        metrics.finish_reason = usage_stats.finish_reason
        yield prepared.emitter.emit(usage_stats.model_dump())

        continue_payload = deps.append_continue_message_if_needed(
            finish_reason=metrics.finish_reason,
            stream_state=ctx.stream_state,
        )
        if continue_payload:
            yield prepared.emitter.emit(continue_payload)
        elif deps.should_handle_tool_call_mismatch(
            finish_reason=metrics.finish_reason,
            tool_call_started_count=prepared.tool_tracker.counts["started"],
        ):
            async for payload in _handle_tool_call_mismatch_retry(
                ctx=ctx,
                prepared=prepared,
                deps=deps,
            ):
                yield payload
    except Exception as usage_err:
        deps.logger.error("Failed to get usage via adapter: %s", usage_err)

    citations = ctx.deps.get("citations") if isinstance(ctx.deps, dict) else None
    if isinstance(citations, list) and citations:
        yield prepared.emitter.emit({"citations": citations})
    require_citations = bool(getattr(ctx.agent_config, "require_citations", False)) if ctx.agent_config else False
    citation_payload = deps.append_citation_suffix_if_needed(
        citations=citations,
        require_citations=require_citations,
        format_citations_suffix=deps.format_citations_suffix,
        stream_state=ctx.stream_state,
    )
    if citation_payload:
        yield prepared.emitter.emit(citation_payload)
    async for payload in _emit_jira_action_preview_events(
        ctx=ctx,
        prepared=prepared,
        deps=deps,
    ):
        yield payload


def _finalize_stream_run(
    *,
    ctx: StreamRunContext,
    metrics: StreamRunMetrics,
    tool_tracker: Any,
    deps: StreamRunnerDeps,
) -> None:
    saved = deps.persist_assistant_message(
        chat_service=deps.chat_service,
        chat_id=ctx.chat_id,
        stream_state=ctx.stream_state,
        thought_duration=metrics.thought_duration,
        ttft=metrics.ttft,
        total_duration=metrics.total_duration,
        prompt_tokens=metrics.prompt_tokens,
        completion_tokens=metrics.completion_tokens,
        total_tokens=metrics.total_tokens,
        finish_reason=metrics.finish_reason,
        current_exception=metrics.current_exception,
        assistant_turn_id=ctx.assistant_turn_id,
        run_id=ctx.run_id,
        turn_binding_enabled=ctx.turn_binding_enabled,
        supports_reasoning=metrics.supports_reasoning,
        deep_thinking_enabled=bool(ctx.request.deep_thinking_enabled),
        reasoning_enabled=metrics.reasoning_enabled,
        continuation_of=_safe_text(getattr(ctx.request, "continuation_of", None)),
        continuation_root_id=_continuation_root_for_request(ctx.request),
        continuation_status=_continuation_status_for_request(ctx.request, metrics.finish_reason),
        content_type=_continuation_content_type_for_request(ctx.request),
    )
    if saved:
        asyncio.create_task(
            deps.refine_title_once_fn(
                ctx.chat_id,
                provider_override=ctx.provider,
                model_override=ctx.model_name,
            )
        )
    if deps.env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
        deps.logger.info(
            "BACKLOG_CHAT_RESPONSE %s",
            deps.safe_json_log(
                deps.build_chat_response_log_payload(
                    chat_id=ctx.chat_id,
                    provider=ctx.provider,
                    model_name=ctx.model_name,
                    finish_reason=metrics.finish_reason or (
                        metrics.current_exception.__class__.__name__
                        if isinstance(metrics.current_exception, (GeneratorExit, asyncio.CancelledError))
                        else None
                    ),
                    prompt_tokens=metrics.prompt_tokens,
                    completion_tokens=metrics.completion_tokens,
                    total_tokens=metrics.total_tokens,
                    ttft=metrics.ttft,
                    total_duration=metrics.total_duration,
                    tool_call_started_count=tool_tracker.counts["started"],
                    tool_call_finished_count=tool_tracker.counts["finished"],
                    full_response=ctx.stream_state.full_response,
                    error=metrics.stream_error_message,
                )
            ),
        )


def build_chat_event_generator(
    *,
    chat_id: str,
    request: Any,
    history: List[Any],
    validated_images: List[str],
    multimodal_service: Any,
    deps: StreamRunnerDeps,
) -> AsyncIterator[str]:
    async def event_generator() -> AsyncIterator[str]:
        ctx, metrics, emitter, tool_tracker = _create_stream_runtime(
            chat_id=chat_id,
            request=request,
            history=history,
            validated_images=validated_images,
            deps=deps,
        )
        yield emitter.emit({"chat_id": ctx.chat_id})

        try:
            prepared: PreparedRuntime | None = None
            async for step in _prepare_runtime_dependencies(
                ctx=ctx,
                metrics=metrics,
                emitter=emitter,
                tool_tracker=tool_tracker,
                multimodal_service=multimodal_service,
                validated_images=validated_images,
                request=request,
                deps=deps,
            ):
                if isinstance(step, PreparedRuntime):
                    prepared = step
                else:
                    yield step
            if prepared is None:
                return

            async for payload in _execute_stream_run(
                ctx=ctx,
                metrics=metrics,
                prepared=prepared,
                deps=deps,
            ):
                yield payload

            async for payload in _postprocess_stream_run(
                ctx=ctx,
                metrics=metrics,
                prepared=prepared,
                deps=deps,
            ):
                yield payload

        except (Exception, GeneratorExit, asyncio.CancelledError) as e:
            metrics.current_exception = e
            if isinstance(e, (GeneratorExit, asyncio.CancelledError)):
                deps.logger.info("Chat stream cancelled by client")
                metrics.stream_error_message = e.__class__.__name__
            else:
                metrics.stream_error_message = str(e)
                deps.logger.exception("Chat error")
                yield emitter.emit({"error": deps.handle_llm_exception(e)})
        finally:
            _finalize_stream_run(
                ctx=ctx,
                metrics=metrics,
                tool_tracker=tool_tracker,
                deps=deps,
            )

    return event_generator()
