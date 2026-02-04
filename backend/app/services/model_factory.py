import os
import httpx
import asyncio
import json
from enum import Enum
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.function import FunctionModel, DeltaToolCall
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
    AZURE_OPENAI = "azure_openai"
    LITELLM = "litellm"

_shared_http_client: Optional[httpx.AsyncClient] = None
_model_cache: Dict[str, Dict[str, any]] = {}
_CACHE_TTL = 3600  # seconds

class SimpleProvider(ABC):
    """
    轻量 Provider 接口：用于以编程方式扩展新的 LLM。
    - name: 注册名（小写唯一）
    - build: 根据可选的 model_name 返回具体可用的模型实例
    - list_models: 异步返回当前可用的模型列表（可选支持 refresh）
    - requirements/configured: 用于展示与管理端判断可用性
    """
    name: str

    @abstractmethod
    def build(self, model_name: Optional[str] = None) -> Any:
        """返回一个可用的模型实例；model_name 为空时应返回默认模型"""
        pass

    @abstractmethod
    async def list_models(self, refresh: bool = False) -> List[str]:
        """返回可用的模型名称列表；出错时建议返回空列表"""
        pass

    def requirements(self) -> List[str]:
        """返回该 Provider 所需的环境或配置说明（如 API_KEY）"""
        return []

    def configured(self) -> bool:
        """是否已配置完成，可用于 UI 显示和过滤"""
        return True

_dynamic_providers: Dict[str, SimpleProvider] = {}
"""运行时注册的 Provider 存储表；键为 provider.name 的小写"""

def register_provider(provider: SimpleProvider) -> None:
    """注册一个新的 Provider；重复名称会覆盖旧的实现"""
    _dynamic_providers[provider.name.lower()] = provider

def unregister_provider(name: str) -> None:
    """卸载指定名称的 Provider"""
    _dynamic_providers.pop(name.lower(), None)

def list_registered_providers() -> List[str]:
    """列出当前已注册的 Provider 名称（小写）"""
    return list(_dynamic_providers.keys())

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
class OpenAIProviderImpl(SimpleProvider):
    name = LLMProvider.OPENAI.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_openai_models(refresh=refresh)
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('openai_model') or 'gpt-4o',
            provider=OpenAIProvider(api_key=api_key, http_client=_get_http_client())
        )
    def requirements(self) -> List[str]:
        return ['OPENAI_API_KEY']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('openai_api_key') or os.getenv('OPENAI_API_KEY'))

class DeepSeekProviderImpl(SimpleProvider):
    name = LLMProvider.DEEPSEEK.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        return ['deepseek-chat', 'deepseek-reasoner']
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('deepseek_model') or 'deepseek-chat',
            provider=DeepSeekProvider(api_key=api_key, http_client=_get_http_client()),
        )
    def requirements(self) -> List[str]:
        return ['DEEPSEEK_API_KEY']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY'))

class OllamaProviderImpl(SimpleProvider):
    name = LLMProvider.OLLAMA.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_ollama_models()
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get('ollama_base_url') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
        return OpenAIChatModel(
            model_name or llm_config.get('ollama_model') or 'llama3',
            provider=OllamaProvider(base_url=base_url, http_client=_get_http_client()),
        )
    def requirements(self) -> List[str]:
        return ['OLLAMA_BASE_URL (optional)']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get('ollama_base_url') or os.getenv('OLLAMA_BASE_URL')
        return bool(base_url)

class GeminiProviderImpl(SimpleProvider):
    name = LLMProvider.GEMINI.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_gemini_models(refresh=refresh)
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        api_key = llm_config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY')
        base_url = llm_config.get('gemini_base_url') or os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        return OpenAIChatModel(
            model_name or llm_config.get('gemini_model') or 'gemini-1.5-pro',
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=_get_http_client()
            )
        )
    def requirements(self) -> List[str]:
        return ['GEMINI_API_KEY', 'GEMINI_BASE_URL (optional)']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY'))

class ZhipuProviderImpl(SimpleProvider):
    name = LLMProvider.ZHIPU.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        return ['glm-4v', 'glm-4-plus']
    def build(self, model_name: Optional[str] = None) -> Any:
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
    def requirements(self) -> List[str]:
        return ['ZHIPU_API_KEY', 'ZHIPU_BASE_URL (optional)']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        return bool(llm_config.get('zhipu_api_key') or os.getenv('ZHIPU_API_KEY'))

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
    def requirements(self) -> List[str]:
        return ['BASE_URL (optional)', 'API_KEY', 'MODEL']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        customs = llm_config.get("custom_models", []) or []
        return len(customs) > 0

