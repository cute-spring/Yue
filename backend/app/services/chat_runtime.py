from typing import Any, Callable, Dict, List, Optional, Tuple


def truncate_for_log(text: str, max_chars: int) -> Dict[str, Any]:
    if max_chars <= 0:
        return {"text": "", "truncated": bool(text), "original_chars": len(text or "")}
    text = text or ""
    if len(text) <= max_chars:
        return {"text": text, "truncated": False, "original_chars": len(text)}
    return {"text": text[:max_chars], "truncated": True, "original_chars": len(text)}


def build_chat_request_log_payload(
    chat_id: str,
    request: Any,
    *,
    env_flag_with_fallback: Callable[[str, str, bool], bool],
    safe_int_env_with_fallback: Callable[[str, str, int], int],
) -> Dict[str, Any]:
    include_images_raw = env_flag_with_fallback("LLM_LOG_INCLUDE_IMAGE_DATA", "BACKLOG_LOG_INCLUDE_IMAGE_DATA", False)
    max_chars = safe_int_env_with_fallback("LLM_LOG_MAX_CHARS", "BACKLOG_LOG_MAX_CHARS", 120000)
    request_dump = request.model_dump()
    images = request_dump.get("images") or []
    if isinstance(images, list):
        if include_images_raw:
            request_dump["images_count"] = len(images)
        else:
            request_dump["images"] = [{"index": idx, "chars": len(img) if isinstance(img, str) else 0} for idx, img in enumerate(images)]
    request_dump["message"] = truncate_for_log(request_dump.get("message") or "", max_chars)
    prompt_value = request_dump.get("system_prompt")
    if isinstance(prompt_value, str):
        request_dump["system_prompt"] = truncate_for_log(prompt_value, max_chars)
    request_dump["chat_id"] = chat_id
    return request_dump


def build_chat_response_log_payload(
    *,
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
    safe_int_env_with_fallback: Callable[[str, str, int], int],
) -> Dict[str, Any]:
    max_chars = safe_int_env_with_fallback("LLM_LOG_MAX_CHARS", "BACKLOG_LOG_MAX_CHARS", 120000)
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "provider": provider,
        "model": model_name,
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "ttft": ttft,
        "total_duration": total_duration,
        "tool_call_started_count": tool_call_started_count,
        "tool_call_finished_count": tool_call_finished_count,
        "response": truncate_for_log(full_response or "", max_chars),
    }
    if error:
        payload["error"] = truncate_for_log(error, max_chars)
    return payload


def safe_json_log(payload: Dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception as err:
        fallback = {"log_payload_error": str(err), "payload_repr": repr(payload)}
        return json.dumps(fallback, ensure_ascii=False, default=str)


def persist_validated_images(
    validated_images: List[str],
    *,
    save_base64_image: Callable[[str], str],
    logger: Any,
) -> List[str]:
    stored_images = []
    for img in validated_images:
        try:
            path = img if img.startswith("/files/") else save_base64_image(img)
            stored_images.append(path)
        except Exception as err:
            logger.error("Failed to save image: %s", err)
    return stored_images


def collect_tool_names(tools: List[Any]) -> List[str]:
    tool_names = []
    for tool in tools:
        name = getattr(tool, "name", None) or getattr(tool, "__name__", None) or tool.__class__.__name__
        tool_names.append(name)
    return tool_names


def patch_model_settings(model_settings: Dict[str, Any]) -> Dict[str, Any]:
    if "max_tokens" in model_settings:
        if "extra_body" not in model_settings:
            model_settings["extra_body"] = {}
        model_settings["extra_body"]["max_tokens"] = model_settings["max_tokens"]
    return model_settings


def build_agent_deps(agent_config: Any) -> Dict[str, Any]:
    deps: Dict[str, Any] = {"citations": []}
    if agent_config and agent_config.doc_roots:
        deps["doc_roots"] = agent_config.doc_roots
    if agent_config and getattr(agent_config, "doc_file_patterns", None):
        deps["doc_file_patterns"] = agent_config.doc_file_patterns
    return deps


def build_skill_effectiveness_payload(
    *,
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
    estimate_tokens: Callable[[str], int],
) -> Dict[str, Any]:
    return {
        "event": "skill_effectiveness",
        "reason_code": selection_reason_code,
        "selection_source": selection_source,
        "selection_score": selection_score,
        "fallback_used": selected_skill_spec is None,
        "selected_skill": (
            {"name": selected_skill_spec.name, "version": selected_skill_spec.version}
            if selected_skill_spec else None
        ),
        "selected_skill_source_layer": (
            selected_skill_spec.source_layer if selected_skill_spec else None
        ),
        "override_hit": bool(selected_skill_spec and selected_skill_spec.override_from),
        "visible_skill_count": visible_skill_count,
        "available_skill_count": available_skill_count,
        "always_injected_count": always_injected_count,
        "selected_group_ids": selected_group_ids,
        "resolved_skill_count": resolved_skill_count,
        "summary_injected": summary_injected,
        "scope_summary_injected": scope_summary_injected,
        "effective_scope_count": effective_scope_count,
        "summary_prompt_enabled": True,
        "lazy_full_load_enabled": True,
        "system_prompt_tokens_estimate": estimate_tokens(system_prompt),
        "user_message_tokens_estimate": estimate_tokens(request_message),
    }


async def ensure_ollama_model_available(
    *,
    provider: str,
    model_name: str,
    fetch_ollama_models: Callable[[], Any],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    if provider != "ollama":
        return model_name, None
    models = await fetch_ollama_models()
    if not models:
        return model_name, {"error": "Ollama 未响应或没有可用模型，请确认服务已启动并可访问"}
    if model_name not in models:
        latest_name = f"{model_name}:latest"
        if latest_name in models:
            return latest_name, None
        return model_name, {"error": f"Ollama 未找到模型 {model_name}，请先执行 `ollama pull {model_name}`"}
    return model_name, None


def format_citations_suffix(citations: Any) -> Optional[str]:
    if not (isinstance(citations, list) and citations):
        return None
    seen = set()
    sources = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        path = citation.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        locator = ""
        start_line = citation.get("start_line")
        end_line = citation.get("end_line")
        start_page = citation.get("start_page")
        end_page = citation.get("end_page")
        if isinstance(start_line, int) and isinstance(end_line, int):
            locator = f"#L{start_line}-L{end_line}"
        elif isinstance(start_page, int) and isinstance(end_page, int):
            locator = f"#P{start_page}-P{end_page}"
        entry = f"- {path}{locator}"
        if entry in seen:
            continue
        seen.add(entry)
        sources.append(entry)
    if not sources:
        return None
    return "\n\nSources:\n" + "\n".join(sources)
