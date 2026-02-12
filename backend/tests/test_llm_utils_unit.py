import pytest
import httpx
import os
from app.services.llm.utils import (
    get_ssl_verify,
    build_async_client,
    get_model_cache,
    get_cache_ttl,
    handle_llm_exception
)
import tempfile
from unittest.mock import patch, MagicMock

def test_handle_llm_exception_tls():
    e = Exception("SSL: CERTIFICATE_VERIFY_FAILED")
    msg = handle_llm_exception(e)
    assert "TLS/SSL Certificate Verification Failed" in msg
    assert "ssl_cert_file" in msg

def test_handle_llm_exception_proxy():
    e = Exception("ProxyError: All connection attempts failed")
    msg = handle_llm_exception(e)
    assert "Proxy connection failed" in msg
    assert "Proxy URL" in msg

def test_handle_llm_exception_normal():
    e = Exception("Some other error")
    msg = handle_llm_exception(e)
    assert msg == "Some other error"

def test_model_cache_accessors():
    cache = get_model_cache()
    assert isinstance(cache, dict)
    assert get_cache_ttl() == 3600

def test_get_ssl_verify_default(monkeypatch):
    with patch("app.services.llm.utils.config_service") as mock_cfg:
        mock_cfg.get_llm_config.return_value = {}
        assert get_ssl_verify() is True

def test_get_ssl_verify_with_cert(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".pem") as tmp:
        with patch("app.services.llm.utils.config_service") as mock_cfg:
            mock_cfg.get_llm_config.return_value = {"ssl_cert_file": tmp.name}
            # Should return a path to a combined bundle
            verify = get_ssl_verify()
            assert isinstance(verify, str)
            assert os.path.exists(verify)
            assert verify.endswith(".pem")

@pytest.mark.asyncio
async def test_build_async_client_basic():
    llm_config = {}
    with patch("app.services.llm.utils.get_ssl_verify", return_value=True):
        async with build_async_client(timeout=10.0, verify=True, llm_config=llm_config) as client:
            assert isinstance(client, httpx.AsyncClient)
            assert client.timeout.connect == 10.0
            assert client.trust_env is True

@pytest.mark.asyncio
async def test_build_async_client_with_proxy(monkeypatch):
    llm_config = {"proxy_url": "http://proxy:8080", "no_proxy": "local.net"}
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_client.return_value = mock_instance
        
        async with build_async_client(timeout=5.0, verify=False, llm_config=llm_config) as client:
            pass
            
        args, kwargs = mock_client.call_args
        # Should now use trust_env=True and environment variables instead of explicit proxies param
        assert kwargs["trust_env"] is True
        assert "proxies" not in kwargs
        assert "proxy" not in kwargs
        
        # Verify environment variables were set
        assert os.environ.get("HTTP_PROXY") == "http://proxy:8080"
        assert os.environ.get("HTTPS_PROXY") == "http://proxy:8080"
        assert "local.net" in os.environ.get("NO_PROXY", "")
