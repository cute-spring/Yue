import os
import httpx
import asyncio
from enum import Enum
from typing import Optional, List, Dict
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.ollama import OllamaProvider
from app.services.config_service import config_service

class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    OLLAMA = "ollama"
    ZHIPU = "zhipu"
    CUSTOM = "custom"

_shared_http_client: Optional[httpx.AsyncClient] = None

def _get_http_client() -> Optional[httpx.AsyncClient]:
    global _shared_http_client
    proxy_url = os.getenv('LLM_PROXY_URL')
    
    if not proxy_url:
        return None
        
    if _shared_http_client is None:
        _shared_http_client = httpx.AsyncClient(
            proxy=proxy_url,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(60.0)
        )
    return _shared_http_client

async def fetch_ollama_models() -> List[str]:
    """
    Tries to connect to local Ollama and fetch available models.
    """
    llm_config = config_service.get_llm_config()
    base_url = llm_config.get('ollama_base_url') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    # Normalize base_url for API call (remove /v1 if present)
    api_url = base_url.replace('/v1', '') + '/api/tags'
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
    except Exception as e:
        print(f"Ollama not detected or error: {e}")
    return []

def get_model(provider_name: str, model_name: Optional[str] = None):
    """
    Returns a model instance based on provider and model name.
    """
    try:
        provider = LLMProvider(provider_name.lower())
    except ValueError:
        # Fallback to OpenAI if provider is just a model name or unknown
        provider = LLMProvider.OPENAI

    if provider == LLMProvider.DEEPSEEK:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('deepseek_model') or 'deepseek-chat',
            provider=DeepSeekProvider(api_key=api_key, http_client=_get_http_client()),
        )
        
    elif provider == LLMProvider.OPENAI:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('openai_model') or 'gpt-4o', 
            provider=OpenAIProvider(api_key=api_key, http_client=_get_http_client())
        )
        
    elif provider == LLMProvider.OLLAMA:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get('ollama_base_url') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
        return OpenAIChatModel(
            model_name or llm_config.get('ollama_model') or 'llama3',
            provider=OllamaProvider(base_url=base_url, http_client=_get_http_client()),
        )

    elif provider == LLMProvider.ZHIPU:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('zhipu_api_key') or os.getenv('ZHIPU_API_KEY')
        base_url = llm_config.get('zhipu_base_url') or os.getenv('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4/')
        return OpenAIChatModel(
            model_name or llm_config.get('zhipu_model') or 'glm-4v',
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=_get_http_client()
            )
        )

    # Add other providers as needed from lab's models.py...
    
    # Default to OpenAI if nothing matches
    return OpenAIChatModel(
        model_name or 'gpt-4o',
        provider=OpenAIProvider(api_key=os.getenv('OPENAI_API_KEY'), http_client=_get_http_client())
    )

def list_supported_providers() -> List[str]:
    return [LLMProvider.OPENAI.value, LLMProvider.DEEPSEEK.value, LLMProvider.OLLAMA.value, LLMProvider.ZHIPU.value, LLMProvider.CUSTOM.value]

async def list_providers() -> List[Dict]:
    providers = []
    llm_config = config_service.get_llm_config()
    
    # Pre-fetch Ollama models
    ollama_models = await fetch_ollama_models()
    
    for name in list_supported_providers():
        configured = False
        requirements: List[str] = []
        available_models: List[str] = []
        
        if name == LLMProvider.OPENAI.value:
            configured = bool(llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY'))
            requirements = ['OPENAI_API_KEY']
            available_models = ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']
        elif name == LLMProvider.DEEPSEEK.value:
            configured = bool(llm_config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY'))
            requirements = ['DEEPSEEK_API_KEY']
            available_models = ['deepseek-chat', 'deepseek-reasoner']
        elif name == LLMProvider.ZHIPU.value:
            configured = bool(llm_config.get('zhipu_api_key') or os.getenv('ZHIPU_API_KEY'))
            requirements = ['ZHIPU_API_KEY', 'ZHIPU_BASE_URL (optional)']
            available_models = ['glm-4v', 'glm-4-plus']
        elif name == LLMProvider.OLLAMA.value:
            configured = len(ollama_models) > 0
            requirements = ['OLLAMA_BASE_URL (optional)']
            available_models = ollama_models
        elif name == LLMProvider.CUSTOM.value:
            configured = all([os.getenv('LLM_BASE_URL'), os.getenv('LLM_API_KEY'), os.getenv('LLM_MODEL_NAME')])
            requirements = ['LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL_NAME']
        
        providers.append({
            "name": name,
            "configured": configured,
            "requirements": requirements,
            "available_models": available_models,
            "current_model": llm_config.get(f"{name}_model")
        })
    return providers
