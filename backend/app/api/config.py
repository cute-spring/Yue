from fastapi import APIRouter, Body
from typing import Dict, Any
from app.services.config_service import config_service

router = APIRouter()

@router.get("/")
async def get_full_config():
    return config_service.get_config()

@router.get("/llm")
async def get_llm_config():
    # Return a redacted view of LLM config to avoid leaking secrets
    raw = config_service.get_llm_config()
    redacted = {}
    for k, v in raw.items():
        if k.endswith("_api_key"):
            # Do not expose API keys via GET
            redacted[k] = ""
        else:
            redacted[k] = v
    return redacted

@router.post("/llm")
async def update_llm_config(config: Dict[str, Any] = Body(...)):
    return config_service.update_llm_config(config)

@router.get("/preferences")
async def get_preferences():
    return config_service.get_preferences()

@router.post("/preferences")
async def update_preferences(prefs: Dict[str, Any] = Body(...)):
    return config_service.update_preferences(prefs)

@router.get("/doc_access")
async def get_doc_access():
    return config_service.get_doc_access()

@router.post("/doc_access")
async def update_doc_access(doc_access: Dict[str, Any] = Body(...)):
    return config_service.update_doc_access(doc_access)
