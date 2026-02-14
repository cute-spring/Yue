import os
import httpx
import logging
import inspect
import time
import tempfile
import certifi
from typing import Optional, Dict, Any, List, Union
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

_shared_http_client: Optional[httpx.AsyncClient] = None
_shared_ollama_client: Optional[httpx.AsyncClient] = None
_model_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 3600  # seconds
_CA_BUNDLE_PATH: Optional[str] = None
_CA_BUNDLE_MTIME: float = 0
_CA_BUNDLE_SIZE: int = 0

def get_ssl_verify() -> Union[bool, str]:
    """
    Get the SSL verification configuration.
    Returns a combined CA bundle (certifi + corporate PEM) if ssl_cert_file is configured.
    """
    global _CA_BUNDLE_PATH, _CA_BUNDLE_MTIME, _CA_BUNDLE_SIZE
    llm_config = config_service.get_llm_config()
    ssl_cert_file = llm_config.get('ssl_cert_file')
    
    if not ssl_cert_file:
        return True
        
    if not os.path.exists(ssl_cert_file):
        logger.warning(f"SSL_CERT_FILE not found: {ssl_cert_file}. Falling back to default CA bundle.")
        return True

    # Check if we have a valid cached bundle and the source file hasn't changed
    try:
        stat = os.stat(ssl_cert_file)
        if (_CA_BUNDLE_PATH and os.path.exists(_CA_BUNDLE_PATH) and 
            stat.st_mtime == _CA_BUNDLE_MTIME and stat.st_size == _CA_BUNDLE_SIZE):
            return _CA_BUNDLE_PATH
        
        # Update cache metadata
        _CA_BUNDLE_MTIME = stat.st_mtime
        _CA_BUNDLE_SIZE = stat.st_size
    except Exception as e:
        logger.debug(f"Failed to stat SSL_CERT_FILE: {e}")

    try:
        # Create a combined CA bundle
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tmp:
            # Add certifi bundle
            with open(certifi.where(), 'r') as f:
                tmp.write(f.read())
            tmp.write("\n")
            # Add corporate bundle
            with open(ssl_cert_file, 'r') as f:
                tmp.write(f.read())
            
            # If we had a previous temp file, try to remove it
            if _CA_BUNDLE_PATH and os.path.exists(_CA_BUNDLE_PATH):
                try:
                    os.unlink(_CA_BUNDLE_PATH)
                except Exception:
                    pass
                    
            _CA_BUNDLE_PATH = tmp.name
            logger.info(f"Created combined CA bundle at {_CA_BUNDLE_PATH}")
            return _CA_BUNDLE_PATH
    except Exception as e:
        logger.error(f"Failed to create combined CA bundle: {e}")
        return ssl_cert_file

def get_model_cache() -> Dict[str, Dict[str, Any]]:
    return _model_cache

def get_cache_ttl() -> int:
    return _CACHE_TTL

def get_ollama_http_client() -> httpx.AsyncClient:
    global _shared_ollama_client
    if _shared_ollama_client is None:
        llm_config = config_service.get_llm_config()
        verify = get_ssl_verify()
        timeout_val = float(llm_config.get('llm_request_timeout', 60))
        
        kwargs: Dict[str, Any] = {
            "timeout": timeout_val,
            "verify": verify,
            "trust_env": False  # Bypass system proxies for local Ollama
        }
        
        # Try to enable HTTP/2 if h2 is installed
        try:
            import h2
            kwargs["http2"] = True
        except ImportError:
            pass

        _shared_ollama_client = httpx.AsyncClient(**kwargs)
    return _shared_ollama_client

