from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError, field_validator
import json
import os
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

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str):
        if v not in {"stdio"}:
            raise ValueError("unsupported transport")
        return v

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
