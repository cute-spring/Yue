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

async def list_providers(refresh: bool = False) -> List[Dict[str, Any]]:
    providers_info = []
    llm_config = config_service.get_llm_config()
    registered_providers = get_registered_providers()
    
    for name, handler in registered_providers.items():
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
            
        # Ensure 'models' always contains all physically available models from the provider
        # and 'available_models' respects the user's allowlist configuration
        providers_info.append({
            "name": name,
            "configured": handler.configured(),
            "requirements": handler.requirements(),
            "available_models": available_models,
            "models": models or (config_enabled if isinstance(config_enabled, list) else []),
            "supports_model_refresh": _supports_model_refresh(name),
            "current_model": llm_config.get(f"{name}_model")
        })
    return providers_info

async def list_providers_structured(refresh: bool = False) -> List[ProviderInfo]:
    raw = await list_providers(refresh=refresh)
    return [ProviderInfo.model_validate(p) for p in raw]
