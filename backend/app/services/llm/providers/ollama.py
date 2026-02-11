import logging
import time
import httpx
from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client, get_model_cache, get_cache_ttl, get_ollama_http_client
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

async def fetch_ollama_models(refresh: bool = False) -> List[str]:
    now = time.time()
    model_cache = get_model_cache()
    cache_ttl = get_cache_ttl()
    cache = model_cache.get("ollama")
    
    if cache and not refresh and (now - cache.get("ts", 0) < cache_ttl):
        return cache.get("models", [])
        
    llm_config = config_service.get_llm_config()
    base_url = llm_config.get('ollama_base_url') or 'http://localhost:11434'
    
    # More robust URL construction
    base_url = base_url.rstrip('/')
    if base_url.endswith('/v1'):
        api_url = base_url[:-3].rstrip('/') + '/api/tags'
    else:
        api_url = base_url + '/api/tags'
    
    ssl_cert_file = llm_config.get('ssl_cert_file')
    verify = ssl_cert_file if ssl_cert_file else True
    try:
        # Use 127.0.0.1 instead of localhost to avoid potential proxy issues
        # and disable trust_env to bypass any system-level proxies for local connections
        api_url = api_url.replace("localhost", "127.0.0.1")
        async with httpx.AsyncClient(timeout=5.0, verify=verify, trust_env=False) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                model_cache["ollama"] = {"models": models, "ts": now}
                return models
    except Exception:
        logger.exception("Ollama model discovery error")
    
    if cache:
        return cache.get("models", [])
    return []

class OllamaProviderImpl(SimpleProvider):
    name = LLMProvider.OLLAMA.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_ollama_models(refresh=refresh)
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base_url = (llm_config.get('ollama_base_url') or 'http://localhost:11434').rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = f"{base_url}/v1"
            
        # Use 127.0.0.1 instead of localhost to avoid potential proxy issues
        base_url = base_url.replace("localhost", "127.0.0.1")
        
        return OpenAIChatModel(
            model_name or llm_config.get('ollama_model') or 'llama3',
            provider=OllamaProvider(base_url=base_url, http_client=get_ollama_http_client()),
        )
        
    def requirements(self) -> List[str]:
        return ['OLLAMA_BASE_URL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get('ollama_base_url')
        return True 
