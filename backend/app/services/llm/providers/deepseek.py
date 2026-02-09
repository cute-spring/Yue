from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client
from app.services.config_service import config_service

class DeepSeekProviderImpl(SimpleProvider):
    name = LLMProvider.DEEPSEEK.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return ['deepseek-chat', 'deepseek-reasoner']
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('deepseek_api_key')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('deepseek_model') or 'deepseek-chat',
            provider=DeepSeekProvider(api_key=api_key, http_client=get_http_client()),
        )
        
    def requirements(self) -> List[str]:
        return ['DEEPSEEK_API_KEY']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('deepseek_api_key'))
