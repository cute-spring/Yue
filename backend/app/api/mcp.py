from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError, field_validator, TypeAdapter
from collections import Counter
import json
import logging
from app.mcp.manager import mcp_manager

router = APIRouter()
logger = logging.getLogger(__name__)

CONFIG_PATH = mcp_manager.config_path

@router.get("/")
async def list_configs():
    return mcp_manager.load_config()

@router.get("/tools")
async def list_tools():
    return await mcp_manager.get_available_tools()

@router.get("/status")
async def status():
    return mcp_manager.get_status()

class ServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: str
    args: List[str] = []
    enabled: bool = True
    env: Optional[Dict[str, str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str):
        if v not in {"stdio"}:
            raise ValueError("unsupported transport")
        return v

SERVER_CONFIG_LIST_ADAPTER = TypeAdapter(List[ServerConfig])


def _format_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for e in errors:
        loc = e.get("loc", ())
        if isinstance(loc, (list, tuple)):
            path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in loc)
        else:
            path = "$"
        formatted.append(
            {
                "path": path,
                "message": e.get("msg") or "invalid value",
                "type": e.get("type"),
            }
        )
    return formatted


@router.post("/")
async def update_configs(configs: List[Dict[str, Any]] = Body(...)):
    try:
        incoming_models = SERVER_CONFIG_LIST_ADAPTER.validate_python(configs)
        incoming_names = [c.name for c in incoming_models]
        duplicates = sorted([name for name, count in Counter(incoming_names).items() if count > 1])
        if duplicates:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "issues": [{"path": "$.name", "message": f"duplicate server name: {n}", "type": "value_error"} for n in duplicates],
                },
            )
        incoming = [c.model_dump() for c in incoming_models]
        merged_map: Dict[str, Dict[str, Any]] = {}
        # Load existing
        existing = mcp_manager.load_config()
        for c in existing:
            name = c.get("name")
            if name:
                merged_map[name] = c
        # Upsert incoming
        for c in incoming:
            name = c.get("name")
            if name:
                if name in merged_map:
                    merged_map[name].update(c)
                else:
                    merged_map[name] = c
        validated_models = SERVER_CONFIG_LIST_ADAPTER.validate_python(list(merged_map.values()))
        validated = [c.model_dump() for c in validated_models]
        with open(CONFIG_PATH, 'w') as f:
            json.dump(validated, f, indent=2)
        # Note: Changes require server restart to take full effect for now
        return validated
    except ValidationError as ve:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "issues": _format_validation_errors(ve.errors()),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update MCP configs")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reload")
async def reload_mcp():
    try:
        await mcp_manager.cleanup()
        await mcp_manager.initialize()
        return {"status": "reloaded"}
    except Exception as e:
        logger.exception("Failed to reload MCP")
        raise HTTPException(status_code=500, detail=str(e))
