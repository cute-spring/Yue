from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.skill_service import skill_registry, skill_router, SkillPolicyGate, SkillSpec
from app.services.agent_store import agent_store
from app.services.config_service import config_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SkillSelectionRequest(BaseModel):
    agent_id: str
    task: str
    mode: str = "auto" # manual | auto | hybrid
    requested_skill: Optional[str] = None # name/version

class SkillSelectionResponse(BaseModel):
    selected_skill: Optional[Dict[str, str]] = None # name, version
    selection_mode: str
    reason_code: str
    fallback_used: bool
    effective_tools: List[str]

@router.get("/", response_model=List[SkillSpec])
async def list_skills():
    """List all loaded skills."""
    return skill_registry.list_skills()

@router.get("/{name}", response_model=SkillSpec)
async def get_skill(name: str, version: Optional[str] = None):
    """Get detailed metadata for a specific skill."""
    skill = skill_registry.get_skill(name, version)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {name} not found")
    return skill

@router.post("/reload")
async def reload_skills():
    """Manual reload of skills from disk."""
    skill_registry.load_all()
    return {"status": "success", "count": len(skill_registry.list_skills())}

@router.post("/select", response_model=SkillSelectionResponse)
async def select_skill(request: SkillSelectionRequest):
    """Resolve the best skill for an agent and task."""
    agent = agent_store.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")
        
    skill = skill_router.route(agent, request.task, requested_skill=request.requested_skill)
    
    if not skill:
        return SkillSelectionResponse(
            selected_skill=None,
            selection_mode=request.mode,
            reason_code="no_matching_skill",
            fallback_used=True,
            effective_tools=agent.enabled_tools
        )
        
    # Intersection logic
    effective_tools = SkillPolicyGate.check_tool_intersection(agent.enabled_tools, skill.constraints.allowed_tools if skill.constraints else None)
    
    return SkillSelectionResponse(
        selected_skill={"name": skill.name, "version": skill.version},
        selection_mode=request.mode,
        reason_code="skill_selected",
        fallback_used=False,
        effective_tools=effective_tools
    )

@router.post("/tool/select_runtime_skill")
async def select_runtime_skill(request: Dict[str, Any] = Body(...)):
    """Tool entrypoint for controlled runtime skill selection."""
    feature_flags = config_service.get_feature_flags()
    if not feature_flags.get("skill_runtime_enabled", True):
        raise HTTPException(status_code=403, detail="skill_selection_unavailable")
    if not feature_flags.get("skill_selector_tool_enabled", True):
        raise HTTPException(status_code=403, detail="skill_selector_disabled")

    agent_id = request.get("agent_id")
    task = request.get("task")
    mode = request.get("mode", "hybrid")
    requested_skill = request.get("requested_skill")

    if not agent_id or not task:
        raise HTTPException(status_code=400, detail="invalid_request")

    agent = agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    if getattr(agent, "skill_mode", "off") == "off":
        return SkillSelectionResponse(
            selected_skill=None,
            selection_mode=mode,
            reason_code="skill_selection_unavailable",
            fallback_used=True,
            effective_tools=agent.enabled_tools
        )

    resolved_skill = skill_router.route(agent, task, requested_skill=requested_skill)
    if not resolved_skill:
        return SkillSelectionResponse(
            selected_skill=None,
            selection_mode=mode,
            reason_code="no_matching_skill",
            fallback_used=True,
            effective_tools=agent.enabled_tools
        )

    effective_tools = SkillPolicyGate.check_tool_intersection(
        agent.enabled_tools,
        resolved_skill.constraints.allowed_tools if resolved_skill.constraints else None
    )
    return SkillSelectionResponse(
        selected_skill={"name": resolved_skill.name, "version": resolved_skill.version},
        selection_mode=mode,
        reason_code="skill_selected",
        fallback_used=False,
        effective_tools=effective_tools
    )
