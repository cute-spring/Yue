from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client
from app.services.config_service import config_service

class CustomProviderImpl(SimpleProvider):
    name = LLMProvider.CUSTOM.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        return [m.get("name") for m in customs if m.get("name")]
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        entry = None
        if model_name:
            entry = next((m for m in customs if m.get("name") == model_name), None)
        if not entry:
            entry = {
                "base_url": llm_config.get("llm_base_url"),
                "api_key": llm_config.get("llm_api_key"),
                "model": llm_config.get("llm_model_name") or model_name
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
                http_client=get_http_client()
            )
        )
        
    def requirements(self) -> List[str]:
        return ['BASE_URL (optional)', 'API_KEY', 'MODEL']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        return len(customs) > 0
