from collections import defaultdict
from typing import Any, Dict, Optional


def title_refinement_reason_distribution(reason_counts: Dict[str, int]) -> Dict[str, Any]:
    counts = {k: int(v) for k, v in reason_counts.items()}
    return {
        "total": int(sum(counts.values())),
        "counts": dict(sorted(counts.items(), key=lambda item: item[0])),
    }


def record_title_refinement_reason(reason: str, reason_counts: defaultdict) -> Dict[str, Any]:
    key = reason.strip().lower() if isinstance(reason, str) and reason.strip() else "unknown"
    reason_counts[key] += 1
    return title_refinement_reason_distribution(reason_counts)


def is_placeholder_title(chat: Any) -> bool:
    title = (chat.title or "").strip()
    if not title or title == "New Chat":
        return True
    first_user_message = next(
        ((m.content or "").strip() for m in chat.messages if m.role == "user" and (m.content or "").strip()),
        None,
    )
    if not first_user_message:
        return False
    expected = first_user_message[:30] + "..." if len(first_user_message) > 30 else first_user_message
    return title == expected


async def refine_title_once(
    *,
    chat_id: str,
    provider_override: Optional[str],
    model_override: Optional[str],
    chat_service: Any,
    session_meta_service: Any,
    config_service: Any,
    logger: Any,
    reason_counts: defaultdict,
) -> None:
    try:
        chat = chat_service.get_chat(chat_id)
        if not chat:
            distribution = record_title_refinement_reason("chat_not_found", reason_counts)
            logger.info("TITLE_REFINEMENT chat_id=%s action=skip reason=chat_not_found distribution=%s", chat_id, distribution)
            return
        original_title = (chat.title or "").strip()
        if not is_placeholder_title(chat):
            distribution = record_title_refinement_reason("non_placeholder", reason_counts)
            logger.info("TITLE_REFINEMENT chat_id=%s action=skip reason=non_placeholder title=%s distribution=%s", chat_id, original_title, distribution)
            return
        assistant_count = sum(1 for m in chat.messages if m.role == "assistant")
        if assistant_count != 1:
            distribution = record_title_refinement_reason("assistant_count_mismatch", reason_counts)
            logger.info("TITLE_REFINEMENT chat_id=%s action=skip reason=assistant_count_mismatch assistant_count=%s distribution=%s", chat_id, assistant_count, distribution)
            return
        llm_config = config_service.get_llm_config()
        if not llm_config.get("meta_use_runtime_model_for_title", False):
            provider_override = None
            model_override = None
        generated_title = await session_meta_service.generate_session_meta(
            chat_id,
            task="title",
            provider_override=provider_override,
            model_override=model_override,
        )
        if not generated_title:
            distribution = record_title_refinement_reason("empty_generated_title", reason_counts)
            logger.info("TITLE_REFINEMENT chat_id=%s action=skip reason=empty_generated_title distribution=%s", chat_id, distribution)
            return
        updated = chat_service.update_chat_title(chat_id, generated_title)
        distribution = record_title_refinement_reason("updated" if updated else "update_noop", reason_counts)
        logger.info(
            "TITLE_REFINEMENT chat_id=%s action=%s old_title=%s new_title=%s distribution=%s",
            chat_id,
            "updated" if updated else "skip",
            original_title,
            generated_title,
            distribution,
        )
    except Exception:
        distribution = record_title_refinement_reason("error", reason_counts)
        logger.info("TITLE_REFINEMENT chat_id=%s action=error distribution=%s", chat_id, distribution)
        logger.exception("TITLE_REFINEMENT chat_id=%s action=error", chat_id)


def normalize_finished_ts(ts: Optional[str]) -> Optional[Any]:
    from datetime import datetime

    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")) if ts else None


def compute_finish_reason(current_exception: Optional[BaseException], finish_reason: Optional[str]) -> Optional[str]:
    if finish_reason:
        return finish_reason
    if isinstance(current_exception, (GeneratorExit, TimeoutError)):
        return current_exception.__class__.__name__
    return finish_reason


def append_continue_message_if_needed(
    *,
    finish_reason: Optional[str],
    stream_state: Any,
) -> Optional[Dict[str, Any]]:
    if finish_reason != "length":
        return None
    continue_msg = "\n\n> ⚠️ **[系统提示]** 由于输出长度限制，内容可能未完全生成。您可以输入 **“继续”** 来获取剩余部分。"
    stream_state.full_response += continue_msg
    return {"content": continue_msg}


def append_citation_suffix_if_needed(
    *,
    citations: Any,
    require_citations: bool,
    format_citations_suffix: Any,
    stream_state: Any,
) -> Optional[Dict[str, Any]]:
    if not require_citations:
        return None
    if isinstance(citations, list) and citations:
        suffix = format_citations_suffix(citations)
        if suffix:
            stream_state.full_response += suffix
            return {"content": suffix}
        return None
    suffix = "\n\n未检索到可引用的文档依据（citations 为空）。建议先使用文档检索/读取工具获取证据后再回答。"
    stream_state.full_response += suffix
    return {"content": suffix}


def persist_assistant_message(
    *,
    chat_service: Any,
    chat_id: str,
    stream_state: Any,
    thought_duration: Optional[float],
    ttft: Optional[float],
    total_duration: Optional[float],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    finish_reason: Optional[str],
    current_exception: Optional[BaseException],
    assistant_turn_id: str,
    run_id: str,
    turn_binding_enabled: bool,
    supports_reasoning: bool,
    deep_thinking_enabled: bool,
    reasoning_enabled: bool,
) -> bool:
    if not stream_state.full_response:
        return False
    resolved_finish_reason = finish_reason or (
        current_exception.__class__.__name__
        if current_exception and isinstance(current_exception, BaseException)
        else None
    )
    chat_service.add_message(
        chat_id,
        "assistant",
        stream_state.full_response,
        thought_duration=thought_duration,
        ttft=ttft,
        total_duration=total_duration,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=resolved_finish_reason,
        assistant_turn_id=assistant_turn_id if turn_binding_enabled else None,
        run_id=run_id if turn_binding_enabled else None,
        supports_reasoning=supports_reasoning,
        deep_thinking_enabled=bool(deep_thinking_enabled),
        reasoning_enabled=reasoning_enabled,
    )
    return True
