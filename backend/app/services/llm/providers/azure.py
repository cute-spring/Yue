import time
import logging
import httpx
from typing import Optional, List, Any, Dict
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_client, get_model_cache
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

def _get_azure_bearer_token(llm_config: Dict[str, Any]) -> str:
    now = time.time()
    model_cache = get_model_cache()
    cache = model_cache.get("azure_openai_token")
    if cache and (now - cache.get("ts", 0) < cache.get("ttl", 0)):
        return cache.get("token", "")
    token_env = llm_config.get("azure_openai_token")
    if token_env:
        model_cache["azure_openai_token"] = {"token": token_env, "ts": now, "ttl": 3000}
        return token_env
    tenant = llm_config.get("azure_tenant_id")
    client_id = llm_config.get("azure_client_id")
    client_secret = llm_config.get("azure_client_secret")
    if not (tenant and client_id and client_secret):
        raise ValueError("Azure credentials missing: tenant/client_id/client_secret")
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://cognitiveservices.azure.com/.default",
    }
    ssl_cert_file = llm_config.get("ssl_cert_file")
    verify = ssl_cert_file if ssl_cert_file else True
    try:
        with build_client(timeout=5.0, verify=verify, llm_config=llm_config) as client:
            r = client.post(token_url, data=data)
            r.raise_for_status()
            j = r.json()
            token = j.get("access_token")
            ttl = int(j.get("expires_in", 3600)) - 60
            model_cache["azure_openai_token"] = {"token": token, "ts": now, "ttl": ttl}
            return token or ""
    except httpx.HTTPStatusError as exc:
        logger.error("Azure token request failed: status=%s url=%s", exc.response.status_code, exc.request.url)
        raise
    except Exception:
        logger.exception("Azure token request error")
        raise

def _get_azure_token_provider(llm_config: Dict[str, Any]):
    token_env = llm_config.get("azure_openai_token")
    if token_env:
        return lambda: token_env
    if llm_config.get("proxy_url") or llm_config.get("ssl_cert_file"):
        return lambda: _get_azure_bearer_token(llm_config)
    try:
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        tenant = llm_config.get("azure_tenant_id")
        client_id = llm_config.get("azure_client_id")
        client_secret = llm_config.get("azure_client_secret")
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
        dep = llm_config.get("azure_openai_deployment")
        if dep:
            return [dep]
        return []
        
    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = config_service.get_llm_config()
        base = llm_config.get("azure_openai_base_url")
        deployment = model_name or llm_config.get("azure_openai_deployment")
        if not (base and deployment):
            raise ValueError("Azure OpenAI base_url or deployment missing")
        token_provider = _get_azure_token_provider(llm_config)
        token = token_provider()
        api_version = llm_config.get("azure_openai_api_version") or "2024-02-15-preview"
        base_url = base.rstrip("/") + f"/openai/deployments/{deployment}?api-version={api_version}"
        return OpenAIChatModel(
            deployment,
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=token,
                http_client=get_http_client()
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
        base = llm_config.get("azure_openai_base_url")
        dep = llm_config.get("azure_openai_deployment")
        has_token = llm_config.get("azure_openai_token")
        has_creds = (llm_config.get("azure_tenant_id")) and \
                    (llm_config.get("azure_client_id")) and \
                    (llm_config.get("azure_client_secret"))
        return bool(base and dep and (has_token or has_creds))
