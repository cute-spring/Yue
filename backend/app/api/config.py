from fastapi import APIRouter, Body
from typing import Dict, Any
from app.services.config_service import config_service

router = APIRouter()

@router.get("/")
async def get_full_config():
    return config_service.get_config()

@router.get("/llm")
async def get_llm_config():
    return config_service.get_llm_config()

@router.post("/llm")
async def update_llm_config(config: Dict[str, Any] = Body(...)):
    return config_service.update_llm_config(config)

@router.get("/preferences")
async def get_preferences():
    return config_service.get_preferences()

@router.post("/preferences")
async def update_preferences(prefs: Dict[str, Any] = Body(...)):
    return config_service.update_preferences(prefs)
