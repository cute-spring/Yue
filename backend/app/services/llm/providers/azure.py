import logging
import re
import sys
import time
import types
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.services.config_service import config_service

from ..base import LLMProvider, SimpleProvider
from ..utils import (
    build_client,
    get_cache_ttl,
    get_http_client,
    get_model_cache,
    get_ssl_verify,
    handle_llm_exception,
)

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = "2024-06-01"
AZURE_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
TOKEN_CACHE_KEY = "azure_openai_token"

if "azure.identity" not in sys.modules:
    try:
        import azure.identity  # type: ignore  # noqa: F401
    except Exception:
        azure_pkg = types.ModuleType("azure")
        identity_mod = types.ModuleType("azure.identity")

        class ClientSecretCredential:
            def __init__(self, *args, **kwargs):
                raise ImportError("azure.identity not installed")

        def get_bearer_token_provider(*args, **kwargs):
            raise ImportError("azure.identity not installed")

        identity_mod.ClientSecretCredential = ClientSecretCredential
        identity_mod.get_bearer_token_provider = get_bearer_token_provider
        azure_pkg.identity = identity_mod
        sys.modules.setdefault("azure", azure_pkg)
        sys.modules.setdefault("azure.identity", identity_mod)


async def fetch_azure_deployments(refresh: bool = False) -> List[str]:
    del refresh
    llm_config = config_service.get_llm_config()
    deployment_str = llm_config.get("azure_openai_deployment")
    if not deployment_str:
        return []

    deployments: List[str] = []
    for raw_value in deployment_str.split(","):
        value = raw_value.strip()
        if not value:
            continue
        if "=" in value:
            deployments.append(value.split("=", 1)[0].strip())
        elif ":" in value:
            deployments.append(value.split(":", 1)[0].strip())
        else:
            deployments.append(value)
    return deployments


def _get_azure_bearer_token(llm_config: Dict[str, Any], max_retries: int = 3) -> str:
    now = time.time()
    model_cache = get_model_cache()
    cache = model_cache.get(TOKEN_CACHE_KEY)
    if cache and (now - cache.get("ts", 0) < cache.get("ttl", 0) - 30):
        return cache.get("token", "")

    token_env = llm_config.get("azure_openai_token")
    if token_env:
        model_cache[TOKEN_CACHE_KEY] = {"token": token_env, "ts": now, "ttl": get_cache_ttl()}
        return token_env

    tenant = llm_config.get("azure_tenant_id")
    client_id = llm_config.get("azure_client_id")
    client_secret = llm_config.get("azure_client_secret")
    if not (tenant and client_id and client_secret):
        raise ValueError(
            "Azure credentials missing: tenant/client_id/client_secret are required for AD authentication"
        )

    token_url = AZURE_TOKEN_URL_TEMPLATE.format(tenant=tenant)
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": AZURE_COGNITIVE_SCOPE,
    }
    verify = get_ssl_verify()

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with build_client(timeout=10.0, verify=verify, llm_config=llm_config) as client:
                response = client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                token = token_data.get("access_token")
                if not token:
                    raise ValueError("No access_token found in Azure response")
                ttl = int(token_data.get("expires_in", get_cache_ttl())) - 60
                model_cache[TOKEN_CACHE_KEY] = {"token": token, "ts": now, "ttl": ttl}
                return token
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            logger.warning("Azure token request failed (attempt %d/%d): %s", attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))

    if last_exc:
        raise ValueError(handle_llm_exception(last_exc))
    raise RuntimeError("Failed to fetch Azure AD token for unknown reasons")


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
            raise ValueError("Azure credentials missing for ClientSecretCredential")
        credential = ClientSecretCredential(
            tenant_id=tenant,
            client_id=client_id,
            client_secret=client_secret,
        )
        return get_bearer_token_provider(credential, AZURE_COGNITIVE_SCOPE)
    except Exception:
        return lambda: _get_azure_bearer_token(llm_config)


