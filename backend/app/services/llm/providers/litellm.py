from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_async_client, get_ssl_verify
from app.services.config_service import config_service

class LiteLLMProviderImpl(SimpleProvider):
    name = LLMProvider.LITELLM.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get("litellm_base_url")
        api_key = llm_config.get("litellm_api_key")
        if not base_url or not api_key:
            return []
        url = base_url.rstrip("/") + "/v1/models"
        verify = get_ssl_verify()
        try:
            async with build_async_client(timeout=2.0, verify=verify, llm_config=llm_config) as client:
                r = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data") or data.get("models") or []
                    return [m.get("id") or m.get("name") for m in items if isinstance(m, dict)]
        except Exception:
            return []
        return []
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get("litellm_base_url")
        api_key = llm_config.get("litellm_api_key")
        model = model_name or llm_config.get("litellm_model") or "gpt-4o-mini"
        if not (base_url and api_key):
            raise ValueError("LiteLLM base_url or api_key missing")
        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=get_http_client()
            )
        )
        
    def requirements(self) -> List[str]:
        return ['LITELLM_BASE_URL', 'LITELLM_API_KEY', 'LITELLM_MODEL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get("litellm_base_url")
        api_key = llm_config.get("litellm_api_key")
        return bool(base_url and api_key)
