import os
import httpx
import logging
import inspect
import time
from typing import Optional, Dict, Any, List
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

_shared_http_client: Optional[httpx.AsyncClient] = None
_shared_ollama_client: Optional[httpx.AsyncClient] = None
_model_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 3600  # seconds

def get_model_cache() -> Dict[str, Dict[str, Any]]:
    return _model_cache

def get_cache_ttl() -> int:
    return _CACHE_TTL

def get_ollama_http_client() -> httpx.AsyncClient:
    global _shared_ollama_client
    if _shared_ollama_client is None:
        llm_config = config_service.get_llm_config()
        ssl_cert_file = llm_config.get('ssl_cert_file')
        verify = ssl_cert_file if ssl_cert_file else True
        timeout_val = float(llm_config.get('llm_request_timeout', 60))
        
        _shared_ollama_client = httpx.AsyncClient(
            timeout=timeout_val,
            verify=verify,
            trust_env=False  # Bypass system proxies for local Ollama
        )
    return _shared_ollama_client

def _get_proxies_config(llm_config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    proxy_url = llm_config.get('proxy_url')
    no_proxy = llm_config.get('no_proxy')
    
    if not proxy_url:
        return None
    
    proxies = {"all://": proxy_url}
    common_no_proxy = ["localhost", "127.0.0.1", "[::1]", "0.0.0.0"]
    for host in common_no_proxy:
        proxies[f"all://{host}"] = None
    
    if no_proxy:
        for host in no_proxy.split(','):
            host = host.strip()
            if host:
                proxies[f"all://{host}"] = None
                
    return proxies

def _client_supports_param(client_cls: Any, param: str) -> bool:
    try:
        return param in inspect.signature(client_cls.__init__).parameters
    except Exception:
        return False

def _build_no_proxy_value(no_proxy: Optional[str]) -> str:
    default_no_proxy = "localhost,127.0.0.1,[::1],0.0.0.0"
    if no_proxy:
        return f"{default_no_proxy},{no_proxy}"
    return default_no_proxy

def _apply_proxy_env(proxy_url: str, no_proxy: Optional[str]) -> None:
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["NO_PROXY"] = _build_no_proxy_value(no_proxy)

def build_async_client(
    *,
    timeout: float,
    verify: Any,
    llm_config: Dict[str, Any],
    limits: Optional[httpx.Limits] = None,
) -> httpx.AsyncClient:
    proxies = _get_proxies_config(llm_config)
    kwargs: Dict[str, Any] = {"timeout": timeout, "verify": verify}
    if limits is not None:
        kwargs["limits"] = limits
    if proxies and _client_supports_param(httpx.AsyncClient, "proxies"):
        kwargs["proxies"] = proxies
        return httpx.AsyncClient(**kwargs)
    proxy_url = llm_config.get("proxy_url")
    no_proxy = llm_config.get("no_proxy")
    if proxy_url:
        _apply_proxy_env(proxy_url, no_proxy)
        if _client_supports_param(httpx.AsyncClient, "proxy"):
            kwargs["proxy"] = proxy_url
    kwargs["trust_env"] = True
    return httpx.AsyncClient(**kwargs)

def build_client(
    *,
    timeout: float,
    verify: Any,
    llm_config: Dict[str, Any],
) -> httpx.Client:
    proxies = _get_proxies_config(llm_config)
    kwargs: Dict[str, Any] = {"timeout": timeout, "verify": verify}
    if proxies and _client_supports_param(httpx.Client, "proxies"):
        kwargs["proxies"] = proxies
        return httpx.Client(**kwargs)
    proxy_url = llm_config.get("proxy_url")
    no_proxy = llm_config.get("no_proxy")
    if proxy_url:
        _apply_proxy_env(proxy_url, no_proxy)
        if _client_supports_param(httpx.Client, "proxy"):
            kwargs["proxy"] = proxy_url
    kwargs["trust_env"] = True
    return httpx.Client(**kwargs)

def get_http_client() -> Optional[httpx.AsyncClient]:
    global _shared_http_client
    llm_config = config_service.get_llm_config()
    proxy_url = llm_config.get('proxy_url')
    ssl_cert_file = llm_config.get('ssl_cert_file')
    
    if not proxy_url and not ssl_cert_file:
        return None
        
    if _shared_http_client is None:
        verify = ssl_cert_file if ssl_cert_file else True
        timeout_val = float(llm_config.get('llm_request_timeout', 60))

        _shared_http_client = build_async_client(
            timeout=timeout_val,
            verify=verify,
            llm_config=llm_config,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _shared_http_client
