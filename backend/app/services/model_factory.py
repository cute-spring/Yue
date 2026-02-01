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
import time

class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    ZHIPU = "zhipu"
    CUSTOM = "custom"

_shared_http_client: Optional[httpx.AsyncClient] = None
_model_cache: Dict[str, Dict[str, any]] = {}
_CACHE_TTL = 3600  # seconds

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

async def fetch_openai_models(refresh: bool = False) -> List[str]:
    now = time.time()
    cache = _model_cache.get("openai")
    if cache and not refresh and (now - cache.get("ts", 0) < _CACHE_TTL):
        return cache.get("models", [])
    llm_config = config_service.get_llm_config()
    api_key = llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
    if not api_key:
        return ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code == 200:
                data = r.json().get("data", [])
                names = [m.get("id") for m in data if isinstance(m.get("id"), str)]
                # keep common chat models recognizable
                filtered = [n for n in names if any(n.startswith(p) for p in ("gpt-", "o1", "o3"))]
                _model_cache["openai"] = {"models": filtered or names, "ts": now}
                return _model_cache["openai"]["models"]
    except Exception as e:
        print(f"OpenAI model discovery error: {e}")
    return ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini']

async def fetch_gemini_models(refresh: bool = False) -> List[str]:
    now = time.time()
    cache = _model_cache.get("gemini")
    if cache and not refresh and (now - cache.get("ts", 0) < _CACHE_TTL):
        return cache.get("models", [])
    llm_config = config_service.get_llm_config()
    api_key = llm_config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY')
    base_url = llm_config.get('gemini_base_url') or os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
    if not api_key:
        return ['gemini-1.5-pro', 'gemini-1.5-flash']
    # Normalize endpoint to .../models
    url = base_url.rstrip('/') + '/models'
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(url, params={"key": api_key})
            if r.status_code == 200:
                models = r.json().get("models", [])
                names = [m.get("name") or m.get("id") for m in models if isinstance(m, dict)]
                # Shorten names like "models/gemini-1.5-pro"
                short = [n.split('/')[-1] for n in names if isinstance(n, str)]
                _model_cache["gemini"] = {"models": short or names, "ts": now}
                return _model_cache["gemini"]["models"]
    except Exception as e:
        print(f"Gemini model discovery error: {e}")
    return ['gemini-1.5-pro', 'gemini-1.5-flash']
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

    elif provider == LLMProvider.GEMINI:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY')
        base_url = llm_config.get('gemini_base_url') or os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        # Use OpenAIChatModel surface with base_url override for now; swap when native provider is integrated
        return OpenAIChatModel(
            model_name or llm_config.get('gemini_model') or 'gemini-1.5-pro',
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=_get_http_client()
            )
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

    elif provider == LLMProvider.CUSTOM:
        # Resolve from llm.custom_models by name
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        entry = None
        if model_name:
            entry = next((m for m in customs if m.get("name") == model_name), None)
        if not entry:
            # fallback to env compatibility
            entry = {
                "base_url": os.getenv("LLM_BASE_URL"),
                "api_key": os.getenv("LLM_API_KEY"),
                "model": os.getenv("LLM_MODEL_NAME") or model_name
            }
        base_url = entry.get("base_url")
        api_key = entry.get("api_key")
        model = entry.get("model") or model_name or 'gpt-4o'
        if not api_key:
            raise ValueError("Custom model API key is not set.")
        return OpenAIChatModel(
            model,
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
    return [
        LLMProvider.OPENAI.value,
        LLMProvider.DEEPSEEK.value,
        LLMProvider.GEMINI.value,
        LLMProvider.OLLAMA.value,
        LLMProvider.ZHIPU.value,
        LLMProvider.CUSTOM.value
    ]

async def list_providers(refresh: bool = False) -> List[Dict]:
    providers = []
    llm_config = config_service.get_llm_config()
    
    # Pre-fetch Ollama models
    ollama_models = await fetch_ollama_models()
    # Pre-fetch discovery for OpenAI/Gemini
    openai_models = await fetch_openai_models(refresh=refresh)
    gemini_models = await fetch_gemini_models(refresh=refresh)
    
    for name in list_supported_providers():
        configured = False
        requirements: List[str] = []
        available_models: List[str] = []
        
        if name == LLMProvider.OPENAI.value:
            configured = bool(llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY'))
            requirements = ['OPENAI_API_KEY']
            models = openai_models
        elif name == LLMProvider.DEEPSEEK.value:
            configured = bool(llm_config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY'))
            requirements = ['DEEPSEEK_API_KEY']
            models = ['deepseek-chat', 'deepseek-reasoner']
        elif name == LLMProvider.GEMINI.value:
            configured = bool(llm_config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY'))
            requirements = ['GEMINI_API_KEY', 'GEMINI_BASE_URL (optional)']
            models = gemini_models
        elif name == LLMProvider.ZHIPU.value:
            configured = bool(llm_config.get('zhipu_api_key') or os.getenv('ZHIPU_API_KEY'))
            requirements = ['ZHIPU_API_KEY', 'ZHIPU_BASE_URL (optional)']
            models = ['glm-4v', 'glm-4-plus']
        elif name == LLMProvider.OLLAMA.value:
            configured = len(ollama_models) > 0
            requirements = ['OLLAMA_BASE_URL (optional)']
            models = ollama_models
        elif name == LLMProvider.CUSTOM.value:
            # available custom models from persisted config
            custom_models = llm_config.get("custom_models", []) or []
            configured = len(custom_models) > 0
            requirements = ['BASE_URL (optional)', 'API_KEY', 'MODEL']
            models = [m.get("name") for m in custom_models if m.get("name")]
        
        # Determine enabled models
        # If config is present, use it. Otherwise default to all models.
        config_enabled = llm_config.get(f"{name}_enabled_models")
        if config_enabled is not None and isinstance(config_enabled, list):
            # Filter enabled models to ensure they still exist in the full list (optional, but good practice)
            # Or just trust the config if models might be offline (like ollama)
            # For now, we trust the config but also include any that are in config
            available_models = [m for m in models if m in config_enabled]
            # If the user enabled a model that is not in 'models' (e.g. offline ollama), should we show it?
            # Probably strictly following 'models' (discovered) is safer for availability.
        else:
            available_models = models

        providers.append({
            "name": name,
            "configured": configured,
            "requirements": requirements,
            "available_models": available_models,
            "models": models,
            "current_model": llm_config.get(f"{name}_model")
        })
    return providers