def _get_azure_bearer_token(llm_config: Dict[str, Any]) -> str:
    now = time.time()
    cache = _model_cache.get("azure_openai_token")
    if cache and (now - cache.get("ts", 0) < cache.get("ttl", 0)):
        return cache.get("token", "")
    token_env = os.getenv("AZURE_OPENAI_TOKEN") or llm_config.get("azure_openai_token")
    if token_env:
        _model_cache["azure_openai_token"] = {"token": token_env, "ts": now, "ttl": 3000}
        return token_env
    tenant = llm_config.get("azure_tenant_id") or os.getenv("AZURE_TENANT_ID")
    client_id = llm_config.get("azure_client_id") or os.getenv("AZURE_CLIENT_ID")
    client_secret = llm_config.get("azure_client_secret") or os.getenv("AZURE_CLIENT_SECRET")
    if not (tenant and client_id and client_secret):
        raise ValueError("Azure credentials missing: tenant/client_id/client_secret")
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://cognitiveservices.azure.com/.default",
    }
    with httpx.Client(timeout=5.0) as client:
        r = client.post(token_url, data=data)
        r.raise_for_status()
        j = r.json()
        token = j.get("access_token")
        ttl = int(j.get("expires_in", 3600)) - 60
        _model_cache["azure_openai_token"] = {"token": token, "ts": now, "ttl": ttl}
        return token or ""

def _get_azure_token_provider(llm_config: Dict[str, Any]):
    token_env = os.getenv("AZURE_OPENAI_TOKEN") or llm_config.get("azure_openai_token")
    if token_env:
        return lambda: token_env
    try:
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        tenant = llm_config.get("azure_tenant_id") or os.getenv("AZURE_TENANT_ID")
        client_id = llm_config.get("azure_client_id") or os.getenv("AZURE_CLIENT_ID")
        client_secret = llm_config.get("azure_client_secret") or os.getenv("AZURE_CLIENT_SECRET")
        if not (tenant and client_id and client_secret):
            raise ValueError("Azure credentials missing: tenant/client_id/client_secret")
        cred = ClientSecretCredential(tenant_id=tenant, client_id=client_id, client_secret=client_secret)
        return get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
    except Exception:
        return lambda: _get_azure_bearer_token(llm_config)

