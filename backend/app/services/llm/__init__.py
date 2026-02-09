from .base import LLMProvider, SimpleProvider, ProviderInfo
from .registry import register_provider, unregister_provider, list_registered_providers
from .factory import get_model, list_supported_providers, list_providers, list_providers_structured
from .providers.ollama import fetch_ollama_models
from .providers import register_all

# Initialize all providers
register_all()

__all__ = [
    "LLMProvider",
    "SimpleProvider",
    "ProviderInfo",
    "register_provider",
    "unregister_provider",
    "list_registered_providers",
    "get_model",
    "list_supported_providers",
    "list_providers",
    "list_providers_structured",
    "fetch_ollama_models",
]
