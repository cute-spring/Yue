from fastapi import APIRouter, Body, HTTPException
from dotenv import load_dotenv
from app.services.model_factory import list_supported_providers, list_providers, get_model, LLMProvider

router = APIRouter()

@router.get("/supported")
async def supported():
    return list_supported_providers()

@router.get("/providers")
async def providers():
    return await list_providers()

@router.post("/reload-env")
async def reload_env():
    load_dotenv(override=True)
    return {"status": "env reloaded", "providers": await list_providers()}

@router.post("/test/{provider}")
async def test_provider(provider: str, payload: dict = Body(None)):
    """
    Attempts to construct a model for the given provider to validate configuration.
    Optionally accepts {"model": "<model_name>"} in payload.
    """
    model_name = None
    if payload and isinstance(payload, dict):
        model_name = payload.get("model")
    try:
        # Validate provider name
        _ = LLMProvider(provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown provider")
    try:
        # If model construction succeeds, basic config is valid
        get_model(provider, model_name)
        return {"provider": provider, "ok": True}
    except Exception as e:
        return {"provider": provider, "ok": False, "error": str(e)}
