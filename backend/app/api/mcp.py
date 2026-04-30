from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError, field_validator
import json
import logging
import os
import shutil
from app.mcp.manager import mcp_manager
from app.mcp.registry import tool_registry
from app.mcp.templates import get_template, list_templates, render_template

router = APIRouter()
logger = logging.getLogger(__name__)

CONFIG_PATH = mcp_manager.config_path

@router.get("/")
async def list_configs():
    return mcp_manager.load_config()

@router.get("/tools")
async def list_tools():
    return await tool_registry.get_all_available_tools_metadata()

@router.get("/templates")
async def templates():
    return list_templates()

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

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str):
        if v not in {"stdio"}:
            raise ValueError("unsupported transport")
        return v


class TemplateValidationRequest(BaseModel):
    template_id: str
    values: Dict[str, Any] = {}


class TemplateValidationResponse(BaseModel):
    ok: bool
    rendered_config: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    error: Optional[str] = None

@router.post("/")
async def update_configs(configs: List[Dict[str, Any]]):
    try:
        incoming = [ServerConfig(**c).model_dump() for c in configs]
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
        validated = list(merged_map.values())
        with open(CONFIG_PATH, 'w') as f:
            json.dump(validated, f, indent=2)
        # Note: Changes require server restart to take full effect for now
        return validated
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.errors())
    except Exception as e:
        logger.exception("Failed to update MCP configs")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=TemplateValidationResponse)
async def validate_template_config(request: TemplateValidationRequest):
    template = get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Unknown MCP template: {request.template_id}")

    try:
        result = render_template(request.template_id, request.values)
        validated = ServerConfig(**result.rendered_config).model_dump()
        command = validated.get("command")
        if command and not shutil.which(command):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            local_cmd = os.path.join(project_root, command)
            if not os.path.exists(local_cmd):
                raise ValueError(f"Command not found locally: {command}")
        return TemplateValidationResponse(ok=True, rendered_config=validated, warnings=result.warnings)
    except ValueError as exc:
        return TemplateValidationResponse(ok=False, error=str(exc))
    except ValidationError as exc:
        return TemplateValidationResponse(ok=False, error=str(exc))

@router.post("/reload")
async def reload_mcp():
    try:
        await mcp_manager.cleanup()
        await mcp_manager.initialize()
        return {"status": "reloaded"}
    except Exception as e:
        logger.exception("Failed to reload MCP")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{server_name}")
async def delete_config(server_name: str):
    try:
        # Load existing
        existing = mcp_manager.load_config()
        # Filter out the server to delete
        updated = [c for c in existing if c.get("name") != server_name]
        
        if len(updated) == len(existing):
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
            
        # Write back to file
        with open(CONFIG_PATH, 'w') as f:
            json.dump(updated, f, indent=2)
            
        # Reload MCP to apply changes
        try:
            await mcp_manager.cleanup()
            await mcp_manager.initialize()
        except Exception as reload_err:
            logger.error(f"Failed to reload MCP after deletion: {reload_err}")
            
        return {"status": "deleted", "name": server_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete MCP server '{server_name}'")
        raise HTTPException(status_code=500, detail=str(e))
