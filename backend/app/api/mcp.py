from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
import json
import os
from app.mcp.manager import mcp_manager

router = APIRouter()

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

@router.post("/")
async def update_configs(configs: List[Dict[str, Any]]):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(configs, f, indent=2)
        # Note: Changes require server restart to take full effect for now
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reload")
async def reload_mcp():
    try:
        await mcp_manager.cleanup()
        await mcp_manager.initialize()
        return {"status": "reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
