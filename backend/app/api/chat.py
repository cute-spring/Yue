from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from app.mcp.manager import mcp_manager
from app.services.agent_store import agent_store
from app.services.model_factory import get_model
from app.services.chat_service import chat_service, ChatSession
import json
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

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
        yield f"data: {json.dumps({'chat_id': chat_id})}\n\n"
        
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
                if agent_config.doc_roots:
                    if "可检索目录" not in system_prompt:
                        roots = "\n".join(f"- {r}" for r in agent_config.doc_roots)
                        system_prompt += f"\n\n可检索目录（优先使用）：\n{roots}"
            
            # Final fallbacks if still None
            provider = provider or "openai"
            model_name = model_name or "gpt-4o"
            system_prompt = system_prompt or "You are a helpful assistant."

            # Inject thinking process instruction if not present
            if "<thought>" not in system_prompt:
                system_prompt += (
                    "\n\nIMPORTANT: You must ALWAYS start your response by thinking step-by-step about the user's request. "
                    "Enclose your thinking process within <thought>...</thought> tags. "
                    "After your thinking process is complete, provide your final answer."
                )

            model = get_model(provider, model_name)

            # Create Pydantic AI Agent
            agent = Agent(
                model,
                system_prompt=system_prompt,
                tools=tools
            )
            deps = {"citations": []}
            if agent_config and agent_config.doc_roots:
                deps["doc_roots"] = agent_config.doc_roots
            
            last_length = 0
            full_response = ""
            thought_start_time = None
            thought_end_time = None
            
            try:
                # Run with history
                async with agent.run_stream(request.message, message_history=history, deps=deps) as result:
                    async for message in result.stream_text():
                        # Track thinking time
                        if ("<thought>" in message or "<think>" in message) and thought_start_time is None:
                            thought_start_time = time.time()
                        if ("</thought>" in message or "</think>" in message) and thought_end_time is None:
                            thought_end_time = time.time()

                        # Get only the new part of the message
                        new_content = message[last_length:]
                        if new_content:
                            full_response += new_content
                            yield f"data: {json.dumps({'content': new_content})}\n\n"
                            last_length = len(message)
            except Exception as stream_err:
                # Handle models that don't support tools (like smaller Ollama models)
                err_str = str(stream_err)
                if "does not support tools" in err_str or "Tool use is not supported" in err_str:
                    logger.info("Model %s does not support tools, falling back to pure chat.", model_name)
                    # Re-create agent without tools
                    agent_no_tools = Agent(model, system_prompt=system_prompt)
                    last_length = 0
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

                            new_content = message[last_length:]
                            if new_content:
                                full_response += new_content
                                yield f"data: {json.dumps({'content': new_content})}\n\n"
                                last_length = len(message)
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
            if isinstance(citations, list) and citations:
                yield f"data: {json.dumps({'citations': citations})}\n\n"

            # Save Assistant Message after completion
            chat_service.add_message(chat_id, "assistant", full_response, thought_duration)
            
        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
