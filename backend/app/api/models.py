from fastapi import APIRouter, Body, HTTPException, Query
from dotenv import load_dotenv
from app.services.llm import (
    LLMProvider,
    get_model,
    list_providers,
    list_supported_providers,
)
from app.services.llm.providers.custom import build_custom_model_from_payload, fetch_custom_endpoint_models
from app.services.llm.utils import handle_llm_exception
from app.services.config_service import config_service

router = APIRouter()

@router.get("/supported")
async def supported():
    return list_supported_providers()

@router.get("/providers")
async def providers(refresh: bool = Query(default=False)):
    return await list_providers(refresh=refresh)

@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str, refresh: bool = Query(default=False)):
    """Admin endpoint to fetch ALL models for a specific provider with capabilities."""
    providers_list = await list_providers(refresh=refresh, admin_mode=True, target_provider=provider)
    if providers_list:
        p = providers_list[0]
        return {
            "name": p["name"],
            "models": p["models"],
            "available_models": p["available_models"],
            "model_capabilities": p["model_capabilities"],
            "explicit_model_capabilities": p["explicit_model_capabilities"]
        }
    raise HTTPException(status_code=404, detail="Provider not found")

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
    if provider.lower() == "custom":
        return await test_custom_model(payload or {})

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
        return {"provider": provider, "ok": False, "error": handle_llm_exception(e)}

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

@router.get("/custom/{name}/models")
async def get_custom_model_endpoint_models(name: str, refresh: bool = Query(default=False)):
    models = config_service.list_custom_models()
    entry = next((model for model in models if model.get("name") == name), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Custom model not found")

    llm_config = config_service.get_llm_config()
    discovered = await fetch_custom_endpoint_models(entry, refresh=refresh, llm_config=llm_config)
    aliases = [
        model_id if model_id == name or model_id.startswith(f"{name}/") else f"{name}/{model_id}"
        for model_id in discovered
    ]
    if not aliases and entry.get("model"):
        aliases = [f"{name}/{entry['model']}"]
    elif not aliases:
        aliases = [name]

    config_enabled = llm_config.get("custom_enabled_models")
    enabled_mode = llm_config.get("custom_enabled_models_mode")
    if isinstance(config_enabled, list) and (enabled_mode == "allowlist" or config_enabled):
        available_models = [model for model in aliases if model in config_enabled]
    else:
        available_models = aliases

    model_capabilities = {
        model_name: config_service.get_model_capabilities("custom", model_name)
        for model_name in aliases
    }
    explicit_model_capabilities = {}
    for model_name in aliases:
        model_info = config_service.get_model_info(f"custom/{model_name}")
        if model_info and "capabilities" in model_info:
            explicit_model_capabilities[model_name] = model_info["capabilities"]

    return {
        "name": "custom",
        "custom_model_name": name,
        "models": aliases,
        "available_models": available_models,
        "model_capabilities": model_capabilities,
        "explicit_model_capabilities": explicit_model_capabilities,
    }

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
        provider_name = payload.get("provider") or "custom"
        build_custom_model_from_payload(
            provider_name=provider_name,
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
