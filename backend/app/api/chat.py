from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent
from app.mcp.manager import mcp_manager
from app.services.agent_store import agent_store
from app.services.model_factory import get_model
import json

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    agent_id: str
    system_prompt: str | None = None

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    # Get agent config
    agent_config = agent_store.get_agent(request.agent_id)
    
    # Initialize MCP Manager and get tools for this agent
    tools = await mcp_manager.get_tools_for_agent(request.agent_id)
    
    # Determine model and system prompt
    if agent_config:
        model = get_model(agent_config.provider, agent_config.model)
        system_prompt = request.system_prompt or agent_config.system_prompt
    else:
        # Fallback for default or missing agent
        model = "openai:gpt-4o"
        system_prompt = request.system_prompt or "You are a helpful assistant."

    # Create Pydantic AI Agent
    agent = Agent(
        model,
        system_prompt=system_prompt,
        tools=tools
    )

    async def event_generator():
        last_length = 0
        async with agent.run_stream(request.message) as result:
            async for message in result.stream_text():
                # Get only the new part of the message
                new_content = message[last_length:]
                if new_content:
                    yield f"data: {json.dumps({'content': new_content})}\n\n"
                    last_length = len(message)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
