from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from app.mcp.manager import mcp_manager
from app.services.agent_store import agent_store
from app.services.model_factory import get_model
from app.services.chat_service import chat_service, ChatSession
from app.observability import get_trace_id
import json
import time
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

_NO_EVIDENCE_TEXT = "未在已配置的文档范围内找到可引用的依据。请尝试：调整关键词、缩小/扩大范围、或提供更具体的文件/段落线索。"
_DENIED_TEXT_PREFIX = "文档访问被拒绝"


def _should_enforce_citations(agent_config, provider: str | None) -> bool:
    if isinstance(provider, str) and provider.startswith("__doc"):
        return True
    if not agent_config:
        return False
    enabled = getattr(agent_config, "enabled_tools", None)
    if not isinstance(enabled, list):
        return False
    tools = set(str(x) for x in enabled if isinstance(x, str))
    if "builtin:docs_search_markdown" in tools or "builtin:docs_read_markdown" in tools:
        return True
    if getattr(agent_config, "id", None) in {"builtin-docs", "builtin-doc-orchestrator", "builtin-doc-retriever"}:
        return True
    return False


def _format_citations(citations: list[dict]) -> str:
    lines = []
    seen = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        path = c.get("path")
        if not isinstance(path, str) or not path:
            continue
        locator = None
        if isinstance(c.get("start_line"), int) and isinstance(c.get("end_line"), int):
            locator = f"L{c['start_line']}-L{c['end_line']}"
        elif isinstance(c.get("locator"), str) and c.get("locator"):
            locator = c["locator"]
        key = (path, locator)
        if key in seen:
            continue
        seen.add(key)
        if locator:
            lines.append(f"- {path}#{locator}")
        else:
            lines.append(f"- {path}")
    return "\n".join(lines)


def _apply_citation_policy(full_response: str, citations: list[dict], *, agent_config, provider: str | None) -> str:
    if not _should_enforce_citations(agent_config, provider):
        return full_response
    text = (full_response or "").strip()
    if citations:
        cite_block = _format_citations(citations)
        if not cite_block:
            return full_response
        if not text or text.upper() == "DONE":
            text = "已找到文档依据。"
        return f"{text}\n\n引用：\n{cite_block}"
    if _DENIED_TEXT_PREFIX in text:
        return full_response
    if _NO_EVIDENCE_TEXT.split("。", 1)[0] in text:
        return full_response
    return _NO_EVIDENCE_TEXT


def _build_gaps_payload(full_response: str, *, doc_root: str | None, provider: str | None) -> dict | None:
    text = (full_response or "").strip()
    if not text:
        return None
    suggestions = ["调整关键词", "提供更具体的文件/段落线索"]
    if isinstance(doc_root, str) and doc_root:
        suggestions.insert(1, f"确认 doc_root: {doc_root}")
    if _DENIED_TEXT_PREFIX in text:
        return {
            "kind": "denied",
            "items": ["文档访问被拒绝（权限/配置不允许读取目标文档）"],
            "suggestions": ["检查 allow_roots/deny_roots 配置", *suggestions],
            "doc_root": doc_root or "",
        }
    if _NO_EVIDENCE_TEXT.split("。", 1)[0] in text:
        return {
            "kind": "no_evidence",
            "items": ["未找到可引用的文档依据"],
            "suggestions": suggestions,
            "doc_root": doc_root or "",
        }
    if isinstance(provider, str) and provider.startswith("__doc"):
        return {
            "kind": "no_evidence",
            "items": ["当前回答缺少可引用依据，已被系统策略拦截"],
            "suggestions": suggestions,
            "doc_root": doc_root or "",
        }
    return None


class ChatRequest(BaseModel):
    message: str
    agent_id: str | None = None
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