def _get_proxies_config(llm_config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Deprecated: Prefer using _apply_proxy_env and trust_env=True.
    """
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

def _build_no_proxy_value(no_proxy: Optional[str], llm_config: Dict[str, Any]) -> str:
    # Use ::1 instead of [::1] for NO_PROXY normalization
    default_no_proxy = "localhost,127.0.0.1,::1,0.0.0.0"
    hosts = [h.strip() for h in default_no_proxy.split(',')]
    
    # Infer hostname from Azure OpenAI base URL
    azure_url = llm_config.get("azure_openai_base_url") or llm_config.get("azure_openai_endpoint")
    if azure_url:
        try:
            from urllib.parse import urlparse
            netloc = urlparse(azure_url).netloc
            if netloc:
                # Remove port if present
                hostname = netloc.split(':')[0]
                if hostname not in hosts:
                    hosts.append(hostname)
        except Exception:
            pass

    if no_proxy:
        # Filter out empty strings and strip spaces
        additional = [h.strip() for h in no_proxy.split(',') if h.strip()]
        for h in additional:
            # Normalize [::1] to ::1 if user provided it
            if h == "[::1]":
                h = "::1"
            if h not in hosts:
                hosts.append(h)
                
    return ",".join(hosts)

def _apply_proxy_env(llm_config: Dict[str, Any]) -> None:
    proxy_url = llm_config.get("proxy_url")
    no_proxy = llm_config.get("no_proxy")
    if proxy_url:
        # Set both uppercase and lowercase variants
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            os.environ[key] = proxy_url
            
        no_proxy_val = _build_no_proxy_value(no_proxy, llm_config)
        os.environ["NO_PROXY"] = no_proxy_val
        os.environ["no_proxy"] = no_proxy_val
    else:
        # Clear them if not configured to avoid side effects
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"]:
            os.environ.pop(key, None)

def build_async_client(
    *,
    timeout: float,
    verify: Any,
    llm_config: Dict[str, Any],
    limits: Optional[httpx.Limits] = None,
) -> httpx.AsyncClient:
    _apply_proxy_env(llm_config)
    kwargs: Dict[str, Any] = {
        "timeout": timeout, 
        "verify": verify,
        "trust_env": True
    }
    if limits is not None:
        kwargs["limits"] = limits
    
    # Try to enable HTTP/2 if h2 is installed
    try:
        import h2
        kwargs["http2"] = True
    except ImportError:
        pass
    
    return httpx.AsyncClient(**kwargs)

def build_client(
    *,
    timeout: float,
    verify: Any,
    llm_config: Dict[str, Any],
) -> httpx.Client:
    _apply_proxy_env(llm_config)
    kwargs: Dict[str, Any] = {
        "timeout": timeout, 
        "verify": verify,
        "trust_env": True
    }
    
    # Try to enable HTTP/2 if h2 is installed
    try:
        import h2
        kwargs["http2"] = True
    except ImportError:
        pass
        
    return httpx.Client(**kwargs)

def get_http_client() -> Optional[httpx.AsyncClient]:
    global _shared_http_client
    llm_config = config_service.get_llm_config()
    proxy_url = llm_config.get('proxy_url')
    ssl_cert_file = llm_config.get('ssl_cert_file')
    
    if not proxy_url and not ssl_cert_file:
        return None
        
    if _shared_http_client is None:
        verify = get_ssl_verify()
        timeout_val = float(llm_config.get('llm_request_timeout', 60))

        _shared_http_client = build_async_client(
            timeout=timeout_val,
            verify=verify,
            llm_config=llm_config,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=10, keepalive_expiry=10.0),
        )
    return _shared_http_client

def handle_llm_exception(e: Exception) -> str:
    """
    Translates common LLM exceptions into user-friendly error messages,
    specifically focusing on TLS/SSL verification failures.
    """
    error_str = str(e)
    
    # Check for TLS/SSL errors in the exception message or underlying causes
    is_tls_error = False
    tls_keywords = ["SSL: CERTIFICATE_VERIFY_FAILED", "certificate verify failed", "SSLCertVerificationError"]
    
    if any(kw in error_str for kw in tls_keywords):
        is_tls_error = True
    
    # Also check cause chain if possible
    curr_e = e
    while curr_e and not is_tls_error:
        if any(kw in str(curr_e) for kw in tls_keywords):
            is_tls_error = True
            break
        curr_e = getattr(curr_e, "__cause__", None) or getattr(curr_e, "__context__", None)

    if is_tls_error:
        return (
            "TLS/SSL Certificate Verification Failed. This usually happens when you are behind a corporate proxy "
            "that intercepts HTTPS traffic. Please ensure you have configured 'SSL Certificate File' (ssl_cert_file) "
            "in your LLM settings with the path to your corporate CA bundle (PEM format)."
        )
    
    # Check for proxy errors
    if "ProxyError" in error_str or ("All connection attempts failed" in error_str and "proxy" in error_str.lower()):
         return (
            f"Proxy connection failed. Please check your 'Proxy URL' and 'No Proxy' settings. "
            f"Original error: {error_str}"
        )

    # Check for RemoteProtocolError (Incomplete Chunked Read)
    if "RemoteProtocolError" in error_str and "incomplete chunked read" in error_str:
        return (
            "Network connection was closed prematurely by the server (Incomplete Chunked Read). "
            "This often happens due to network instability or proxy timeouts. Please try again."
        )

    return error_str

