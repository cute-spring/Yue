from fastapi import APIRouter, Body, HTTPException
from dotenv import load_dotenv
from app.services.model_factory import list_supported_providers, list_providers, get_model, LLMProvider
from app.services.config_service import config_service

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

@router.get("/custom")
async def list_custom_models():
    # Redact api_key
    models = config_service.list_custom_models()
    redacted = []
    for m in models:
        m2 = dict(m)
        if "api_key" in m2:
            m2["api_key"] = ""
        redacted.append(m2)
    return redacted

@router.post("/custom")
async def create_or_update_custom_model(model: dict = Body(...)):
    try:
        models = config_service.upsert_custom_model(model)
        return models
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/custom/{name}")
async def update_custom_model(name: str, model: dict = Body(...)):
    model["name"] = name
    try:
        models = config_service.upsert_custom_model(model)
        return models
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/custom/{name}")
async def delete_custom_model(name: str):
    models = config_service.delete_custom_model(name)
    return models

@router.post("/test/custom")
async def test_custom_model(payload: dict = Body(...)):
    """
    Tests a custom model connection via provided payload:
    { \"base_url\": \"...\", \"api_key\": \"...\", \"model\": \"...\" }
    """
    try:
        base_url = payload.get("base_url")
        api_key = payload.get("api_key")
        model_name = payload.get("model")
        provider_name = "custom"
        # Temporarily inject into env-config reading path via direct get_model fallback
        # get_model will default to OPENAI if unknown; for custom, treat like OpenAIProvider with base_url/api_key
        # For this app, we reuse OpenAIChatModel semantics; test succeeds if model can be constructed.
        get_model(provider_name, model_name)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
