from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart, ImageUrl
from app.mcp.manager import mcp_manager
from app.services.agent_store import agent_store
from app.services.model_factory import get_model
from app.services.chat_service import chat_service, ChatSession
from app.utils.image_handler import save_base64_image, load_image_to_base64
import json
import time
import logging

logger = logging.getLogger(__name__)

# Token Management Constants
# DeepSeek Reasoner has 128k context. We set a safe limit of ~100k tokens.
# Heuristic: 1 token ~= 3 characters (conservative for code/mixed content).
EST_CHARS_PER_TOKEN = 3
MAX_CONTEXT_TOKENS = 100000
MAX_SINGLE_MSG_TOKENS = 20000  # Cap single messages to avoid one massive file read blocking everything

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // EST_CHARS_PER_TOKEN

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    images: list[str] | None = None
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

            tool_names = []
            for tool in tools:
                name = getattr(tool, "name", None)
                if not name:
                    name = getattr(tool, "__name__", None)
                if not name:
                    name = tool.__class__.__name__
                tool_names.append(name)

            yield f"data: {json.dumps({'meta': {'provider': provider, 'model': model_name, 'tools': tool_names, 'context_id': chat_id, 'agent_id': request.agent_id}})}\n\n"

            # Inject thinking process instruction if not present
            if "<thought>" not in system_prompt:
                system_prompt += (
                    "\n\nIMPORTANT: You must ALWAYS start your response by thinking step-by-step about the user's request. "
                    "Enclose your thinking process within <thought>...</thought> tags. "
                    "After your thinking process is complete, provide your final answer."
                )

            # Inject Mermaid visualization instructions (Enhanced DeepSeek/Doubao Style)
            if "mermaid" not in system_prompt.lower():
                system_prompt += (
                    "\n\nVISUALIZATION GUIDELINES - UML Diagram Generation:\n"
                    "You are an expert system architect who excels at visual communication through UML diagrams. "
                    "Your core principle: \"A picture is worth a thousand words\" - always visualize complex concepts.\n\n"
                    
                    "AUTOMATIC DIAGRAM GENERATION RULES:\n"
                    "1. **Proactive Visualization**: When users ask about ANY of these topics, IMMEDIATELY generate diagrams:\n"
                    "   - System architecture, microservices, or component relationships\n"
                    "   - Business processes, workflows, or data flow\n"
                    "   - User authentication, API flows, or request sequences\n"
                    "   - Database schemas, entity relationships, or data models\n"
                    "   - State machines, lifecycle flows, or decision trees\n"
                    "   - Deployment pipelines, CI/CD processes, or infrastructure\n\n"
                    
                    "2. **Diagram Type Selection** (Choose the most appropriate):\n"
                    "   - Sequence Diagram: API calls, user flows, time-based interactions\n"
                    "   - Flowchart/Activity: Business processes, decision logic, algorithms\n"
                    "   - Component/Deployment: System architecture, service relationships\n"
                    "   - Entity Relationship: Database schemas, data models\n"
                    "   - State Diagram: Object lifecycles, status transitions\n\n"
                    
                    "3. **Mermaid Syntax Standards**:\n"
                    "   - Always use ```mermaid code blocks with proper language identifier\n"
                    "   - Prefer 'graph TD' for top-down flow, 'graph LR' for horizontal layouts\n"
                    "   - Use 'sequenceDiagram' for interaction sequences\n"
                    "   - Keep node labels concise but descriptive (max 3-4 words)\n"
                    "   - Use meaningful IDs: [User], {API}, (Database), [[Service]]\n\n"
                    
                    "4. **Visual Design Principles**:\n"
                    "   - Start with clear entry points (Start, User, Request)\n"
                    "   - Show decision points with {Decision} and labeled branches\n"
                    "   - Use consistent styling: same node types = same shapes\n"
                    "   - Add color coding: green=success, red=error, blue=process\n"
                    "   - Include error handling paths and edge cases\n\n"
                    
                    "5. **Integration Best Practices**:\n"
                    "   - Place diagrams AFTER textual explanation for context\n"
                    "   - Reference diagram elements in your text (see 'Auth Service' in diagram)\n"
                    "   - Provide diagram legend if using custom symbols/colors\n"
                    "   - Generate multiple diagrams for complex multi-step processes\n\n"
                    
                    "EXAMPLE RESPONSE STRUCTURE:\n"
                    "Let me explain the OAuth2 authentication flow through a visual diagram:\n\n"
                    "```mermaid\n"
                    "sequenceDiagram\n"
                    "    participant User\n"
                    "    participant Browser\n"
                    "    participant AuthServer\n"
                    "    participant ResourceServer\n\n"
                    "    User->>Browser: Click Login\n"
                    "    Browser->>AuthServer: Redirect to /oauth/authorize\n"
                    "    AuthServer->>User: Show consent screen\n"
                    "    User->>AuthServer: Approve access\n"
                    "    AuthServer->>Browser: Return authorization code\n"
                    "    Browser->>AuthServer: Exchange code for token\n"
                    "    AuthServer->>Browser: Return access token\n"
                    "    Browser->>ResourceServer: Request resource with token\n"
                    "    ResourceServer->>Browser: Return protected data\n"
                    "```\n\n"
                    
                    "Remember: Visualize first, explain second. Users love diagrams!"
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
            if agent_config and getattr(agent_config, "doc_file_patterns", None):
                deps["doc_file_patterns"] = agent_config.doc_file_patterns
            
            last_length = 0
            full_response = ""
            thought_start_time = None
            thought_end_time = None
            
            try:
                # Prepare input
                user_input = request.message
                if request.images:
                    user_input = [request.message]
                    for img in request.images:
                        user_input.append(ImageUrl(url=img))

                # Run with history
                async with agent.run_stream(user_input, message_history=history, deps=deps) as result:
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
                    
                    # Prepare input
                    user_input = request.message
                    if request.images:
                        user_input = [request.message]
                        for img in request.images:
                            user_input.append(ImageUrl(url=img))

                    async with agent_no_tools.run_stream(user_input, message_history=history, deps=deps) as result:
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

            # Save Assistant Message after completion
            chat_service.add_message(chat_id, "assistant", full_response, thought_duration)
            
        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
