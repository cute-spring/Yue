from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel
from pydantic_ai import Agent
from app.services.model_factory import get_model
import json
import logging
import re
import ast
from app.services.agent_store import agent_store, AgentConfig
from app.mcp.manager import mcp_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_enabled_tools(raw: list[str], available_tools: list[dict]) -> list[str]:
    name_to_ids: dict[str, list[str]] = {}
    for t in available_tools:
        name = t.get("name")
        tid = t.get("id")
        if not name or not tid:
            continue
        name_to_ids.setdefault(name, []).append(tid)

    normalized: list[str] = []
    for x in raw:
        if not isinstance(x, str):
            continue
        if ":" in x:
            normalized.append(x)
        elif x in name_to_ids and len(name_to_ids[x]) == 1:
            normalized.append(name_to_ids[x][0])
        else:
            normalized.append(x)
    return normalized


def _extract_json_object(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Empty model output")

    def _loads_object(s: str) -> dict:
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        try:
            obj = ast.literal_eval(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        raise ValueError("Invalid JSON/Python object")

    candidate = text.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        return _loads_object(candidate)

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", candidate, re.IGNORECASE)
    if fenced:
        inner = fenced.group(1).strip()
        if inner.startswith("{") and inner.endswith("}"):
            return _loads_object(inner)

    first = candidate.find("{")
    if first == -1:
        raise ValueError("No JSON object found in model output")

    depth = 0
    end = None
    for i, ch in enumerate(candidate[first:], start=first):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError("Unterminated JSON object in model output")

    return _loads_object(candidate[first:end])


def _classify_tool_risk(tool_id: str, tool_meta: Optional[dict]) -> str:
    if not tool_id:
        return "unknown"

    tid = (tool_id or "").lower()
    name = (tool_meta or {}).get("name", "")
    desc = (tool_meta or {}).get("description", "")
    server = (tool_meta or {}).get("server", "")
    hay = " ".join([tid, str(name).lower(), str(desc).lower(), str(server).lower()])

    if any(x in hay for x in ["http", "web", "browser", "fetch", "crawl", "scrape"]):
        return "network"
    if tid.startswith("builtin:docs_") or "docs_" in hay:
        return "read"
    if any(x in hay for x in ["write", "edit", "delete", "remove", "create", "update", "save", "patch", "upload"]):
        return "write"
    if any(x in hay for x in ["read", "list", "search", "get", "query"]):
        return "read"
    return "unknown"


def _normalize_tool_reason_keys(reasons: dict, available_tools: list[dict]) -> dict[str, str]:
    if not isinstance(reasons, dict):
        return {}

    name_to_ids: dict[str, list[str]] = {}
    for t in available_tools:
        name = t.get("name")
        tid = t.get("id")
        if name and tid:
            name_to_ids.setdefault(name, []).append(tid)

    out: dict[str, str] = {}
    for k, v in reasons.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        key = k
        if ":" not in key and key in name_to_ids and len(name_to_ids[key]) == 1:
            key = name_to_ids[key][0]
        out[key] = v.strip()
    return out


class GenerateAgentRequest(BaseModel):
    description: str
    provider: Optional[str] = None
    model: Optional[str] = None
    existing_tools: list[str] = []
    update_tools: bool = True


class GenerateAgentResponse(BaseModel):
    name: str
    system_prompt: str
    enabled_tools: list[str] = []
    recommended_tools: list[str] = []
    tool_reasons: dict[str, str] = {}
    tool_risks: dict[str, str] = {}

@router.get("/", response_model=List[AgentConfig])
async def list_agents():
    return agent_store.list_agents()

@router.post("/generate", response_model=GenerateAgentResponse)
async def generate_agent(req: GenerateAgentRequest):
    description = (req.description or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description is required")

    available_tools = await mcp_manager.get_available_tools()
    tool_lines = []
    for t in available_tools:
        tid = t.get("id", "")
        name = t.get("name", "")
        server = t.get("server", "")
        desc = t.get("description", "")
        if tid and name:
            tool_lines.append(f"- {tid} | {name} | {server} | {desc}")
    tools_context = "\n".join(tool_lines) if tool_lines else "(no tools available)"

    provider = (req.provider or "openai").strip()
    model_name = (req.model or "gpt-4o").strip()

    generator_system = (
        "You are a senior AI Agent architect. Convert a user's natural-language request into a practical Agent configuration.\n"
        "You MUST output a single JSON object and nothing else (no markdown, no code fences).\n\n"
        "JSON schema:\n"
        "{\n"
        '  "name": "A concise professional name (<= 40 chars)",\n'
        '  "system_prompt": "A high-quality system prompt (include: role, scope/boundaries, workflow, output format, prohibitions)",\n'
        '  "enabled_tools": ["Tool ID list (prefer composite IDs like server:name or builtin:tool)"],\n'
        '  "tool_reasons": {"tool_id": "one short reason why this tool is needed"}\n'
        "}\n\n"
        "Constraints:\n"
        "- Write system_prompt in the same language as the user's request; if unclear, default to English.\n"
        "- Only choose enabled_tools from the Available Tools list. Recommend 0-6 tools; if unsure, return an empty list.\n"
        "- If the request involves searching local directories, prefer docs_search_markdown_dir / docs_read_markdown_dir.\n"
        "- If the request only needs Yue/docs, prefer docs_search_markdown / docs_read_markdown.\n\n"
        "- tool_reasons must only contain keys from enabled_tools; omit it or use an empty object if no tools.\n\n"
        f"Available Tools:\n{tools_context}\n"
    )

    user_prompt = f"User request: {description}"

    try:
        model = get_model(provider, model_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_text = ""
    last_error: Optional[str] = None
    for attempt in range(2):
        agent = Agent(model, system_prompt=generator_system)
        full_text = ""
        last_length = 0
        try:
            async with agent.run_stream(user_prompt) as result:
                async for message in result.stream_text():
                    if len(message) > last_length:
                        full_text += message[last_length:]
                        last_length = len(message)
        except Exception as e:
            logger.exception("Smart generate failed")
            raise HTTPException(status_code=500, detail=str(e))

        try:
            raw_obj = _extract_json_object(full_text)
            parsed = GenerateAgentResponse.model_validate(raw_obj)
            last_error = None
            break
        except Exception as e:
            last_error = str(e)
            user_prompt = (
                "Your previous output was invalid. Return ONLY a single JSON object that matches the schema.\n"
                "No markdown, no code fences, no extra text.\n\n"
                f"User request: {description}\n\n"
                f"Invalid output:\n{full_text}"
            )
            continue

    if last_error is not None:
        raise HTTPException(status_code=500, detail=f"Invalid model output: {last_error}")

    recommended = _normalize_enabled_tools(parsed.enabled_tools or [], available_tools)
    parsed.recommended_tools = recommended
    reasons = _normalize_tool_reason_keys(parsed.tool_reasons, available_tools)
    recommended_set = set(recommended)
    parsed.tool_reasons = {k: v for k, v in reasons.items() if k in recommended_set and v}
    meta_by_id = {t.get("id"): t for t in available_tools if t.get("id")}
    parsed.tool_risks = {tid: _classify_tool_risk(tid, meta_by_id.get(tid)) for tid in recommended}

    if not req.update_tools:
        tools = req.existing_tools if isinstance(req.existing_tools, list) else []
    else:
        tools = recommended or req.existing_tools or []

    parsed.enabled_tools = _normalize_enabled_tools(tools, available_tools)
    return parsed

@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str):
    agent = agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/", response_model=AgentConfig)
async def create_agent(agent: AgentConfig):
    tools = await mcp_manager.get_available_tools()
    agent.enabled_tools = _normalize_enabled_tools(agent.enabled_tools, tools)
    return agent_store.create_agent(agent)

@router.put("/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: str, updates: dict = Body(...)):
    if "enabled_tools" in updates and isinstance(updates["enabled_tools"], list):
        tools = await mcp_manager.get_available_tools()
        updates["enabled_tools"] = _normalize_enabled_tools(updates["enabled_tools"], tools)
    agent = agent_store.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if not agent_store.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "success"}
