import time
import logging
import httpx
import re
from typing import Optional, List, Any, Dict
from urllib.parse import urlparse
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncAzureOpenAI
from ..base import SimpleProvider, LLMProvider
from ..utils import get_http_client, build_client, get_model_cache, get_cache_ttl
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

# Constants for Azure OpenAI
DEFAULT_API_VERSION = "2024-06-01"
AZURE_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
TOKEN_CACHE_KEY = "azure_openai_token"
DEFAULT_TOKEN_TTL = 3600

async def fetch_azure_deployments(refresh: bool = False) -> List[str]:
    """
    Return the configured Azure OpenAI deployment(s).
    Supports multiple deployments via comma-separated string in AZURE_OPENAI_DEPLOYMENT.
    Can also specify version per deployment using 'name:version' format.
    """
    llm_config = config_service.get_llm_config()
    deployment_str = llm_config.get("azure_openai_deployment")
    if not deployment_str:
        return []
    
    # Split by comma and clean up whitespace
    deployments = []
    for d in deployment_str.split(","):
        d = d.strip()
        if not d:
            continue
        # If format is name:version, only return the name for the list
        if ":" in d:
            deployments.append(d.split(":")[0].strip())
        else:
            deployments.append(d)
    return deployments

def _get_azure_bearer_token(llm_config: Dict[str, Any], max_retries: int = 3) -> str:
    """
    Fetch an Azure AD bearer token for Cognitive Services with retries.
    Uses caching to avoid redundant network calls.
    
    Args:
        llm_config: Dictionary containing Azure configuration (tenant_id, client_id, etc.)
        max_retries: Maximum number of retries for the token request.
        
    Returns:
        The bearer token string.
        
    Raises:
        ValueError: If required credentials are missing.
        httpx.HTTPStatusError: If the token request fails after retries.
    """
    now = time.time()
    model_cache = get_model_cache()
    cache = model_cache.get(TOKEN_CACHE_KEY)
    
    # Return cached token if still valid (with 30s buffer)
    if cache and (now - cache.get("ts", 0) < cache.get("ttl", 0) - 30):
        return cache.get("token", "")
        
    # Check if a static token is provided in config (as a fallback/override)
    token_env = llm_config.get("azure_openai_token")
    if token_env:
        # Cache the static token for a reasonable time
        model_cache[TOKEN_CACHE_KEY] = {"token": token_env, "ts": now, "ttl": 3600}
        return token_env
        
    tenant = llm_config.get("azure_tenant_id")
    client_id = llm_config.get("azure_client_id")
    client_secret = llm_config.get("azure_client_secret")
    
    if not (tenant and client_id and client_secret):
        raise ValueError("Azure credentials missing: tenant/client_id/client_secret are required for AD authentication")
        
    token_url = AZURE_TOKEN_URL_TEMPLATE.format(tenant=tenant)
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": AZURE_COGNITIVE_SCOPE,
    }
    
    ssl_cert_file = llm_config.get("ssl_cert_file")
    verify = ssl_cert_file if ssl_cert_file else True
    
    last_exc = None
    for attempt in range(max_retries):
        try:
            with build_client(timeout=10.0, verify=verify, llm_config=llm_config) as client:
                response = client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                token = token_data.get("access_token")
                if not token:
                    raise ValueError("No access_token found in Azure response")
                    
                # Subtract 60s buffer from TTL
                ttl = int(token_data.get("expires_in", DEFAULT_TOKEN_TTL)) - 60
                
                model_cache[TOKEN_CACHE_KEY] = {"token": token, "ts": now, "ttl": ttl}
                logger.debug("Successfully fetched Azure AD token (attempt %d)", attempt + 1)
                return token
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            logger.warning("Azure token request failed (attempt %d/%d): %s", attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))  # Simple exponential backoff
            continue
            
    if isinstance(last_exc, httpx.HTTPStatusError):
        logger.error("Azure token request failed: status=%s url=%s", last_exc.response.status_code, last_exc.request.url)
    
    # Raise the last exception caught during attempts
    if last_exc:
        raise last_exc
    raise RuntimeError("Failed to fetch Azure AD token for unknown reasons")

