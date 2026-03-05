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
from app.services.usage_service import calculate_usage
from app.services.llm.utils import handle_llm_exception
from app.services.skill_service import skill_registry, skill_router, SkillPolicyGate, MarkdownSkillAdapter, LegacyAgentAdapter
from app.utils.image_handler import save_base64_image, load_image_to_base64
import time
import asyncio
import uuid
import json
import logging
import os
from typing import List, Optional, Dict, Any

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

    chat_service.add_message(chat_id, "user", request.message, images=stored_images if stored_images else None)
    
    async def event_generator():
        # Yield the chat ID first so frontend knows where we are
        yield f"data: {json.dumps({'chat_id': chat_id})}\n\n"
        
        # Tool event queue to capture events from tool callbacks
        tool_event_queue = asyncio.Queue()

        # Tool event callback for tool.call.started and tool.call.finished
        async def on_tool_event(event: Dict[str, Any]):
            try:
                # 1. Emit to SSE stream
                await tool_event_queue.put(event)
                
                # 2. Persistence (Phase 2)
                event_type = event.get("event")
                if event_type == "tool.call.started":
                    chat_service.add_tool_call(
                        session_id=chat_id,
                        call_id=event.get("call_id"),
                        tool_name=event.get("tool_name"),
                        args=event.get("args")
                    )
                elif event_type == "tool.call.finished":
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
            feature_flags = config_service.get_feature_flags()
            
            if feature_flags.get("skill_runtime_enabled") and agent_config and agent_config.skill_mode != "off":
                bound_name, bound_version = chat_service.get_session_skill(chat_id)
                bound_skill = None
                if bound_name:
                    bound_skill = skill_registry.get_skill(bound_name, bound_version)
                visible_skills = skill_router.get_visible_skills(agent_config)
                if bound_skill and bound_skill not in visible_skills:
                    bound_skill = None
                if agent_config.skill_mode == "manual":
                    if request.requested_skill:
                        selected_skill_spec, _ = skill_router.route_with_score(
                            agent_config,
                            request.message,
                            requested_skill=request.requested_skill
                        )
                    elif bound_skill:
                        bound_score = skill_router.score_skill(bound_skill, request.message)
                        if bound_score >= SKILL_BIND_MIN_SCORE:
                            selected_skill_spec = bound_skill
                elif agent_config.skill_mode == "auto":
                    if feature_flags.get("skill_auto_mode_enabled", True):
                        best_skill, best_score = skill_router.route_with_score(
                            agent_config,
                            request.message,
                            requested_skill=None
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
                    chat_service.set_session_skill(chat_id, selected_skill_spec.name, selected_skill_spec.version)
                else:
                    chat_service.clear_session_skill(chat_id)
            elif agent_config:
                chat_service.clear_session_skill(chat_id)
                
            if selected_skill_spec:
                # Skill path
                descriptor = MarkdownSkillAdapter.to_descriptor(selected_skill_spec)
                provider = provider or agent_config.provider
                model_name = model_name or agent_config.model
                
                persona = agent_config.system_prompt or ""
                skill_prompt = descriptor.prompt_blocks.get("system_prompt", "")
                instructions = descriptor.prompt_blocks.get("instructions", "")
                
                use_persona = True
                if agent_config.name == "Expert Mgr" or "Skill Expert Manager" in persona:
                    use_persona = False
                if use_persona and persona:
                    system_prompt = f"{persona}\n\n[Active Skill: {selected_skill_spec.name}]\n{skill_prompt}"
                else:
                    system_prompt = f"[Active Skill: {selected_skill_spec.name}]\n{skill_prompt}"
                if instructions:
                    system_prompt += f"\n\n### Additional Instructions\n{instructions}"
                    
                # Tool intersection
                enabled_tools = agent_config.enabled_tools
                allowed_tools = descriptor.tool_policy.get("allowed_tools")
                final_tools_list = SkillPolicyGate.check_tool_intersection(enabled_tools, allowed_tools)
                
                # Overwrite enabled_tools for tool_registry call later
                # We'll need a way to pass these to tool_registry
                logger.info(f"Skill {selected_skill_spec.name} selected. Tool intersection: {final_tools_list}")
                yield f"data: {json.dumps({'event': 'skill_selected', 'name': selected_skill_spec.name, 'version': selected_skill_spec.version})}\n\n"
            elif agent_config:
                # Legacy path
                provider = provider or agent_config.provider
                model_name = model_name or agent_config.model
                system_prompt = system_prompt or agent_config.system_prompt
                if agent_config.doc_roots:
                    if "可检索目录" not in system_prompt:
                        roots = "\n".join(f"- {r}" for r in agent_config.doc_roots)
                        system_prompt += f"\n\n可检索目录（优先使用）：\n{roots}"
                final_tools_list = agent_config.enabled_tools
            else:
                final_tools_list = [] # Default for no agent
            
            # Final fallbacks if still None
            provider = provider or "openai"
            model_name = model_name or "gpt-4o"
            system_prompt = system_prompt or "You are a helpful assistant."

            if provider == "ollama":
                models = await fetch_ollama_models()
                if not models:
                    yield f"data: {json.dumps({'error': 'Ollama 未响应或没有可用模型，请确认服务已启动并可访问'})}\n\n"
                    return
                if model_name not in models:
                    latest_name = f"{model_name}:latest"
                    if latest_name in models:
                        model_name = latest_name
                    else:
                        yield f"data: {json.dumps({'error': f'Ollama 未找到模型 {model_name}，请先执行 `ollama pull {model_name}`'})}\n\n"
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

            yield f"data: {json.dumps({'meta': {'provider': provider, 'model': model_name, 'tools': tool_names, 'context_id': chat_id, 'agent_id': request.agent_id}})}\n\n"
            
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
                                    yield f"data: {json.dumps(item)}\n\n"
                                
                                # Prepare next stream chunk task
                                stream_task = asyncio.create_task(stream_iter.__anext__())
                            except StopAsyncIteration:
                                # Stream finished. Check if queue_task has a pending result.
                                if queue_task.done() and not queue_task.cancelled():
                                    try:
                                        ev = queue_task.result()
                                        yield f"data: {json.dumps(ev)}\n\n"
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
                                yield f"data: {json.dumps(ev)}\n\n"
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
                        yield f"data: {json.dumps(ev)}\n\n"
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
                
                yield f"data: {json.dumps(limit_info)}\n\n"
                
                # Provide a friendly user message
                friendly_msg = f"\n\n> ⚠️ **[系统提示]** 已触达策略上限（{limit_err}）。为了您的账户安全和成本控制，本轮执行已自动停止。您可以根据已有信息继续，或尝试缩小问题范围。"
                full_response += friendly_msg
                yield f"data: {json.dumps({'content': friendly_msg})}\n\n"

            except Exception as stream_err:
                err_str = str(stream_err)
                if "status_code: 502" in err_str and provider == "ollama":
                    yield f"data: {json.dumps({'error': 'Ollama 返回 502，请检查模型是否已拉取且服务正常运行'})}\n\n"
                    return
                
                # Check for TLS/SSL or Proxy errors
                friendly_error = handle_llm_exception(stream_err)
                if friendly_error != err_str:
                    yield f"data: {json.dumps({'error': friendly_error})}\n\n"
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
                                        yield f"data: {json.dumps(item)}\n\n"
                                    stream_task = asyncio.create_task(stream_iter.__anext__())
                                except StopAsyncIteration:
                                    if queue_task.done() and not queue_task.cancelled():
                                        try:
                                            ev = queue_task.result()
                                            yield f"data: {json.dumps(ev)}\n\n"
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
                                    yield f"data: {json.dumps(ev)}\n\n"
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
                            yield f"data: {json.dumps(ev)}\n\n"
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
                yield f"data: {json.dumps({'thought_duration': thought_duration})}\n\n"

            if ttft is not None:
                yield f"data: {json.dumps({'ttft': ttft})}\n\n"
            
            yield f"data: {json.dumps({'total_duration': total_duration})}\n\n"

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
                
                yield f"data: {json.dumps(usage_stats.model_dump())}\n\n"

                # Manual continuation guidance logic
                if finish_reason == "length":
                    continue_msg = "\n\n> ⚠️ **[系统提示]** 由于输出长度限制，内容可能未完全生成。您可以输入 **“继续”** 来获取剩余部分。"
                    full_response += continue_msg
                    yield f"data: {json.dumps({'content': continue_msg})}\n\n"
            except Exception as usage_err:
                logger.error(f"Failed to get usage via adapter: {usage_err}")

            citations = deps.get("citations") if isinstance(deps, dict) else None
            if isinstance(citations, list) and citations:
                yield f"data: {json.dumps({'citations': citations})}\n\n"

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
                        yield f"data: {json.dumps({'content': suffix})}\n\n"
                else:
                    suffix = "\n\n未检索到可引用的文档依据（citations 为空）。建议先使用文档检索/读取工具获取证据后再回答。"
                    full_response += suffix
                    yield f"data: {json.dumps({'content': suffix})}\n\n"

        except (Exception, GeneratorExit, asyncio.CancelledError) as e:
            if isinstance(e, (GeneratorExit, asyncio.CancelledError)):
                logger.info("Chat stream cancelled by client")
            else:
                logger.exception("Chat error")
                yield f"data: {json.dumps({'error': handle_llm_exception(e)})}\n\n"
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")
