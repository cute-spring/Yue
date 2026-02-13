from typing import Optional, List, Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client
from app.services.config_service import config_service

class ZhipuProviderImpl(SimpleProvider):
    name = LLMProvider.ZHIPU.value
    
    async def list_models(self, refresh: bool = False) -> List[str]:
        return ['glm-4.6v']
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('zhipu_api_key')
        base_url = llm_config.get('zhipu_base_url') or 'https://open.bigmodel.cn/api/paas/v4/'
        return OpenAIChatModel(
            model_name or llm_config.get('zhipu_model') or 'glm-4.6v',
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=get_http_client()
            )
        )
        
    def requirements(self) -> List[str]:
        return ['ZHIPU_API_KEY', 'ZHIPU_BASE_URL (optional)']
        
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('zhipu_api_key'))