def _get_azure_token_provider(llm_config: Dict[str, Any]):
    """
    Get a token provider function for Azure OpenAI.
    Prioritizes azure-identity SDK if available and no proxy/SSL issues.
    
    Args:
        llm_config: Configuration dictionary.
        
    Returns:
        A callable that returns a token string.
    """
    token_env = llm_config.get("azure_openai_token")
    if token_env:
        return lambda: token_env
        
    # If proxy or custom SSL is needed, use our custom bearer token fetcher which supports them
    if llm_config.get("proxy_url") or llm_config.get("ssl_cert_file"):
        return lambda: _get_azure_bearer_token(llm_config)
        
    try:
        # Attempt to use official Azure Identity SDK for token management
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        
        tenant = llm_config.get("azure_tenant_id")
        client_id = llm_config.get("azure_client_id")
        client_secret = llm_config.get("azure_client_secret")
        
        if not (tenant and client_id and client_secret):
            raise ValueError("Azure credentials missing for ClientSecretCredential")
            
        credential = ClientSecretCredential(tenant_id=tenant, client_id=client_id, client_secret=client_secret)
        return get_bearer_token_provider(credential, AZURE_COGNITIVE_SCOPE)
    except (ImportError, ValueError, Exception):
        # Fallback to custom implementation if SDK fails or is missing
        return lambda: _get_azure_bearer_token(llm_config)