class AzureOpenAIProviderImpl(SimpleProvider):
    name = LLMProvider.AZURE_OPENAI.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        llm_config = config_service.get_llm_config()
        dep = llm_config.get("azure_openai_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if dep:
            return [dep]
        return []
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base = llm_config.get("azure_openai_base_url") or os.getenv("AZURE_OPENAI_BASE_URL")
        deployment = model_name or llm_config.get("azure_openai_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not (base and deployment):
            raise ValueError("Azure OpenAI base_url or deployment missing")
        token_provider = _get_azure_token_provider(llm_config)
        token = token_provider()
        api_version = llm_config.get("azure_openai_api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
        base_url = base.rstrip("/") + f"/openai/deployments/{deployment}?api-version={api_version}"
        return OpenAIChatModel(
            deployment,
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=token,
                http_client=_get_http_client()
            )
        )
    def requirements(self) -> List[str]:
        return [
            'AZURE_OPENAI_BASE_URL',
            'AZURE_OPENAI_DEPLOYMENT',
            'AZURE_OPENAI_API_VERSION (optional)',
            'AZURE_TENANT_ID',
            'AZURE_CLIENT_ID',
            'AZURE_CLIENT_SECRET or AZURE_OPENAI_TOKEN'
        ]
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base = llm_config.get("azure_openai_base_url") or os.getenv("AZURE_OPENAI_BASE_URL")
        dep = llm_config.get("azure_openai_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        has_token = os.getenv("AZURE_OPENAI_TOKEN") or llm_config.get("azure_openai_token")
        has_creds = (llm_config.get("azure_tenant_id") or os.getenv("AZURE_TENANT_ID")) and \
                    (llm_config.get("azure_client_id") or os.getenv("AZURE_CLIENT_ID")) and \
                    (llm_config.get("azure_client_secret") or os.getenv("AZURE_CLIENT_SECRET"))
        return bool(base and dep and (has_token or has_creds))

register_provider(OpenAIProviderImpl())
register_provider(DeepSeekProviderImpl())
register_provider(OllamaProviderImpl())
register_provider(GeminiProviderImpl())
register_provider(ZhipuProviderImpl())
register_provider(CustomProviderImpl())
register_provider(AzureOpenAIProviderImpl())
class LiteLLMProviderImpl(SimpleProvider):
    name = LLMProvider.LITELLM.value
    async def list_models(self, refresh: bool = False) -> List[str]:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get("litellm_base_url") or os.getenv("LITELLM_BASE_URL")
        api_key = llm_config.get("litellm_api_key") or os.getenv("LITELLM_API_KEY")
        if not base_url or not api_key:
            return []
        url = base_url.rstrip("/") + "/v1/models"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
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
        base_url = llm_config.get("litellm_base_url") or os.getenv("LITELLM_BASE_URL")
        api_key = llm_config.get("litellm_api_key") or os.getenv("LITELLM_API_KEY")
        model = model_name or llm_config.get("litellm_model") or os.getenv("LITELLM_MODEL") or "gpt-4o-mini"
        if not (base_url and api_key):
            raise ValueError("LiteLLM base_url or api_key missing")
        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
                http_client=_get_http_client()
            )
        )
    def requirements(self) -> List[str]:
        return ['LITELLM_BASE_URL', 'LITELLM_API_KEY', 'LITELLM_MODEL (optional)']
    def configured(self) -> bool:
        llm_config = config_service.get_llm_config()
        base_url = llm_config.get("litellm_base_url") or os.getenv("LITELLM_BASE_URL")
        api_key = llm_config.get("litellm_api_key") or os.getenv("LITELLM_API_KEY")
        return bool(base_url and api_key)
register_provider(LiteLLMProviderImpl())

class _InternalGuardProvider(SimpleProvider):
    name = "__guard__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            instructions = agent_info.instructions or ""
            marker = "Enclose your thinking process within <thought>...</thought> tags"
            if marker in instructions:
                yield "<thought>guard_detected_forced_thought_injection</thought>"
                return
            yield "O"
            yield "K"

        return FunctionModel(stream_function=stream_function, model_name=model_name or "guard")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["guard"]

    def configured(self) -> bool:
        return True

register_provider(_InternalGuardProvider())

class _InternalToolCallProvider(SimpleProvider):
    name = "__toolcall__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) in ("tool-return", "builtin-tool-return"):
                        yield "OK"
                        return

            payload = {
                "tasks": [
                    {
                        "id": "subtask-1",
                        "title": "Deterministic subtask",
                        "prompt": "ping",
                        "provider": "__guard__",
                        "model": "guard",
                    }
                ]
            }
            yield {
                0: DeltaToolCall(
                    name="task_tool",
                    json_args=json.dumps(payload, ensure_ascii=False),
                    tool_call_id="toolcall-1",
                )
            }

        return FunctionModel(stream_function=stream_function, model_name=model_name or "toolcall")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["toolcall"]

    def configured(self) -> bool:
        return True

register_provider(_InternalToolCallProvider())

class _InternalSlowProvider(SimpleProvider):
    name = "__slow__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            yield "S"
            await asyncio.sleep(60)
            yield "LOW"

        return FunctionModel(stream_function=stream_function, model_name=model_name or "slow")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["slow"]

    def configured(self) -> bool:
        return True

register_provider(_InternalSlowProvider())

class _InternalEchoProvider(SimpleProvider):
    name = "__echo__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            last_user_prompt: Optional[str] = None
            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) == "user-prompt" and isinstance(getattr(p, "content", None), str):
                        last_user_prompt = p.content
            yield f"ECHO:{(last_user_prompt or '').strip()}"

        return FunctionModel(stream_function=stream_function, model_name=model_name or "echo")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["echo"]

    def configured(self) -> bool:
        return True

register_provider(_InternalEchoProvider())

