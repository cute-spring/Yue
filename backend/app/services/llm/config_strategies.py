from typing import Dict, Any, List, Optional
import os

class ProviderConfigStrategy:
    """Provider 配置策略基类"""
    def __init__(self, name: str, env_map: Dict[str, str]):
        self.name = name
        self.env_map = env_map

    def get_config(self, json_config: Dict[str, Any]) -> Dict[str, Any]:
        """从 JSON 和环境变量中获取合并后的配置"""
        provider_config = json_config.get("providers", {}).get(self.name, {}).copy()
        
        # 合并环境变量（环境变量优先级更高）
        for key, env_var in self.env_map.items():
            env_val = os.getenv(env_var)
            if env_val:
                provider_config[key] = env_val
        
        # 如果没有设置 model，使用 default_model
        if "model" not in provider_config and "default_model" in provider_config:
            provider_config["model"] = provider_config["default_model"]
        
        return provider_config

    def mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """对敏感信息进行脱敏"""
        masked = config.copy()
        for key in config:
            if key.endswith("_api_key") or key in ["api_key", "token", "client_secret"]:
                val = config[key]
                if isinstance(val, str) and len(val) > 8:
                    masked[key] = f"{val[:4]}****{val[-4:]}"
                elif val:
                    masked[key] = "****"
        return masked

class OpenAIStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("openai", {
            "api_key": "OPENAI_API_KEY",
            "model": "OPENAI_MODEL"
        })

class ZhipuStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("zhipu", {
            "api_key": "ZHIPU_API_KEY",
            "base_url": "ZHIPU_BASE_URL",
            "model": "ZHIPU_MODEL"
        })

class DeepseekStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("deepseek", {
            "api_key": "DEEPSEEK_API_KEY",
            "model": "DEEPSEEK_MODEL"
        })

class OllamaStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("ollama", {
            "base_url": "OLLAMA_BASE_URL",
            "model": "OLLAMA_MODEL"
        })

class AzureStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("azure_openai", {
            "endpoint": "AZURE_OPENAI_ENDPOINT",
            "base_url": "AZURE_OPENAI_BASE_URL",
            "deployment": "AZURE_OPENAI_DEPLOYMENT",
            "api_version": "AZURE_OPENAI_API_VERSION",
            "token": "AZURE_OPENAI_TOKEN",
            "client_id": "AZURE_CLIENT_ID",
            "client_secret": "AZURE_CLIENT_SECRET",
            "tenant_id": "AZURE_TENANT_ID"
        })

class LiteLLMStrategy(ProviderConfigStrategy):
    def __init__(self):
        super().__init__("litellm", {
            "base_url": "LITELLM_BASE_URL",
            "api_key": "LITELLM_API_KEY",
            "model": "LITELLM_MODEL"
        })

# 策略注册表
STRATEGIES: Dict[str, ProviderConfigStrategy] = {
    "openai": OpenAIStrategy(),
    "zhipu": ZhipuStrategy(),
    "deepseek": DeepseekStrategy(),
    "ollama": OllamaStrategy(),
    "azure_openai": AzureStrategy(),
    "litellm": LiteLLMStrategy()
}
