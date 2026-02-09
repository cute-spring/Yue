import logging
from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

async def fetch_ollama_models() -> List[str]:
    llm_config = config_service.get_llm_config()
    base_url = llm_config.get('ollama_base_url') or 'http://localhost:11434'
    api_url = base_url.replace('/v1', '') + '/api/tags'
    
    ssl_cert_file = llm_config.get('ssl_cert_file')
    verify = ssl_cert_file if ssl_cert_file else True
    try:
        async with build_async_client(timeout=2.0, verify=verify, llm_config=llm_config) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
    except Exception:
        logger.exception("Ollama model discovery error")
    return []

class OllamaProviderImpl(SimpleProvider):
    name = LLMProvider.OLLAMA.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_ollama_models()
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base_url = (llm_config.get('ollama_base_url') or 'http://localhost:11434').rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = f"{base_url}/v1"
        return OpenAIChatModel(
            model_name or llm_config.get('ollama_model') or 'llama3',
            provider=OllamaProvider(base_url=base_url, http_client=get_http_client()),
        )
        
    def requirements(self) -> List[str]:
        return ['OLLAMA_BASE_URL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get('ollama_base_url')
        return True 