class _InternalDocRetrieverProvider(SimpleProvider):
    name = "__docretriever__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            tool_returns: dict[str, str] = {}
            last_user_prompt: Optional[str] = None

            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) == "user-prompt" and isinstance(getattr(p, "content", None), str):
                        last_user_prompt = p.content
                    if getattr(p, "part_kind", None) in ("tool-return", "builtin-tool-return"):
                        tool_name = getattr(p, "tool_name", None)
                        content = getattr(p, "content", None)
                        if isinstance(tool_name, str) and isinstance(content, str):
                            tool_returns[tool_name] = content

            if "docs_read_markdown" in tool_returns:
                text = tool_returns["docs_read_markdown"]
                lines = text.splitlines()
                header = lines[0] if lines else ""
                snippet = "\n".join(lines[1:]).strip()
                path = header.split("#", 1)[0] if header else ""
                locator = header.split("#", 1)[1] if "#" in header else ""
                payload = {
                    "status": "ok",
                    "citations": [
                        {
                            "path": path,
                            "locator": locator,
                            "snippet": snippet,
                        }
                    ],
                }
                yield json.dumps(payload, ensure_ascii=False)
                return

            if "docs_search_markdown" in tool_returns:
                yield {
                    0: DeltaToolCall(
                        name="docs_read_markdown",
                        json_args=json.dumps({"path": "alpha.md", "start_line": 1, "max_lines": 50}, ensure_ascii=False),
                        tool_call_id="docread-1",
                    )
                }
                return

            query = (last_user_prompt or "").strip() or "Obsidian"
            yield {
                0: DeltaToolCall(
                    name="docs_search_markdown",
                    json_args=json.dumps({"query": query, "limit": 1}, ensure_ascii=False),
                    tool_call_id="docsearch-1",
                )
            }

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docretriever")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docretriever"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocRetrieverProvider())

class _InternalDocRetrieverNoHitProvider(SimpleProvider):
    name = "__docretriever_nohit__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            yield json.dumps({"status": "no_hit", "citations": []}, ensure_ascii=False)

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docretriever_nohit")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docretriever_nohit"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocRetrieverNoHitProvider())

class _InternalDocRetrieverDeniedProvider(SimpleProvider):
    name = "__docretriever_denied__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            yield json.dumps({"status": "denied", "citations": [], "reason": "forbidden"}, ensure_ascii=False)

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docretriever_denied")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docretriever_denied"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocRetrieverDeniedProvider())

class _InternalDocMainProvider(SimpleProvider):
    name = "__docmain__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            last_user_prompt: Optional[str] = None
            tool_return_content: Optional[str] = None

            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) == "user-prompt" and isinstance(getattr(p, "content", None), str):
                        last_user_prompt = p.content
                    if getattr(p, "part_kind", None) in ("tool-return", "builtin-tool-return") and getattr(p, "tool_name", None) == "task_tool":
                        if isinstance(getattr(p, "content", None), str):
                            tool_return_content = p.content

            if tool_return_content is not None:
                try:
                    payload = json.loads(tool_return_content)
                    tasks = payload.get("tasks") if isinstance(payload, dict) else None
                    first = tasks[0] if isinstance(tasks, list) and tasks else None
                    citations = first.get("citations") if isinstance(first, dict) else None
                    if isinstance(citations, list) and citations:
                        path = citations[0].get("path") if isinstance(citations[0], dict) else None
                        if isinstance(path, str) and path:
                            yield f"已找到文档依据。\n\n引用：\n- {path}"
                        else:
                            yield "已找到文档依据。"
                    else:
                        yield "未在已配置的文档范围内找到可引用的依据。请尝试：调整关键词、缩小/扩大范围、或提供更具体的文件/段落线索。"
                except Exception:
                    yield "未在已配置的文档范围内找到可引用的依据。请尝试：调整关键词、缩小/扩大范围、或提供更具体的文件/段落线索。"
                return

            payload = {
                "tasks": [
                    {
                        "id": "doc-task-1",
                        "title": "Doc retrieval",
                        "prompt": (last_user_prompt or "").strip() or "Obsidian",
                        "agent_id": "builtin-doc-retriever",
                        "provider": "__docretriever__",
                        "model": "docretriever",
                    }
                ]
            }
            yield {
                0: DeltaToolCall(
                    name="task_tool",
                    json_args=json.dumps(payload, ensure_ascii=False),
                    tool_call_id="docmain-1",
                )
            }

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docmain")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docmain"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocMainProvider())

class _InternalDocHallucinateProvider(SimpleProvider):
    name = "__dochallucinate__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            yield "这是一个没有引用的结论性回答，用于测试强制引用策略。"
        return FunctionModel(stream_function=stream_function, model_name=model_name or "dochallucinate")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["dochallucinate"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocHallucinateProvider())