class AzureOpenAIProviderImpl(SimpleProvider):
    name = LLMProvider.AZURE_OPENAI.value

    def _get_config(self) -> Dict[str, Any]:
        return config_service.get_llm_config()

    def _clean_endpoint(self, base_url: str) -> str:
        if not base_url:
            return ""

        endpoint = base_url.strip().rstrip("/")
        parsed = urlparse(endpoint)
        if not parsed.scheme:
            endpoint = f"https://{endpoint}"
            parsed = urlparse(endpoint)

        path = parsed.path
        if path.lower().endswith("/openai"):
            path = path[:-7]
        elif "/openai/deployments" in path.lower():
            path = re.split(r"/openai/deployments", path, flags=re.IGNORECASE)[0]

        return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")

    async def list_models(self, refresh: bool = False) -> List[str]:
        return await fetch_azure_deployments(refresh=refresh)

    def build(self, model_name: Optional[str] = None) -> Any:
        llm_config = self._get_config()
        base_url = llm_config.get("azure_openai_base_url") or llm_config.get("azure_openai_endpoint")
        deployment_str = llm_config.get("azure_openai_deployment") or ""
        deployments_info = [value.strip() for value in deployment_str.split(",") if value.strip()]

        deployment_info_map: Dict[str, tuple[str, Optional[str]]] = {}
        for value in deployments_info:
            nickname: Optional[str] = None
            real_name: Optional[str] = None
            version: Optional[str] = None

            if "=" in value:
                nickname, remainder = value.split("=", 1)
                nickname = nickname.strip()
                if ":" in remainder:
                    real_name, version = remainder.split(":", 1)
                    real_name = real_name.strip()
                    version = version.strip()
                else:
                    real_name = remainder.strip()
            elif ":" in value:
                real_name, version = value.split(":", 1)
                real_name = real_name.strip()
                version = version.strip()
            else:
                real_name = value.strip()

            display_name = nickname or real_name
            if real_name:
                deployment_info_map[display_name] = (real_name, version)

        display_name = model_name or (next(iter(deployment_info_map.keys())) if deployment_info_map else None)
        if not (base_url and display_name):
            raise ValueError("Azure OpenAI configuration missing: base_url and deployment are required")

        real_deployment, version = deployment_info_map.get(display_name, (display_name, None))
        token_provider = _get_azure_token_provider(llm_config)
        token = token_provider()
        api_version = version or llm_config.get("azure_openai_api_version") or DEFAULT_API_VERSION

        if not re.match(r"^\d{4}-\d{2}-\d{2}(-preview)?$", api_version):
            logger.warning(
                "Azure OpenAI API version '%s' may be invalid. Expected format: YYYY-MM-DD or YYYY-MM-DD-preview",
                api_version,
            )

        endpoint = self._clean_endpoint(base_url)
        token_value = llm_config.get("azure_openai_token")
        has_static_token = token_value not in (None, "")

        try:
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                api_key=token if has_static_token else None,
                azure_ad_token_provider=token_provider if not has_static_token else None,
                http_client=get_http_client(),
                default_query={"api-version": api_version},
            )
        except Exception as exc:
            logger.error("Failed to initialize Azure OpenAI client: %s", exc)
            raise ValueError(handle_llm_exception(exc))

        return OpenAIChatModel(real_deployment, provider=OpenAIProvider(openai_client=azure_client))

    def requirements(self) -> List[str]:
        return [
            "AZURE_OPENAI_BASE_URL (e.g. https://your-resource.openai.azure.com)",
            "AZURE_OPENAI_DEPLOYMENT (supports multiple deployments, nicknames and per-deployment versions)",
            "AZURE_OPENAI_API_VERSION (default version if not specified per deployment)",
            "AZURE_OPENAI_TOKEN (API Key) OR Azure AD Credentials:",
            "- AZURE_TENANT_ID",
            "- AZURE_CLIENT_ID",
            "- AZURE_CLIENT_SECRET",
        ]

    def configured(self) -> bool:
        llm_config = self._get_config()
        base_url = llm_config.get("azure_openai_base_url") or llm_config.get("azure_openai_endpoint")
        deployment_str = llm_config.get("azure_openai_deployment")
        has_token = bool(llm_config.get("azure_openai_token"))
        has_creds = all(
            [
                llm_config.get("azure_tenant_id"),
                llm_config.get("azure_client_id"),
                llm_config.get("azure_client_secret"),
            ]
        )
        if not (base_url and deployment_str and (has_token or has_creds)):
            return False

        deployments_info = [value.strip() for value in deployment_str.split(",") if value.strip()]
        valid_deployments = 0
        for value in deployments_info:
            if "=" in value:
                _, remainder = value.split("=", 1)
                if ":" in remainder:
                    deployment, version = remainder.split(":", 1)
                else:
                    deployment, version = remainder, None
            elif ":" in value:
                deployment, version = value.split(":", 1)
            else:
                deployment, version = value, None

            deployment = deployment.strip()
            if version:
                version = version.strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}(-preview)?$", version):
                    logger.warning(
                        "Azure deployment '%s' has potentially invalid API version '%s'",
                        deployment,
                        version,
                    )

            if not re.match(r"^[a-zA-Z0-9_-]+$", deployment):
                logger.warning(
                    "Azure deployment name '%s' contains unusual characters. Use only letters, numbers, underscores, and hyphens",
                    deployment,
                )
            else:
                valid_deployments += 1

        return valid_deployments > 0
