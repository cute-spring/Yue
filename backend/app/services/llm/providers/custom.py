import logging
import time
from typing import Optional, List, Any, Dict
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import (
    build_async_client,
    get_cache_ttl,
    get_model_cache,
    get_pydantic_ai_http_client,
    get_ssl_verify,
    handle_llm_exception,
)
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

def _normalize_custom_base_url(base_url: Optional[str]) -> Optional[str]:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return None
    cleaned = cleaned.removesuffix("/chat/completions").rstrip("/")
    return cleaned

def _custom_models_url(base_url: str) -> str:
    if base_url.endswith("/models"):
        return base_url
    return f"{base_url}/models"

def _extract_model_ids(payload: Any) -> List[str]:
    if isinstance(payload, dict):
        items = payload.get("data") or payload.get("models") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    model_ids: List[str] = []
    for item in items:
        if isinstance(item, str):
            model_ids.append(item)
            continue
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("name") or item.get("model")
            if isinstance(model_id, str) and model_id.strip():
                model_ids.append(model_id.strip())
    return model_ids

def _alias_custom_model(entry_name: str, model_id: str) -> str:
    if model_id == entry_name or model_id.startswith(f"{entry_name}/"):
        return model_id
    return f"{entry_name}/{model_id}"

async def fetch_custom_endpoint_models(
    entry: Dict[str, Any],
    *,
    refresh: bool = False,
    llm_config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    base_url = _normalize_custom_base_url(entry.get("base_url"))
    if not base_url:
        return []

    now = time.time()
    cache_key = f"custom::{entry.get('name') or ''}::{base_url}"
    model_cache = get_model_cache()
    cache = model_cache.get(cache_key)
    if cache and not refresh and (now - cache.get("ts", 0) < get_cache_ttl()):
        return cache.get("models", [])

    config = llm_config or config_service.get_llm_config()
    api_key = entry.get("api_key")
    headers = {}
    if isinstance(api_key, str) and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    try:
        async with build_async_client(timeout=2.5, verify=get_ssl_verify(), llm_config=config) as client:
            response = await client.get(_custom_models_url(base_url), headers=headers)
            if response.status_code == 200:
                model_ids = _extract_model_ids(response.json())
                model_cache[cache_key] = {"models": model_ids, "ts": now}
                return model_ids
            logger.warning("Custom model discovery failed for %s: HTTP %s", entry.get("name"), response.status_code)
    except Exception as exc:
        logger.warning("Custom model discovery error for %s: %s", entry.get("name"), handle_llm_exception(exc))

    return cache.get("models", []) if cache else []

def _resolve_custom_entry(customs: List[Dict[str, Any]], model_name: Optional[str]) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    if model_name:
        exact = next((item for item in customs if item.get("name") == model_name), None)
        if exact:
            return exact, exact.get("model") or model_name or "gpt-4o"

        for item in customs:
            entry_name = item.get("name")
            if isinstance(entry_name, str) and model_name.startswith(f"{entry_name}/"):
                return item, model_name[len(entry_name) + 1:]

    if customs:
        entry = customs[0]
        return entry, entry.get("model") or model_name or "gpt-4o"

    return None, model_name or "gpt-4o"

def build_custom_model_from_payload(
    *,
    provider_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Any:
    del provider_name  # Reserved for provider-specific custom transports.
    model = model_name or 'gpt-4o'
    normalized_api_key = api_key.strip() if isinstance(api_key, str) else api_key
    if normalized_api_key == "":
        normalized_api_key = None
    normalized_api_key = normalized_api_key or "local-openai-compatible"
    return OpenAIChatModel(
        model,
        provider=OpenAIProvider(
            base_url=_normalize_custom_base_url(base_url),
            api_key=normalized_api_key,
            http_client=get_pydantic_ai_http_client()
        )
    )

class CustomProviderImpl(SimpleProvider):
    name = LLMProvider.CUSTOM.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        models: List[str] = []
        for entry in customs:
            entry_name = entry.get("name")
            if not entry_name:
                continue
            discovered = await fetch_custom_endpoint_models(entry, refresh=refresh, llm_config=llm_config)
            if discovered:
                models.extend(_alias_custom_model(entry_name, model_id) for model_id in discovered)
                continue
            if entry.get("model"):
                models.append(_alias_custom_model(entry_name, entry["model"]))
            else:
                models.append(entry_name)
        return models
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        entry, resolved_model = _resolve_custom_entry(customs, model_name)
        if not entry:
            entry = {
                "base_url": llm_config.get("llm_base_url"),
                "api_key": llm_config.get("llm_api_key"),
                "model": llm_config.get("llm_model_name") or resolved_model
            }
        base_url = entry.get("base_url")
        api_key = entry.get("api_key")
        model = resolved_model or entry.get("model") or 'gpt-4o'
        return build_custom_model_from_payload(
            provider_name=entry.get("provider"),
            base_url=base_url,
            api_key=api_key,
            model_name=model,
        )
        
    def requirements(self) -> List[str]:
        return ['BASE_URL (optional)', 'API_KEY (optional)', 'MODEL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        return len(customs) > 0