class _InternalDocMainNoHitProvider(SimpleProvider):
    name = "__docmain_nohit__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            last_user_prompt: Optional[str] = None
            tool_return_content: Optional[str] = None

            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) == "user-prompt" and isinstance(getattr(p, "content", None), str):
                        last_user_prompt = p.content
                    if getattr(p, "part_kind", None) in ("tool-return", "builtin-tool-return") and getattr(p, "tool_name", None) == "task_tool":
                        if isinstance(getattr(p, "content", None), str):
                            tool_return_content = p.content

            if tool_return_content is not None:
                try:
                    payload = json.loads(tool_return_content)
                    tasks = payload.get("tasks") if isinstance(payload, dict) else None
                    first = tasks[0] if isinstance(tasks, list) and tasks else None
                    citations = first.get("citations") if isinstance(first, dict) else None
                    if isinstance(citations, list) and citations:
                        yield "已找到文档依据。"
                    else:
                        yield "未在已配置的文档范围内找到可引用的依据。请尝试：调整关键词、缩小/扩大范围、或提供更具体的文件/段落线索。"
                except Exception:
                    yield "未在已配置的文档范围内找到可引用的依据。请尝试：调整关键词、缩小/扩大范围、或提供更具体的文件/段落线索。"
                return

            payload = {
                "tasks": [
                    {
                        "id": "doc-task-nohit-1",
                        "title": "Doc retrieval nohit",
                        "prompt": (last_user_prompt or "").strip() or "Obsidian",
                        "agent_id": "builtin-doc-retriever",
                        "provider": "__docretriever_nohit__",
                        "model": "docretriever_nohit",
                    }
                ]
            }
            yield {
                0: DeltaToolCall(
                    name="task_tool",
                    json_args=json.dumps(payload, ensure_ascii=False),
                    tool_call_id="docmain-nohit-1",
                )
            }

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docmain_nohit")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docmain_nohit"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocMainNoHitProvider())

class _InternalDocMainDeniedProvider(SimpleProvider):
    name = "__docmain_denied__"

    def build(self, model_name: Optional[str] = None) -> Any:
        async def stream_function(messages, agent_info):
            last_user_prompt: Optional[str] = None
            tool_return_content: Optional[str] = None

            for m in messages:
                if getattr(m, "kind", None) != "request":
                    continue
                for p in getattr(m, "parts", []) or []:
                    if getattr(p, "part_kind", None) == "user-prompt" and isinstance(getattr(p, "content", None), str):
                        last_user_prompt = p.content
                    if getattr(p, "part_kind", None) in ("tool-return", "builtin-tool-return") and getattr(p, "tool_name", None) == "task_tool":
                        if isinstance(getattr(p, "content", None), str):
                            tool_return_content = p.content

            if tool_return_content is not None:
                yield "文档访问被拒绝：当前权限/配置不允许读取目标文档。请检查 doc_root 与 allowlist/denylist 配置。"
                return

            payload = {
                "tasks": [
                    {
                        "id": "doc-task-denied-1",
                        "title": "Doc retrieval denied",
                        "prompt": (last_user_prompt or "").strip() or "Obsidian",
                        "agent_id": "builtin-doc-retriever",
                        "provider": "__docretriever_denied__",
                        "model": "docretriever_denied",
                    }
                ]
            }
            yield {
                0: DeltaToolCall(
                    name="task_tool",
                    json_args=json.dumps(payload, ensure_ascii=False),
                    tool_call_id="docmain-denied-1",
                )
            }

        return FunctionModel(stream_function=stream_function, model_name=model_name or "docmain_denied")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return ["docmain_denied"]

    def configured(self) -> bool:
        return True

register_provider(_InternalDocMainDeniedProvider())

def get_model(provider_name: str, model_name: Optional[str] = None):
    handler = _dynamic_providers.get(provider_name.lower()) or _dynamic_providers.get(LLMProvider.OPENAI.value)
    return handler.build(model_name)

def list_supported_providers() -> List[str]:
    return [p for p in list_registered_providers() if not p.startswith("__")]

async def list_providers(refresh: bool = False) -> List[Dict]:
    providers = []
    llm_config = config_service.get_llm_config()
    
    for name, handler in _dynamic_providers.items():
        if name.startswith("__"):
            continue
        try:
            models = await handler.list_models(refresh=refresh)
        except Exception:
            models = []
        config_enabled = llm_config.get(f"{name}_enabled_models")
        available_models = [m for m in models if isinstance(config_enabled, list) and m in config_enabled] if isinstance(config_enabled, list) else models
        providers.append({
            "name": name,
            "configured": handler.configured(),
            "requirements": handler.requirements(),
            "available_models": available_models,
            "models": models,
            "current_model": llm_config.get(f"{name}_model")
        })
    return providers

class ProviderInfo(BaseModel):
    name: str
    configured: bool
    requirements: List[str]
    available_models: List[str]
    models: List[str]
    current_model: Optional[str] = None

async def list_providers_structured(refresh: bool = False) -> List[ProviderInfo]:
    raw = await list_providers(refresh=refresh)
    return [ProviderInfo.model_validate(p) for p in raw]
