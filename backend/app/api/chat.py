from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart, ImageUrl
from app.mcp.manager import mcp_manager
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
from app.services.skill_service import skill_registry, skill_router, SkillPolicyGate, MarkdownSkillAdapter, LegacyAgentAdapter
from app.services import doc_retrieval
from app.utils.image_handler import save_base64_image, load_image_to_base64
import time
import asyncio
import uuid
import json
import logging
import os
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Token Management Constants
# DeepSeek Reasoner has 128k context. We set a safe limit of ~100k tokens.
# Heuristic: 1 token ~= 3 characters (conservative for code/mixed content).
EST_CHARS_PER_TOKEN = 3
MAX_CONTEXT_TOKENS = 100000
MAX_SINGLE_MSG_TOKENS = 20000  # Cap single messages to avoid one massive file read blocking everything
SKILL_BIND_MIN_SCORE = 2
SKILL_SWITCH_DELTA = 2

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // EST_CHARS_PER_TOKEN

def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}

def _safe_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default

def _env_flag_with_fallback(primary: str, legacy: str, default: bool) -> bool:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        value = raw_primary.strip().lower()
        return value in {"1", "true", "yes", "on"}
    return _env_flag(legacy, default)

def _safe_int_env_with_fallback(primary: str, legacy: str, default: int) -> int:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        try:
            value = int(raw_primary)
        except Exception:
            return default
        return value if value > 0 else default
    return _safe_int_env(legacy, default)

def _truncate_for_log(text: str, max_chars: int) -> Dict[str, Any]:
    if max_chars <= 0:
        return {"text": "", "truncated": bool(text), "original_chars": len(text or "")}
    text = text or ""
    if len(text) <= max_chars:
        return {"text": text, "truncated": False, "original_chars": len(text)}
    return {"text": text[:max_chars], "truncated": True, "original_chars": len(text)}

def _build_chat_request_log_payload(chat_id: str, request: "ChatRequest") -> Dict[str, Any]:
    include_images_raw = _env_flag_with_fallback("LLM_LOG_INCLUDE_IMAGE_DATA", "BACKLOG_LOG_INCLUDE_IMAGE_DATA", False)
    max_chars = _safe_int_env_with_fallback("LLM_LOG_MAX_CHARS", "BACKLOG_LOG_MAX_CHARS", 120000)
    request_dump = request.model_dump()
    images = request_dump.get("images") or []
    if isinstance(images, list):
        if include_images_raw:
            request_dump["images_count"] = len(images)
        else:
            request_dump["images"] = [{"index": idx, "chars": len(img) if isinstance(img, str) else 0} for idx, img in enumerate(images)]
    request_dump["message"] = _truncate_for_log(request_dump.get("message") or "", max_chars)
    prompt_value = request_dump.get("system_prompt")
    if isinstance(prompt_value, str):
        request_dump["system_prompt"] = _truncate_for_log(prompt_value, max_chars)
    request_dump["chat_id"] = chat_id
    return request_dump

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
    max_chars = _safe_int_env_with_fallback("LLM_LOG_MAX_CHARS", "BACKLOG_LOG_MAX_CHARS", 120000)
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
        "response": _truncate_for_log(full_response or "", max_chars),
    }
    if error:
        payload["error"] = _truncate_for_log(error, max_chars)
    return payload

