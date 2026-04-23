from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.skill_service import (
    build_stage4_lite_runtime_seams,
    get_stage4_lite_runtime_context,
)
from app.services.skills import SkillSpec, SkillSummary
from app.services.agent_store import agent_store
from app.services.config_service import config_service
from app.services.skills.runtime_catalog import RUNTIME_MODE_IMPORT_GATE, resolve_skill_runtime_mode
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SkillSelectionResponse(BaseModel):
    selected_skill: Optional[Dict[str, str]] = None # name, version
    reason_code: str
    fallback_used: bool
    

def _runtime_seams():
    return build_stage4_lite_runtime_seams()


def _runtime_context():
    return get_stage4_lite_runtime_context()


def _build_selection_contract(
    reason_code: str,
    requested_skill: Optional[str],
    visible_skill_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    trace = []
    if visible_skill_refs is not None:
        trace.append({
            "stage": "resolve_visible_skills",
            "status": "completed",
            "visible_skill_refs": visible_skill_refs,
        })
    trace.append({
        "stage": "fallback",
        "status": "completed",
        "reason_code": reason_code,
    })
    return {
        "selected": None,
        "candidates": [],
        "scores": [],
        "reason": {
            "code": reason_code,
            "requested_skill": requested_skill,
            "fallback_used": True,
        },
        "fallback_used": True,
        "stage_trace": trace,
    }


def _build_selection_response(
    *,
    selected_skill: Optional[Dict[str, str]],
    reason_code: str,
    fallback_used: bool,
    selection_mode: str,
    effective_tools: List[str],
    include_debug_contract: bool,
    contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "selected_skill": selected_skill,
        "reason_code": reason_code,
        "fallback_used": fallback_used,
    }
    if include_debug_contract:
        payload["selection_mode"] = selection_mode
        payload["effective_tools"] = effective_tools
        if contract:
            payload.update({key: value for key, value in contract.items() if key != "fallback_used"})
    elif contract:
        logger.debug("skill selection contract (suppressed in non-debug response): %s", contract)
    return payload

@router.get("/", response_model=List[SkillSpec])
async def list_skills():
    """List all loaded skills."""
    return _runtime_context().skill_registry.list_skills()

@router.get("/summary", response_model=List[SkillSummary])
async def list_skill_summaries():
    return _runtime_context().skill_registry.list_summaries()

@router.get("/{name}", response_model=SkillSpec)
async def get_skill(name: str, version: Optional[str] = None):
    """Get detailed metadata for a specific skill."""
    skill = _runtime_context().skill_registry.get_skill(name, version)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {name} not found")
    return skill

@router.post("/reload")
async def reload_skills(layer: str = Query("all")):
    if resolve_skill_runtime_mode() == RUNTIME_MODE_IMPORT_GATE:
        raise HTTPException(status_code=409, detail="skill_reload_unavailable_in_import_gate_mode")
    allowed_layers = {"all", "builtin", "workspace", "user"}
    if layer not in allowed_layers:
        raise HTTPException(status_code=400, detail=f"Invalid layer '{layer}'")
    runtime_registry = _runtime_context().skill_registry
    runtime_registry.load_all(layer=layer)
    return {"status": "success", "count": len(runtime_registry.list_skills()), "layer": layer}

@router.post("/tool/select_runtime_skill")
async def select_runtime_skill(request: Dict[str, Any] = Body(...)):
    """Tool entrypoint for controlled runtime skill selection."""
    feature_flags = config_service.get_feature_flags()
    if not feature_flags.get("skill_runtime_enabled", True):
        raise HTTPException(status_code=403, detail="skill_selection_unavailable")

    agent_id = request.get("agent_id")
    task = request.get("task")
    mode = request.get("mode", "hybrid")
    requested_skill = request.get("requested_skill")

    if not agent_id or not task:
        raise HTTPException(status_code=400, detail="invalid_request")

    agent = agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    runtime_context = _runtime_context()
    runtime_router = runtime_context.skill_router
    runtime_seams = _runtime_seams()

    include_debug_contract = bool(feature_flags.get("skill_runtime_debug_contract_enabled", False))
    if getattr(agent, "skill_mode", "off") == "off":
        contract = None
        if include_debug_contract:
            contract = _build_selection_contract(
                reason_code="skill_selection_unavailable",
                requested_skill=requested_skill,
                visible_skill_refs=runtime_seams.visibility_resolver.resolve_visible_skill_refs(agent),
            )
        return _build_selection_response(
            selected_skill=None,
            reason_code="skill_selection_unavailable",
            fallback_used=True,
            selection_mode=mode,
            effective_tools=agent.enabled_tools,
            include_debug_contract=include_debug_contract,
            contract=contract,
        )

    resolved_skill = runtime_router.route(agent, task, requested_skill=requested_skill)
    contract = None
    if include_debug_contract:
        contract = runtime_router.route_with_contract(agent, task, requested_skill=requested_skill)
    if not resolved_skill:
        return _build_selection_response(
            selected_skill=None,
            reason_code="no_matching_skill",
            fallback_used=True,
            selection_mode=mode,
            effective_tools=agent.enabled_tools,
            include_debug_contract=include_debug_contract,
            contract=contract,
        )

    effective_tools = runtime_seams.tool_capability_provider.resolve_effective_tools(
        agent_tools=agent.enabled_tools,
        skill=resolved_skill,
    )
    return _build_selection_response(
        selected_skill={"name": resolved_skill.name, "version": resolved_skill.version},
        reason_code="skill_selected",
        fallback_used=False,
        selection_mode=mode,
        effective_tools=effective_tools,
        include_debug_contract=include_debug_contract,
        contract=contract,
    )
