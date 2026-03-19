import asyncio
import logging
from typing import Optional, List, Dict, Any
from .base import LLMProvider, ProviderInfo
from .registry import get_registered_providers, list_registered_providers
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

_MODEL_REFRESH_SUPPORTED_PROVIDERS = {
    LLMProvider.OPENAI.value,
    LLMProvider.GEMINI.value,
    LLMProvider.OLLAMA.value,
    LLMProvider.LITELLM.value,
}

def _supports_model_refresh(provider_name: str) -> bool:
    return provider_name.lower() in _MODEL_REFRESH_SUPPORTED_PROVIDERS

def get_model(provider_name: str, model_name: Optional[str] = None):
    providers = get_registered_providers()
    handler = providers.get(provider_name.lower()) or providers.get(LLMProvider.OPENAI.value)
    if not handler:
        raise ValueError(f"Provider {provider_name} not found and fallback to OpenAI failed.")
    return handler.build(model_name)

def list_supported_providers() -> List[str]:
    return list_registered_providers()

async def list_providers(refresh: bool = False, check_connectivity: bool = False) -> List[Dict[str, Any]]:
    providers_info = []
    llm_config = config_service.get_llm_config()
    registered_providers = get_registered_providers()
    
    # Simple turn on/off provider logic
    enabled_providers_str = llm_config.get("enabled_providers")
    enabled_providers = None
    if enabled_providers_str:
        enabled_providers = [p.strip().lower() for p in enabled_providers_str.split(",") if p.strip()]
    
    for name, handler in registered_providers.items():
        # Filter by enabled_providers if configured
        if enabled_providers is not None and name.lower() not in enabled_providers:
            continue
            
        try:
            models = await handler.list_models(refresh=refresh)
        except Exception:
            logger.exception("Provider list_models error: %s", name)
            models = []
            
        config_enabled = llm_config.get(f"{name}_enabled_models")
        enabled_mode = llm_config.get(f"{name}_enabled_models_mode")
        use_allowlist = enabled_mode == "allowlist"
        
        # available_models is used for picking in dropdowns (filtered by allowlist)
        # models (all_models) is used in Settings to allow enabling new ones
        if isinstance(config_enabled, list) and (use_allowlist or (config_enabled and len(config_enabled) > 0)):
            available_models = [m for m in models if m in config_enabled] if models else config_enabled
        else:
            available_models = models
        capability_models = models or (config_enabled if isinstance(config_enabled, list) else [])
        model_capabilities = {
            model_name: config_service.get_model_capabilities(name, model_name)
            for model_name in capability_models
        }
        
        explicit_model_capabilities = {}
        for model_name in capability_models:
            model_info = config_service.get_model_info(f"{name}/{model_name}")
            if model_info and "capabilities" in model_info:
                explicit_model_capabilities[model_name] = model_info["capabilities"]
        
        is_configured = handler.configured()
        if not is_configured:
            available_models = []
        provider_data = {
            "name": name,
            "configured": is_configured,
            "requirements": handler.requirements(),
            "available_models": available_models,
            "models": models or (config_enabled if isinstance(config_enabled, list) else []),
            "model_capabilities": model_capabilities,
            "explicit_model_capabilities": explicit_model_capabilities,
            "supports_model_refresh": _supports_model_refresh(name),
            "current_model": llm_config.get(f"{name}_model"),
            "description": handler.__doc__ or f"{name} provider",
            "status": "online" if is_configured and models else ("unknown" if not is_configured else "offline")
        }
        
        if check_connectivity and is_configured:
            try:
                # Shallow connectivity check: list models with a short timeout
                # We already called list_models above, so we can just use that result if we want,
                # but if check_connectivity is True, we might want to force a fresh check.
                if not models:
                    models = await asyncio.wait_for(handler.list_models(refresh=True), timeout=5.0)
                provider_data["status"] = "online" if models else "offline"
                provider_data["model_count"] = len(models)
            except Exception as e:
                logger.warning(f"Connectivity check failed for {name}: {e}")
                provider_data["status"] = "error"
                provider_data["error"] = str(e)
        
        providers_info.append(provider_data)
        
    return providers_info

async def list_providers_structured(refresh: bool = False) -> List[ProviderInfo]:
    raw = await list_providers(refresh=refresh)
    return [ProviderInfo.model_validate(p) for p in raw]
