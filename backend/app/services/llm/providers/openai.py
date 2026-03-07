import time
import logging
from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client, get_model_cache, get_cache_ttl, get_ssl_verify, handle_llm_exception
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

def _normalize_openai_base_url(base_url: Optional[str]) -> str:
    cleaned = (base_url or "").strip()
    if not cleaned:
        return "https://api.openai.com/v1"
    return cleaned.rstrip("/")

def _is_official_openai(base_url: str) -> bool:
    return "api.openai.com" in base_url

async def fetch_openai_models(refresh: bool = False) -> List[str]:
    now = time.time()
    model_cache = get_model_cache()
    cache_ttl = get_cache_ttl()
    llm_config = config_service.get_llm_config()
    base_url = _normalize_openai_base_url(llm_config.get('openai_base_url'))
    cache_key = f"openai::{base_url}"
    cache = model_cache.get(cache_key)
    
    if cache and not refresh and (now - cache.get("ts", 0) < cache_ttl):
        return cache.get("models", [])
        
    api_key = llm_config.get('openai_api_key')
    is_openrouter = "openrouter.ai" in base_url
    fallback_models = (
        ['stepfun/step-3.5-flash'] if is_openrouter
        else ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']
    )
    if not api_key:
        return fallback_models
        
    verify = get_ssl_verify()
    try:
        async with build_async_client(timeout=2.5, verify=verify, llm_config=llm_config) as client:
            r = await client.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code == 200:
                data = r.json().get("data", [])
                names = [m.get("id") for m in data if isinstance(m.get("id"), str)]
                if _is_official_openai(base_url):
                    resolved = [n for n in names if any(n.startswith(p) for p in ("gpt-", "o1", "o3"))] or names
                else:
                    resolved = names
                model_cache[cache_key] = {"models": resolved, "ts": now}
                return model_cache[cache_key]["models"]
    except Exception as e:
        logger.warning(f"OpenAI model discovery error: {handle_llm_exception(e)}")
    return fallback_models

class OpenAIProviderImpl(SimpleProvider):
    name = LLMProvider.OPENAI.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_openai_models(refresh=refresh)
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('openai_api_key')
        base_url = _normalize_openai_base_url(llm_config.get('openai_base_url'))
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        provider_kwargs = {"api_key": api_key, "http_client": get_http_client()}
        if base_url:
            provider_kwargs["base_url"] = base_url
        return OpenAIChatModel(
            model_name or llm_config.get('openai_model') or 'gpt-4o',
            provider=OpenAIProvider(**provider_kwargs)
        )
        
    def requirements(self) -> List[str]:
        return ['OPENAI_API_KEY', 'OPENAI_BASE_URL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('openai_api_key')
        return bool(api_key and not api_key.startswith("your_api_key"))
