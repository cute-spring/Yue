from fastapi import APIRouter
from dotenv import load_dotenv
from app.services.model_factory import list_supported_providers, list_providers

router = APIRouter()

@router.get("/supported")
async def supported():
    return list_supported_providers()

@router.get("/providers")
async def providers():
    return list_providers()

@router.post("/reload-env")
async def reload_env():
    load_dotenv(override=True)
    return {"status": "env reloaded", "providers": list_providers()}
