import time
import logging
from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client, get_model_cache, get_cache_ttl, get_ssl_verify, handle_llm_exception
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

async def fetch_gemini_models(refresh: bool = False) -> List[str]:
    now = time.time()
    model_cache = get_model_cache()
    cache_ttl = get_cache_ttl()
    cache = model_cache.get("gemini")
    
    if cache and not refresh and (now - cache.get("ts", 0) < cache_ttl):
        return cache.get("models", [])
        
    llm_config = config_service.get_llm_config()
    api_key = llm_config.get('gemini_api_key')
    base_url = llm_config.get('gemini_base_url') or 'https://generativelanguage.googleapis.com/v1beta'
    if not api_key:
        return ['gemini-1.5-pro', 'gemini-1.5-flash']
        
    url = base_url.rstrip('/') + '/models'
    verify = get_ssl_verify()
    try:
        async with build_async_client(timeout=2.5, verify=verify, llm_config=llm_config) as client:
            r = await client.get(url, params={"key": api_key})
            if r.status_code == 200:
                models = r.json().get("models", [])
                names = [m.get("name") or m.get("id") for m in models if isinstance(m, dict)]
                short = [n.split('/')[-1] for n in names if isinstance(n, str)]
                model_cache["gemini"] = {"models": short or names, "ts": now}
                return model_cache["gemini"]["models"]
    except Exception as e:
        logger.warning(f"Gemini model discovery error: {handle_llm_exception(e)}")
    return ['gemini-1.5-pro', 'gemini-1.5-flash']

class GeminiProviderImpl(SimpleProvider):
    name = LLMProvider.GEMINI.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_gemini_models(refresh=refresh)
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('gemini_api_key')
        base_url = llm_config.get('gemini_base_url') or 'https://generativelanguage.googleapis.com/v1beta'
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('gemini_model') or 'gemini-1.5-pro',
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=get_http_client()
            )
        )
        
    def requirements(self) -> List[str]:
        return ['GEMINI_API_KEY', 'GEMINI_BASE_URL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('gemini_api_key'))
