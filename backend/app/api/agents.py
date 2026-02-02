from fastapi import APIRouter, HTTPException, Body
from typing import List
from app.services.agent_store import agent_store, AgentConfig
from app.mcp.manager import mcp_manager

router = APIRouter()

@router.get("/", response_model=List[AgentConfig])
async def list_agents():
    return agent_store.list_agents()

@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str):
    agent = agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/", response_model=AgentConfig)
async def create_agent(agent: AgentConfig):
    tools = await mcp_manager.get_available_tools()
    name_to_ids = {}
    for t in tools:
        name_to_ids.setdefault(t["name"], []).append(t["id"])
    normalized = []
    for x in agent.enabled_tools:
        if ":" in x:
            normalized.append(x)
        elif x in name_to_ids and len(name_to_ids[x]) == 1:
            normalized.append(name_to_ids[x][0])
        else:
            normalized.append(x)
    agent.enabled_tools = normalized
    return agent_store.create_agent(agent)

@router.put("/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: str, updates: dict = Body(...)):
    if "enabled_tools" in updates and isinstance(updates["enabled_tools"], list):
        tools = await mcp_manager.get_available_tools()
        name_to_ids = {}
        for t in tools:
            name_to_ids.setdefault(t["name"], []).append(t["id"])
        normalized = []
        for x in updates["enabled_tools"]:
            if ":" in x:
                normalized.append(x)
            elif x in name_to_ids and len(name_to_ids[x]) == 1:
                normalized.append(name_to_ids[x][0])
            else:
                normalized.append(x)
        updates["enabled_tools"] = normalized
    agent = agent_store.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if not agent_store.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "success"}