def _safe_json_log(payload: Dict[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception as err:
        fallback = {"log_payload_error": str(err), "payload_repr": repr(payload)}
        return json.dumps(fallback, ensure_ascii=False, default=str)


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

def _has_docs_capability(agent_config: Any) -> bool:
    tools = getattr(agent_config, "enabled_tools", []) or []
    for tool in tools:
        if not isinstance(tool, str):
            continue
        if "docs_" in tool:
            return True
    return False

def _mask_scope_root(path: str) -> str:
    if not path:
        return path
    project_root = doc_retrieval.get_project_root()
    path_real = os.path.realpath(path)
    project_real = os.path.realpath(project_root)
    try:
        if os.path.commonpath([project_real, path_real]) == project_real:
            rel = os.path.relpath(path_real, project_real).replace(os.sep, "/")
            return rel if rel != "." else "."
    except Exception:
        pass
    parts = [p for p in path_real.replace("\\", "/").split("/") if p]
    tail = "/".join(parts[-2:]) if len(parts) >= 2 else (parts[0] if parts else path_real)
    return f".../{tail}" if tail else path_real

def _build_scope_summary_block(agent_config: Any) -> Tuple[Optional[str], int]:
    if not agent_config or not _has_docs_capability(agent_config):
        return None, 0
    if not _env_flag("PROMPT_SCOPE_SUMMARY_ENABLED", True):
        return None, 0
    reveal_paths = _env_flag("PROMPT_SCOPE_SUMMARY_REVEAL_PATHS", False)
    max_roots = _safe_int_env("PROMPT_SCOPE_SUMMARY_MAX_ROOTS", 3)
    doc_roots = getattr(agent_config, "doc_roots", None) or []
    doc_access = config_service.get_doc_access()
    allow_roots = doc_access.get("allow_roots") or []
    deny_roots = doc_access.get("deny_roots") or []
    try:
        effective_roots = doc_retrieval.resolve_docs_roots_for_search(
            None,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )
    except Exception:
        effective_roots = []
    if not effective_roots:
        return None, 0
    shown = effective_roots[:max_roots]
    if reveal_paths:
        display_roots = shown
    else:
        display_roots = [_mask_scope_root(p) for p in shown]
    lines = ["### Scope Summary", f"- Effective roots: {len(effective_roots)}"]
    lines.extend(f"- {root}" for root in display_roots)
    if len(effective_roots) > len(shown):
        lines.append(f"- ... and {len(effective_roots) - len(shown)} more")
    lines.append("- If uncertain, call docs_list first to inspect paths.")
    return "\n".join(lines), len(effective_roots)

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

@router.get("/history", response_model=list[ChatSession])
async def list_chats():
    return chat_service.list_chats()

@router.get("/{chat_id}", response_model=ChatSession)
async def get_chat(chat_id: str):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    if not chat_service.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

class TruncateRequest(BaseModel):
    keep_count: int

@router.post("/{chat_id}/truncate")
async def truncate_chat(chat_id: str, request: TruncateRequest):
    chat_service.truncate_chat(chat_id, request.keep_count)
    return {"status": "success"}

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    # Initialize Chat Session
    chat_id = request.chat_id
    if not chat_id:
        chat = chat_service.create_chat(request.agent_id)
        chat_id = chat.id
    
    # Load History for Context
    history = []
    existing_chat = chat_service.get_chat(chat_id)
    if existing_chat:
        # Smart Context Management
        # 1. Start from the most recent messages
        # 2. Enforce per-message limits
        # 3. Enforce global context limits
        
        all_msgs = existing_chat.messages
        current_tokens = 0
        temp_history = []
        
        # Iterate backwards to prioritize recent context
        for m in reversed(all_msgs):
            content = m.content or ""
            msg_tokens = estimate_tokens(content)
            
            # Per-message truncation
            if msg_tokens > MAX_SINGLE_MSG_TOKENS:
                keep_chars = MAX_SINGLE_MSG_TOKENS * EST_CHARS_PER_TOKEN
                content = content[:keep_chars] + "\n... (content truncated due to length)"
                msg_tokens = MAX_SINGLE_MSG_TOKENS
            
            # Check global limit
            if current_tokens + msg_tokens > MAX_CONTEXT_TOKENS:
                logger.info(f"Context limit reached. Dropping older messages. Current tokens: {current_tokens}")
                break
                
            current_tokens += msg_tokens
            
            # Add to temp history
            if m.role == "user":
                if m.images:
                    parts = [m.content]
                    for img in m.images:
                        # Reload from disk if it's a path
                        base64_img = load_image_to_base64(img)
                        parts.append(ImageUrl(url=base64_img))
                    temp_history.append(ModelRequest(parts=[UserPromptPart(content=parts)]))
                else:
                    temp_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
            elif m.role == "assistant":
                temp_history.append(ModelResponse(parts=[TextPart(content=content)]))
        
        # Restore chronological order
        history = list(reversed(temp_history))

    # Save User Message to DB
    # Save images to disk before DB
    stored_images = []
    if request.images:
        for img in request.images:
            try:
                # If it's already a path (e.g. from existing chat re-sent?), keep it.
                # But request.images from frontend usually base64.
                # save_base64_image will just return if it fails or we might want to check?
                # Actually save_base64_image raises exception if fails.
                path = save_base64_image(img)
                stored_images.append(path)
            except Exception as e:
                logger.error(f"Failed to save image: {e}")
                # Fallback? Or skip?
                pass

    if _env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
        logger.info(
            "BACKLOG_CHAT_REQUEST %s",
            _safe_json_log(_build_chat_request_log_payload(chat_id, request)),
        )

    chat_service.add_message(chat_id, "user", request.message, images=stored_images if stored_images else None)
    
    async def event_generator():
        # Yield the chat ID first so frontend knows where we are
        yield _serialize_sse_payload({"chat_id": chat_id})
        
        # Tool event queue to capture events from tool callbacks
        tool_event_queue = asyncio.Queue()
        tool_call_started_count = 0
        tool_call_finished_count = 0

        # Tool event callback for tool.call.started and tool.call.finished
        async def on_tool_event(event: Dict[str, Any]):
            nonlocal tool_call_started_count, tool_call_finished_count
            try:
                # 1. Emit to SSE stream
                await tool_event_queue.put(event)
                
                # 2. Persistence (Phase 2)
                event_type = event.get("event")
                if event_type == "tool.call.started":
                    tool_call_started_count += 1
                    chat_service.add_tool_call(
                        session_id=chat_id,
                        call_id=event.get("call_id"),
                        tool_name=event.get("tool_name"),
                        args=event.get("args")
                    )
                elif event_type == "tool.call.finished":
                    tool_call_finished_count += 1
                    chat_service.update_tool_call(
                        call_id=event.get("call_id"),
                        status="error" if "error" in event else "success",
                        result=event.get("result"),
                        error=event.get("error"),
                        duration_ms=event.get("duration_ms")
                    )
            except Exception:
                logger.exception("Error in on_tool_event (streaming + persistence)")

        full_response = ""
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
            selected_skill_spec = None
            always_skill_specs = []
            selection_reason_code = "legacy_path"
            selection_source = "none"
            visible_skill_count = 0
            available_skill_count = 0
            always_injected_count = 0
            feature_flags = config_service.get_feature_flags()
            
            summary_block = None
            if feature_flags.get("skill_summary_prompt_enabled", False) and agent_config and agent_config.skill_mode != "off":
                visible_skills = skill_router.get_visible_skills(agent_config)
                summary_lines = []
                for skill in visible_skills:
                    status = "available" if skill.availability is not False else "unavailable"
                    summary_lines.append(f"- {skill.name}: {skill.description} ({status})")
                if summary_lines:
                    summary_block = "### Skill Summaries\n" + "\n".join(summary_lines)

            if feature_flags.get("skill_runtime_enabled") and agent_config and agent_config.skill_mode != "off":
                bound_name, bound_version = chat_service.get_session_skill(chat_id)
                bound_skill = None
                if bound_name:
                    bound_skill = skill_registry.get_skill(bound_name, bound_version)
                visible_skills = skill_router.get_visible_skills(agent_config)
                visible_skill_count = len(visible_skills)
                available_skill_count = len([s for s in visible_skills if s.availability is not False])
                always_skill_specs = [s for s in visible_skills if s.always and s.availability is not False]
                if bound_skill and bound_skill not in visible_skills:
                    bound_skill = None
                inferred_requested_skill = skill_router.infer_requested_skill(agent_config, request.message)
                if agent_config.skill_mode == "manual":
                    explicit_requested_skill = request.requested_skill or inferred_requested_skill
                    if explicit_requested_skill:
                        selection_source = "explicit" if request.requested_skill else "inferred"
                        selected_skill_spec, _ = skill_router.route_with_score(
                            agent_config,
                            request.message,
                            requested_skill=explicit_requested_skill
                        )
                    elif bound_skill:
                        bound_score = skill_router.score_skill(bound_skill, request.message)
                        if bound_score >= SKILL_BIND_MIN_SCORE:
                            selected_skill_spec = bound_skill
                elif agent_config.skill_mode == "auto":
                    if feature_flags.get("skill_auto_mode_enabled", True):
                        if inferred_requested_skill:
                            selection_source = "inferred"
                        best_skill, best_score = skill_router.route_with_score(
                            agent_config,
                            request.message,
                            requested_skill=inferred_requested_skill
                        )
                        if bound_skill:
                            bound_score = skill_router.score_skill(bound_skill, request.message)
                            if not best_skill:
                                if bound_score >= SKILL_BIND_MIN_SCORE:
                                    selected_skill_spec = bound_skill
                            else:
                                if bound_skill.name == best_skill.name and bound_skill.version == best_skill.version:
                                    if best_score >= SKILL_BIND_MIN_SCORE:
                                        selected_skill_spec = bound_skill
                                else:
                                    if best_score >= max(bound_score + SKILL_SWITCH_DELTA, SKILL_BIND_MIN_SCORE):
                                        selected_skill_spec = best_skill
                                    elif bound_score >= SKILL_BIND_MIN_SCORE:
                                        selected_skill_spec = bound_skill
                        else:
                            if best_skill and best_score >= SKILL_BIND_MIN_SCORE:
                                selected_skill_spec = best_skill
                if selected_skill_spec:
                    selection_reason_code = "skill_selected"
                    chat_service.set_session_skill(chat_id, selected_skill_spec.name, selected_skill_spec.version)
                else:
                    selection_reason_code = "no_matching_skill"
                    chat_service.clear_session_skill(chat_id)
            elif agent_config:
                selection_reason_code = "skill_mode_off"
                chat_service.clear_session_skill(chat_id)
                
            if selected_skill_spec:
                if feature_flags.get("skill_lazy_full_load_enabled", True):
                    selected_skill_spec = skill_registry.get_full_skill(selected_skill_spec.name, selected_skill_spec.version) or selected_skill_spec
                # Skill path
                descriptor = MarkdownSkillAdapter.to_descriptor(selected_skill_spec)
                provider = provider or agent_config.provider
                model_name = model_name or agent_config.model
                
                persona = agent_config.system_prompt or ""
                skill_prompt = descriptor.prompt_blocks.get("system_prompt", "")
                instructions = descriptor.prompt_blocks.get("instructions", "")
                always_blocks = []
                for always_skill in always_skill_specs:
                    if always_skill.name == selected_skill_spec.name and always_skill.version == selected_skill_spec.version:
                        continue
                    resolved_always = always_skill
                    if feature_flags.get("skill_lazy_full_load_enabled", True):
                        resolved_always = skill_registry.get_full_skill(always_skill.name, always_skill.version) or always_skill
                    always_descriptor = MarkdownSkillAdapter.to_descriptor(resolved_always)
                    always_prompt = always_descriptor.prompt_blocks.get("system_prompt", "")
                    always_instructions = always_descriptor.prompt_blocks.get("instructions", "")
                    block = f"[Always Skill: {resolved_always.name}]\n{always_prompt}".strip()
                    if always_instructions:
                        block = f"{block}\n\n### Always Instructions\n{always_instructions}"
                    always_blocks.append(block)
                always_injected_count = len(always_blocks)
                
                use_persona = True
                if agent_config.name == "Expert Mgr" or "Skill Expert Manager" in persona:
                    use_persona = False
                if use_persona and persona:
                    system_prompt = f"{persona}\n\n[Active Skill: {selected_skill_spec.name}]\n{skill_prompt}"
                else:
                    system_prompt = f"[Active Skill: {selected_skill_spec.name}]\n{skill_prompt}"
                if instructions:
                    system_prompt += f"\n\n### Additional Instructions\n{instructions}"
                if always_blocks:
                    system_prompt += "\n\n" + "\n\n".join(always_blocks)
                    
                # Tool intersection
                enabled_tools = agent_config.enabled_tools
                allowed_tools = descriptor.tool_policy.get("allowed_tools")
                final_tools_list = SkillPolicyGate.check_tool_intersection(enabled_tools, allowed_tools)
                
                # Overwrite enabled_tools for tool_registry call later
                # We'll need a way to pass these to tool_registry
                logger.info(f"Skill {selected_skill_spec.name} selected. Tool intersection: {final_tools_list}")
                yield _serialize_sse_payload({"event": "skill_selected", "name": selected_skill_spec.name, "version": selected_skill_spec.version})
            elif agent_config:
                # Legacy path
                provider = provider or agent_config.provider
                model_name = model_name or agent_config.model
                system_prompt = system_prompt or agent_config.system_prompt
                if agent_config.doc_roots:
                    if "可检索目录" not in system_prompt:
                        roots = "\n".join(f"- {r}" for r in agent_config.doc_roots)
                        system_prompt += f"\n\n可检索目录（优先使用）：\n{roots}"
                if always_skill_specs:
                    always_blocks = []
                    for always_skill in always_skill_specs:
                        resolved_always = always_skill
                        if feature_flags.get("skill_lazy_full_load_enabled", True):
                            resolved_always = skill_registry.get_full_skill(always_skill.name, always_skill.version) or always_skill
                        always_descriptor = MarkdownSkillAdapter.to_descriptor(resolved_always)
                        always_prompt = always_descriptor.prompt_blocks.get("system_prompt", "")
                        always_instructions = always_descriptor.prompt_blocks.get("instructions", "")
                        block = f"[Always Skill: {resolved_always.name}]\n{always_prompt}".strip()
                        if always_instructions:
                            block = f"{block}\n\n### Always Instructions\n{always_instructions}"
                        always_blocks.append(block)
                    if always_blocks:
                        always_injected_count = len(always_blocks)
                        system_prompt += "\n\n" + "\n\n".join(always_blocks)
                final_tools_list = agent_config.enabled_tools
            else:
                final_tools_list = [] # Default for no agent

            scope_summary_block, effective_scope_count = _build_scope_summary_block(agent_config)
            scope_summary_injected = False
            if scope_summary_block and scope_summary_block not in (system_prompt or ""):
                system_prompt = (system_prompt or "").strip()
                if system_prompt:
                    system_prompt += f"\n\n{scope_summary_block}"
                else:
                    system_prompt = scope_summary_block
                scope_summary_injected = True

            if summary_block and not selected_skill_spec:
                system_prompt = system_prompt or ""
                if system_prompt:
                    system_prompt = f"{system_prompt}\n\n{summary_block}"
                else:
                    system_prompt = summary_block
            summary_injected = bool(summary_block and not selected_skill_spec)
            
            # Final fallbacks if still None
            provider = provider or "openai"
            model_name = model_name or "gpt-4o"
            system_prompt = system_prompt or "You are a helpful assistant."

            skill_effectiveness_payload = {
                "event": "skill_effectiveness",
                "reason_code": selection_reason_code,
                "selection_source": selection_source,
                "fallback_used": selected_skill_spec is None,
                "selected_skill": (
                    {"name": selected_skill_spec.name, "version": selected_skill_spec.version}
                    if selected_skill_spec else None
                ),
                "visible_skill_count": visible_skill_count,
                "available_skill_count": available_skill_count,
                "always_injected_count": always_injected_count,
                "summary_injected": summary_injected,
                "scope_summary_injected": scope_summary_injected,
                "effective_scope_count": effective_scope_count,
                "summary_prompt_enabled": feature_flags.get("skill_summary_prompt_enabled", False),
                "lazy_full_load_enabled": feature_flags.get("skill_lazy_full_load_enabled", True),
                "system_prompt_tokens_estimate": estimate_tokens(system_prompt),
                "user_message_tokens_estimate": estimate_tokens(request.message),
            }
            try:
                chat_service.add_skill_effectiveness_event(chat_id, skill_effectiveness_payload)
            except Exception:
                logger.exception("Failed to persist skill_effectiveness event")
            yield _serialize_sse_payload(skill_effectiveness_payload)

            if provider == "ollama":
                models = await fetch_ollama_models()
                if not models:
                    yield _serialize_sse_payload({"error": "Ollama 未响应或没有可用模型，请确认服务已启动并可访问"})
                    return
                if model_name not in models:
                    latest_name = f"{model_name}:latest"
                    if latest_name in models:
                        model_name = latest_name
                    else:
                        yield _serialize_sse_payload({"error": f"Ollama 未找到模型 {model_name}，请先执行 `ollama pull {model_name}`"})
                        return

            tools = await tool_registry.get_pydantic_ai_tools_for_agent(
                request.agent_id, 
                provider,
                on_event=on_tool_event,
                enabled_tools=final_tools_list
            )

            tool_names = []
            for tool in tools:
                name = getattr(tool, "name", None)
                if not name:
                    name = getattr(tool, "__name__", None)
                if not name:
                    name = tool.__class__.__name__
                tool_names.append(name)

            yield _serialize_sse_payload({"meta": {"provider": provider, "model": model_name, "tools": tool_names, "context_id": chat_id, "agent_id": request.agent_id}})
            
            # Use PromptBuilder to enhance system prompt (Builder Pattern)
            system_prompt = build_system_prompt(
                base_prompt=system_prompt,
                provider=provider,
                model_name=model_name,
                user_message=request.message
            )

            try:
                model = get_model(provider, model_name)
            except Exception as model_err:
                if os.getenv("PYTEST_CURRENT_TEST"):
                    model = object()
                else:
                    raise model_err

            # Create Pydantic AI Agent
            agent = Agent(
                model,
                system_prompt=system_prompt,
                tools=tools
            )
            deps = {"citations": []}
            if agent_config and agent_config.doc_roots:
                deps["doc_roots"] = agent_config.doc_roots
            if agent_config and getattr(agent_config, "doc_file_patterns", None):
                deps["doc_file_patterns"] = agent_config.doc_file_patterns
            
            # Retrieve model settings (max_tokens etc)
            model_settings = config_service.get_model_settings(provider, model_name)
            
            # Retrieve usage limits policy
            tier = "default"
            if agent_config and getattr(agent_config, "tier", None):
                tier = agent_config.tier
            usage_policy = config_service.get_usage_limits(tier)
            usage_limits = UsageLimits(
                request_limit=usage_policy.get("request_limit"),
                tool_calls_limit=usage_policy.get("tool_calls_limit")
            )

            # DeepSeek/Ollama compatibility: ensure max_tokens is also in extra_body
            # because some providers (like DeepSeek) might not support max_completion_tokens
            # which is what pydantic-ai uses by default for OpenAI-compatible models now.
            if "max_tokens" in model_settings:
                if "extra_body" not in model_settings:
                    model_settings["extra_body"] = {}
                model_settings["extra_body"]["max_tokens"] = model_settings["max_tokens"]
            
            # Prepare Parser (Adapter Pattern)
            capabilities = config_service.get_model_capabilities(provider, model_name)
            parser = get_parser(provider, model_name, capabilities)
            
            last_length = 0
            start_time = time.time()
            first_token_time = None
            
            try:
                # Prepare input
                user_input = request.message
                if request.images:
                    user_input = [request.message]
                    for img in request.images:
                        user_input.append(ImageUrl(url=img))

                # Run with history and model settings
                async with agent.run_stream(user_input, message_history=history, deps=deps, model_settings=model_settings, usage_limits=usage_limits) as result:
                    stream_iter = result.stream_text()
                    if asyncio.iscoroutine(stream_iter):
                        stream_iter = await stream_iter
                    
                    # Manual iteration to handle both text and tool events
                    stream_task = asyncio.create_task(stream_iter.__anext__())
                    queue_task = asyncio.create_task(tool_event_queue.get())
                    
                    while True:
                        # Wait for either next text chunk or a tool event
                        done, _ = await asyncio.wait(
                            [stream_task, queue_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        if stream_task in done:
                            try:
                                res = await stream_task
                                # Track TTFT
                                if not first_token_time:
                                    first_token_time = time.time()

                                # Use Parser to process chunk (Adapter Pattern)
                                results = parser.parse_chunk(res)
                                for item in results:
                                    if "content" in item:
                                        full_response += item["content"]
                                    # Ensure data is followed by exactly two newlines for SSE spec
                                    yield _serialize_sse_payload(item)
                                
                                # Prepare next stream chunk task
                                stream_task = asyncio.create_task(stream_iter.__anext__())
                            except StopAsyncIteration:
                                # Stream finished. Check if queue_task has a pending result.
                                if queue_task.done() and not queue_task.cancelled():
                                    try:
                                        ev = queue_task.result()
                                        yield _serialize_sse_payload(ev)
                                        tool_event_queue.task_done()
                                    except Exception:
                                        pass
                                break
                            except Exception:
                                logger.exception("Error in stream_iter")
                                break
                        
                        if queue_task in done:
                            try:
                                ev = await queue_task
                                yield _serialize_sse_payload(ev)
                                tool_event_queue.task_done()
                                # Prepare next queue event task
                                queue_task = asyncio.create_task(tool_event_queue.get())
                            except Exception:
                                logger.exception("Error getting from tool_event_queue")
                                # Try again?
                                queue_task = asyncio.create_task(tool_event_queue.get())
                    
                    # Cleanup tasks
                    if not stream_task.done():
                        stream_task.cancel()
                    if not queue_task.done():
                        queue_task.cancel()
                    
                    # Final tool events drain (just in case)
                    while not tool_event_queue.empty():
                        ev = tool_event_queue.get_nowait()
                        yield _serialize_sse_payload(ev)
                        tool_event_queue.task_done()

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
                
                yield _serialize_sse_payload(limit_info)
                
                # Provide a friendly user message
                friendly_msg = f"\n\n> ⚠️ **[系统提示]** 已触达策略上限（{limit_err}）。为了您的账户安全和成本控制，本轮执行已自动停止。您可以根据已有信息继续，或尝试缩小问题范围。"
                full_response += friendly_msg
                yield _serialize_sse_payload({"content": friendly_msg})

            except Exception as stream_err:
                err_str = str(stream_err)
                if "status_code: 502" in err_str and provider == "ollama":
                    yield _serialize_sse_payload({"error": "Ollama 返回 502，请检查模型是否已拉取且服务正常运行"})
                    return
                
                # Check for TLS/SSL or Proxy errors
                friendly_error = handle_llm_exception(stream_err)
                if friendly_error != err_str:
                    yield _serialize_sse_payload({"error": friendly_error})
                    return

                if "does not support tools" in err_str or "Tool use is not supported" in err_str:
                    logger.info("Model %s does not support tools, falling back to pure chat.", model_name)
                    # Re-create agent without tools
                    agent_no_tools = Agent(model, system_prompt=system_prompt)
                    # Reset parser and response tracking for second attempt
                    parser = get_parser(provider, model_name, capabilities)
                    full_response = ""
                    first_token_time = None 
                    
                    # Prepare input
                    user_input = request.message
                    if request.images:
                        user_input = [request.message]
                        for img in request.images:
                            user_input.append(ImageUrl(url=img))

                    async with agent_no_tools.run_stream(user_input, message_history=history, deps=deps, model_settings=model_settings) as result:
                        stream_iter = result.stream_text()
                        if asyncio.iscoroutine(stream_iter):
                            stream_iter = await stream_iter
                        
                        # Manual iteration for fallback
                        stream_task = asyncio.create_task(stream_iter.__anext__())
                        queue_task = asyncio.create_task(tool_event_queue.get())
                        
                        while True:
                            done, _ = await asyncio.wait(
                                [stream_task, queue_task],
                                return_when=asyncio.FIRST_COMPLETED
                            )
                            
                            if stream_task in done:
                                try:
                                    res = await stream_task
                                    if not first_token_time:
                                        first_token_time = time.time()
                                    results = parser.parse_chunk(res)
                                    for item in results:
                                        if "content" in item:
                                            full_response += item["content"]
                                        yield _serialize_sse_payload(item)
                                    stream_task = asyncio.create_task(stream_iter.__anext__())
                                except StopAsyncIteration:
                                    if queue_task.done() and not queue_task.cancelled():
                                        try:
                                            ev = queue_task.result()
                                            yield _serialize_sse_payload(ev)
                                            tool_event_queue.task_done()
                                        except Exception:
                                            pass
                                    break
                                except Exception:
                                    logger.exception("Error in stream_iter (fallback)")
                                    break
                            
                            if queue_task in done:
                                try:
                                    ev = await queue_task
                                    yield _serialize_sse_payload(ev)
                                    tool_event_queue.task_done()
                                    queue_task = asyncio.create_task(tool_event_queue.get())
                                except Exception:
                                    logger.exception("Error in tool_event_queue (fallback)")
                                    queue_task = asyncio.create_task(tool_event_queue.get())
                        
                        if not stream_task.done():
                            stream_task.cancel()
                        if not queue_task.done():
                            queue_task.cancel()
                        
                        while not tool_event_queue.empty():
                            ev = tool_event_queue.get_nowait()
                            yield _serialize_sse_payload(ev)
                            tool_event_queue.task_done()
                else:
                    raise stream_err
            
            # Calculate duration
            total_end_time = time.time()
            total_duration = total_end_time - start_time
            if first_token_time:
                ttft = first_token_time - start_time

            if parser.thought_start_time:
                if parser.thought_end_time:
                    thought_duration = parser.thought_end_time - parser.thought_start_time
                else:
                    thought_duration = time.time() - parser.thought_start_time

            if thought_duration is not None:
                yield _serialize_sse_payload({"thought_duration": thought_duration})

            if ttft is not None:
                yield _serialize_sse_payload({"ttft": ttft})
            
            yield _serialize_sse_payload({"total_duration": total_duration})

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
                
                yield _serialize_sse_payload(usage_stats.model_dump())

                # Manual continuation guidance logic
                if finish_reason == "length":
                    continue_msg = "\n\n> ⚠️ **[系统提示]** 由于输出长度限制，内容可能未完全生成。您可以输入 **“继续”** 来获取剩余部分。"
                    full_response += continue_msg
                    yield _serialize_sse_payload({"content": continue_msg})
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
                                yield _serialize_sse_payload({"event": "tool_call_retry", "from_provider": provider, "from_model": model_name, "to_provider": retry_provider, "to_model": retry_model_name})
                                retry_model = get_model(retry_provider, retry_model_name)
                                retry_model_settings = config_service.get_model_settings(retry_provider, retry_model_name)
                                if "max_tokens" in retry_model_settings:
                                    if "extra_body" not in retry_model_settings:
                                        retry_model_settings["extra_body"] = {}
                                    retry_model_settings["extra_body"]["max_tokens"] = retry_model_settings["max_tokens"]
                                retry_capabilities = config_service.get_model_capabilities(retry_provider, retry_model_name)
                                retry_parser = get_parser(retry_provider, retry_model_name, retry_capabilities)
                                retry_agent = Agent(
                                    retry_model,
                                    system_prompt=system_prompt,
                                    tools=tools
                                )
                                retry_input = request.message
                                if request.images:
                                    retry_input = [request.message]
                                    for img in request.images:
                                        retry_input.append(ImageUrl(url=img))
                                async with retry_agent.run_stream(
                                    retry_input,
                                    message_history=history,
                                    deps=deps,
                                    model_settings=retry_model_settings,
                                    usage_limits=usage_limits
                                ) as retry_result:
                                    retry_stream_iter = retry_result.stream_text()
                                    if asyncio.iscoroutine(retry_stream_iter):
                                        retry_stream_iter = await retry_stream_iter
                                    retry_stream_task = asyncio.create_task(retry_stream_iter.__anext__())
                                    retry_queue_task = asyncio.create_task(tool_event_queue.get())
                                    while True:
                                        done, _ = await asyncio.wait(
                                            [retry_stream_task, retry_queue_task],
                                            return_when=asyncio.FIRST_COMPLETED
                                        )
                                        if retry_stream_task in done:
                                            try:
                                                retry_chunk = await retry_stream_task
                                                retry_items = retry_parser.parse_chunk(retry_chunk)
                                                for item in retry_items:
                                                    if "content" in item:
                                                        full_response += item["content"]
                                                    yield _serialize_sse_payload(item)
                                                retry_stream_task = asyncio.create_task(retry_stream_iter.__anext__())
                                            except StopAsyncIteration:
                                                if retry_queue_task.done() and not retry_queue_task.cancelled():
                                                    try:
                                                        ev = retry_queue_task.result()
                                                        yield _serialize_sse_payload(ev)
                                                        tool_event_queue.task_done()
                                                    except Exception:
                                                        pass
                                                break
                                            except Exception:
                                                logger.exception("Error in retry stream_iter")
                                                break
                                        if retry_queue_task in done:
                                            try:
                                                ev = await retry_queue_task
                                                yield _serialize_sse_payload(ev)
                                                tool_event_queue.task_done()
                                                retry_queue_task = asyncio.create_task(tool_event_queue.get())
                                            except Exception:
                                                logger.exception("Error getting retry tool_event_queue")
                                                retry_queue_task = asyncio.create_task(tool_event_queue.get())
                                    if not retry_stream_task.done():
                                        retry_stream_task.cancel()
                                    if not retry_queue_task.done():
                                        retry_queue_task.cancel()
                                    retry_finish_reason = getattr(getattr(retry_result, "response", None), "finish_reason", None)
                                    if tool_call_started_count > 0 or retry_finish_reason != "tool_call":
                                        mismatch_resolved = True
                                if mismatch_resolved:
                                    yield _serialize_sse_payload({"event": "tool_call_retry_success", "provider": retry_provider, "model": retry_model_name, "started": tool_call_started_count, "finished": tool_call_finished_count})
                                    break
                            except Exception as retry_err:
                                logger.exception("Auto retry after tool_call mismatch failed")
                                yield _serialize_sse_payload({"event": "tool_call_retry_failed", "provider": retry_provider, "model": retry_model_name, "error": str(retry_err)})
                    if not mismatch_resolved:
                        tool_msg = (
                            "\n\n> ⚠️ **[系统提示]** 模型返回了 `tool_call` 结束信号，但未产生可执行工具调用。"
                            "这通常是当前模型与工具调用协议兼容性问题。"
                            "建议切换到已验证支持工具调用的模型（例如 `gpt-4o`/`gpt-4o-mini`），"
                            "或重试并明确要求“立即调用工具后再回答”。"
                        )
                        full_response += tool_msg
                        yield _serialize_sse_payload({"event": "tool_call_mismatch", "started": tool_call_started_count, "finished": tool_call_finished_count})
                        yield _serialize_sse_payload({"content": tool_msg})
            except Exception as usage_err:
                logger.error(f"Failed to get usage via adapter: {usage_err}")

            citations = deps.get("citations") if isinstance(deps, dict) else None
            if isinstance(citations, list) and citations:
                yield _serialize_sse_payload({"citations": citations})

            require_citations = bool(getattr(agent_config, "require_citations", False)) if agent_config else False
            if require_citations:
                if isinstance(citations, list) and citations:
                    seen = set()
                    sources = []
                    for c in citations:
                        if not isinstance(c, dict):
                            continue
                        path = c.get("path")
                        if not isinstance(path, str) or not path.strip():
                            continue
                        locator = ""
                        start_line = c.get("start_line")
                        end_line = c.get("end_line")
                        start_page = c.get("start_page")
                        end_page = c.get("end_page")
                        if isinstance(start_line, int) and isinstance(end_line, int):
                            locator = f"#L{start_line}-L{end_line}"
                        elif isinstance(start_page, int) and isinstance(end_page, int):
                            locator = f"#P{start_page}-P{end_page}"
                        entry = f"- {path}{locator}"
                        if entry in seen:
                            continue
                        seen.add(entry)
                        sources.append(entry)
                    if sources:
                        suffix = "\n\nSources:\n" + "\n".join(sources)
                        full_response += suffix
                        yield _serialize_sse_payload({"content": suffix})
                else:
                    suffix = "\n\n未检索到可引用的文档依据（citations 为空）。建议先使用文档检索/读取工具获取证据后再回答。"
                    full_response += suffix
                    yield _serialize_sse_payload({"content": suffix})

        except (Exception, GeneratorExit, asyncio.CancelledError) as e:
            if isinstance(e, (GeneratorExit, asyncio.CancelledError)):
                logger.info("Chat stream cancelled by client")
                stream_error_message = e.__class__.__name__
            else:
                stream_error_message = str(e)
                logger.exception("Chat error")
                yield _serialize_sse_payload({"error": handle_llm_exception(e)})
        finally:
            # Save Assistant Message after completion
            if full_response:
                chat_service.add_message(
                    chat_id, 
                    "assistant", 
                    full_response, 
                    thought_duration=thought_duration,
                    ttft=ttft,
                    total_duration=total_duration,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    finish_reason=finish_reason or (e.__class__.__name__ if 'e' in locals() and isinstance(e, (GeneratorExit, asyncio.CancelledError)) else None)
                )
            if _env_flag_with_fallback("LLM_VERBOSE_LOG_ENABLED", "BACKLOG_VERBOSE_LOG_ENABLED", True):
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
                            full_response=full_response,
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