class AzureOpenAIProviderImpl(SimpleProvider):
    """
    Implementation of Azure OpenAI provider for the LLM service.
    Handles model listing, client building, and configuration validation.
    """
    name = LLMProvider.AZURE_OPENAI.value
    
    def _get_config(self) -> Dict[str, Any]:
        """Helper to get LLM configuration."""
        return config_service.get_llm_config()
    
    def _clean_endpoint(self, base_url: str) -> str:
        """
        Clean the base URL to be compatible with AsyncAzureOpenAI.
        Ensures it's just the base endpoint like https://resource.openai.azure.com
        """
        if not base_url:
            return ""
            
        endpoint = base_url.strip().rstrip("/")
        
        # Parse URL to handle various formats
        parsed = urlparse(endpoint)
        if not parsed.scheme:
            # Assume https if no scheme provided
            endpoint = f"https://{endpoint}"
            parsed = urlparse(endpoint)
            
        # Remove common suffixes that users might include by mistake
        path = parsed.path
        if path.lower().endswith("/openai"):
            path = path[:-7]
        elif "/openai/deployments" in path.lower():
            path = re.split(r'/openai/deployments', path, flags=re.IGNORECASE)[0]
            
        # Reconstruct the endpoint
        endpoint = f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")
        return endpoint

    async def list_models(self, refresh: bool = False) -> List[str]:
        """
        List available Azure OpenAI models (deployments).
        """
        return await fetch_azure_deployments(refresh=refresh)
        
    def build(self, model_name: Optional[str] = None) -> Any:
        """
        Build and return an OpenAIChatModel instance configured for Azure.
        
        Args:
            model_name: Optional deployment name to override configuration.
            
        Returns:
            An instance of OpenAIChatModel.
        """
        llm_config = self._get_config()
        base_url = llm_config.get("azure_openai_base_url") or llm_config.get("azure_openai_endpoint")
        
        # Get all configured deployments and their optional versions
        deployment_str = llm_config.get("azure_openai_deployment") or ""
        deployments_info = [d.strip() for d in deployment_str.split(",") if d.strip()]
        
        # Parse deployments into a mapping of name -> version
        deployment_map = {}
        for d in deployments_info:
            if ":" in d:
                name, version = d.split(":", 1)
                deployment_map[name.strip()] = version.strip()
            else:
                deployment_map[d.strip()] = None
        
        # Use provided model_name or default to the first configured deployment
        deployment = model_name or (list(deployment_map.keys())[0] if deployment_map else None)
        
        if not (base_url and deployment):
            raise ValueError("Azure OpenAI configuration missing: base_url and deployment are required")
            
        token_provider = _get_azure_token_provider(llm_config)
        # Fetch initial token to verify connectivity and configuration
        token = token_provider()
        
        # Determine API version: 1. deployment-specific, 2. global config, 3. default
        api_version = deployment_map.get(deployment) or llm_config.get("azure_openai_api_version") or DEFAULT_API_VERSION
        
        # Validate API version format
        if not re.match(r'^\d{4}-\d{2}-\d{2}(-preview)?$', api_version):
            logger.warning(
                "Azure OpenAI API version '%s' may be invalid. Expected format: YYYY-MM-DD or YYYY-MM-DD-preview",
                api_version
            )
        
        endpoint = self._clean_endpoint(base_url)
        
        # Determine authentication method
        token_value = llm_config.get("azure_openai_token")
        has_static_token = token_value not in (None, "")
        
        try:
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                api_key=token if has_static_token else None,
                azure_ad_token_provider=token_provider if not has_static_token else None,
                http_client=get_http_client()
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "azure_endpoint" in error_msg or "url" in error_msg:
                raise ValueError(f"Invalid Azure endpoint '{endpoint}'. Expected format: https://<resource-name>.openai.azure.com")
            elif "api_key" in error_msg and "azure_ad_token_provider" in error_msg:
                raise ValueError("Azure OpenAI configuration error: Must provide either azure_openai_token or Azure AD credentials")
            else:
                logger.error("Failed to initialize Azure OpenAI client: %s", e)
                raise
        
        return OpenAIChatModel(
            deployment,
            provider=OpenAIProvider(
                openai_client=azure_client
            )
        )
        
    def requirements(self) -> List[str]:
        """List required configuration keys for this provider."""
        return [
            'AZURE_OPENAI_BASE_URL (e.g. https://your-resource.openai.azure.com)',
            'AZURE_OPENAI_DEPLOYMENT (Support multiple deployments and per-deployment versions, e.g. gpt-4o:2024-06-01,o1-preview:2024-09-01-preview)',
            'AZURE_OPENAI_API_VERSION (Default version if not specified per deployment, e.g. 2024-06-01)',
            'AZURE_OPENAI_TOKEN (API Key) OR Azure AD Credentials:',
            '- AZURE_TENANT_ID',
            '- AZURE_CLIENT_ID',
            '- AZURE_CLIENT_SECRET'
        ]
        
    def configured(self) -> bool:
        """Check if the provider is sufficiently configured."""
        llm_config = self._get_config()
        base_url = llm_config.get("azure_openai_base_url") or llm_config.get("azure_openai_endpoint")
        deployment_str = llm_config.get("azure_openai_deployment")
        has_token = bool(llm_config.get("azure_openai_token"))
        has_creds = all([
            llm_config.get("azure_tenant_id"),
            llm_config.get("azure_client_id"),
            llm_config.get("azure_client_secret")
        ])
        
        # Base requirements
        if not (base_url and deployment_str and (has_token or has_creds)):
            return False
            
        # Validate configuration and log warnings for common issues
        if not base_url.startswith("https://"):
            logger.warning("Azure OpenAI base_url should use HTTPS for security")
        if not (".openai.azure.com" in base_url or "localhost" in base_url):
            logger.warning("Azure OpenAI base_url '%s' may not be a valid Azure OpenAI endpoint", base_url)
        
        # Validate deployments and versions
        deployments_info = [d.strip() for d in deployment_str.split(",") if d.strip()]
        valid_deployments = 0
        for d in deployments_info:
            if ":" in d:
                deployment, version = d.split(":", 1)
                deployment = deployment.strip()
                version = version.strip()
                if not re.match(r'^\d{4}-\d{2}-\d{2}(-preview)?$', version):
                    logger.warning("Azure deployment '%s' has potentially invalid API version '%s'", deployment, version)
            else:
                deployment = d.strip()
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', deployment):
                logger.warning(
                    "Azure deployment name '%s' contains unusual characters. Use only letters, numbers, underscores, and hyphens",
                    deployment
                )
            else:
                valid_deployments += 1
        
        return valid_deployments > 0