@router.post("/stream")
async def chat_stream(http_request: Request, request: ChatRequest):
    # Initialize Chat Session
    chat_id = request.chat_id
    if not chat_id:
        chat = chat_service.create_chat(request.agent_id)
        chat_id = chat.id
    
    # Load History for Context
    history = []
    existing_chat = chat_service.get_chat(chat_id)
    if existing_chat:
        # Simple sliding window: last 20 messages
        msgs = existing_chat.messages[-20:]
        for m in msgs:
            if m.role == "user":
                history.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
            elif m.role == "assistant":
                history.append(ModelResponse(parts=[TextPart(content=m.content)]))

    # Save User Message to DB
    chat_service.add_message(chat_id, "user", request.message)
    
    async def event_generator():
        # Yield the chat ID first so frontend knows where we are
        trace_id = get_trace_id()
        yield f"data: {json.dumps({'chat_id': chat_id, 'trace_id': trace_id})}\n\n"
        
        try:
            # Get agent config if provided
            agent_config = None
            if request.agent_id:
                agent_config = agent_store.get_agent(request.agent_id)
            
            # Initialize MCP Manager and get tools for this agent (or all if no agent)
            tools = await mcp_manager.get_tools_for_agent(request.agent_id)
            
            # Determine model and system prompt
            provider = request.provider
            model_name = request.model
            system_prompt = request.system_prompt

            if agent_config:
                provider = provider or agent_config.provider
                model_name = model_name or agent_config.model
                system_prompt = system_prompt or agent_config.system_prompt
            
            # Final fallbacks if still None
            provider = provider or "openai"
            model_name = model_name or "gpt-4o"
            system_prompt = system_prompt or "You are a helpful assistant."

            model = get_model(provider, model_name)
            enforce_policy = _should_enforce_citations(agent_config, provider)

            # Create Pydantic AI Agent
            agent = Agent(
                model,
                system_prompt=system_prompt,
                tools=tools
            )
            event_queue: asyncio.Queue = asyncio.Queue()
            deps = {"citations": [], "chat_id": chat_id, "task_event_queue": event_queue, "trace_id": trace_id}
            if agent_config and getattr(agent_config, "doc_root", None):
                deps["doc_root"] = agent_config.doc_root
            
            full_response = ""
            thought_start_time = None
            thought_end_time = None

            async def merged_stream(result):
                nonlocal full_response, thought_start_time, thought_end_time
                stream_iter = result.stream_text().__aiter__()
                next_text = asyncio.create_task(stream_iter.__anext__())
                next_event = asyncio.create_task(event_queue.get())
                try:
                    while True:
                        if await http_request.is_disconnected():
                            raise asyncio.CancelledError()
                        done, _ = await asyncio.wait(
                            {next_text, next_event},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if next_event in done:
                            evt = next_event.result()
                            if evt is not None:
                                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                            next_event = asyncio.create_task(event_queue.get())

                        if next_text in done:
                            try:
                                message = next_text.result()
                            except StopAsyncIteration:
                                break
                            next_text = asyncio.create_task(stream_iter.__anext__())

                            if ("<thought>" in message or "<think>" in message) and thought_start_time is None:
                                thought_start_time = time.time()
                            if ("</thought>" in message or "</think>" in message) and thought_end_time is None:
                                thought_end_time = time.time()

                            if not message:
                                continue
                            if full_response and message.startswith(full_response):
                                new_content = message[len(full_response) :]
                            elif full_response and full_response.startswith(message):
                                new_content = ""
                            else:
                                new_content = message
                            if new_content:
                                full_response += new_content
                                if not enforce_policy:
                                    yield f"data: {json.dumps({'content': new_content}, ensure_ascii=False)}\n\n"
                finally:
                    if next_event and not next_event.done():
                        next_event.cancel()
                    while True:
                        try:
                            evt = event_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                        if evt is not None:
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            
            try:
                # Run with history
                async with agent.run_stream(request.message, message_history=history, deps=deps) as result:
                    async for item in merged_stream(result):
                        yield item
            except Exception as stream_err:
                # Handle models that don't support tools (like smaller Ollama models)
                err_str = str(stream_err)
                if "does not support tools" in err_str or "Tool use is not supported" in err_str:
                    logger.info("Model %s does not support tools, falling back to pure chat.", model_name)
                    # Re-create agent without tools
                    agent_no_tools = Agent(model, system_prompt=system_prompt)
                    full_response = ""
                    thought_start_time = None
                    thought_end_time = None
                    async with agent_no_tools.run_stream(request.message, message_history=history, deps=deps) as result:
                        async for message in result.stream_text():
                            # Track thinking time
                            if ("<thought>" in message or "<think>" in message) and thought_start_time is None:
                                thought_start_time = time.time()
                            if ("</thought>" in message or "</think>" in message) and thought_end_time is None:
                                thought_end_time = time.time()

                            if not message:
                                continue
                            if full_response and message.startswith(full_response):
                                new_content = message[len(full_response):]
                            elif full_response and full_response.startswith(message):
                                new_content = ""
                            else:
                                new_content = message
                            if new_content:
                                full_response += new_content
                                if not enforce_policy:
                                    yield f"data: {json.dumps({'content': new_content}, ensure_ascii=False)}\n\n"
                else:
                    raise stream_err
            
            # Calculate duration
            thought_duration = None
            if thought_start_time:
                if thought_end_time:
                    thought_duration = thought_end_time - thought_start_time
                else:
                    thought_duration = time.time() - thought_start_time

            if thought_duration:
                yield f"data: {json.dumps({'thought_duration': thought_duration})}\n\n"

            citations = deps.get("citations") if isinstance(deps, dict) else None
            if isinstance(citations, list):
                full_response = _apply_citation_policy(full_response, citations, agent_config=agent_config, provider=provider)
                if enforce_policy:
                    yield f"data: {json.dumps({'content': full_response}, ensure_ascii=False)}\n\n"
                if citations:
                    yield f"data: {json.dumps({'citations': citations})}\n\n"
                if enforce_policy and not citations:
                    doc_root = deps.get("doc_root") if isinstance(deps, dict) else None
                    gaps = _build_gaps_payload(full_response, doc_root=doc_root, provider=provider)
                    if isinstance(gaps, dict):
                        yield f"data: {json.dumps({'gaps': gaps}, ensure_ascii=False)}\n\n"

            # Save Assistant Message after completion
            chat_service.add_message(chat_id, "assistant", full_response, thought_duration)
            
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
