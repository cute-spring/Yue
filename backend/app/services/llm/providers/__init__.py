from ..registry import register_provider
from .openai import OpenAIProviderImpl
from .deepseek import DeepSeekProviderImpl
from .ollama import OllamaProviderImpl
from .gemini import GeminiProviderImpl
from .zhipu import ZhipuProviderImpl
from .custom import CustomProviderImpl
from .azure import AzureOpenAIProviderImpl
from .litellm import LiteLLMProviderImpl

def register_all():
    register_provider(OpenAIProviderImpl())
    register_provider(DeepSeekProviderImpl())
    register_provider(OllamaProviderImpl())
    register_provider(GeminiProviderImpl())
    register_provider(ZhipuProviderImpl())
    register_provider(CustomProviderImpl())
    register_provider(AzureOpenAIProviderImpl())
    register_provider(LiteLLMProviderImpl())
