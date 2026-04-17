from ..registry import register_provider
from .openai import OpenAIProviderImpl
from .deepseek import DeepSeekProviderImpl
from .ollama import OllamaProviderImpl
from .gemini import GeminiProviderImpl
from .custom import CustomProviderImpl
from .litellm import LiteLLMProviderImpl

def register_all():
    register_provider(OpenAIProviderImpl())
    register_provider(DeepSeekProviderImpl())
    register_provider(OllamaProviderImpl())
    register_provider(GeminiProviderImpl())
    register_provider(CustomProviderImpl())
    register_provider(LiteLLMProviderImpl())
