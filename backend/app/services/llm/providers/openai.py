import time
import logging
from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client, get_model_cache, get_cache_ttl
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

async def fetch_openai_models(refresh: bool = False) -> List[str]:
    now = time.time()
    model_cache = get_model_cache()
    cache_ttl = get_cache_ttl()
    cache = model_cache.get("openai")
    
    if cache and not refresh and (now - cache.get("ts", 0) < cache_ttl):
        return cache.get("models", [])
        
    llm_config = config_service.get_llm_config()
    api_key = llm_config.get('openai_api_key')
    if not api_key:
        return ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']
        
    ssl_cert_file = llm_config.get('ssl_cert_file')
    verify = ssl_cert_file if ssl_cert_file else True
    try:
        async with build_async_client(timeout=2.5, verify=verify, llm_config=llm_config) as client:
            r = await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code == 200:
                data = r.json().get("data", [])
                names = [m.get("id") for m in data if isinstance(m.get("id"), str)]
                filtered = [n for n in names if any(n.startswith(p) for p in ("gpt-", "o1", "o3"))]
                model_cache["openai"] = {"models": filtered or names, "ts": now}
                return model_cache["openai"]["models"]
    except Exception:
        logger.exception("OpenAI model discovery error")
    return ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']

class OpenAIProviderImpl(SimpleProvider):
    name = LLMProvider.OPENAI.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_openai_models(refresh=refresh)
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('openai_api_key')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('openai_model') or 'gpt-4o',
            provider=OpenAIProvider(api_key=api_key, http_client=get_http_client())
        )
        
    def requirements(self) -> List[str]:
        return ['OPENAI_API_KEY']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('openai_api_key'))
