import pytest
import httpx
import os
from app.services.llm.utils import (
    _get_proxies_config, 
    _build_no_proxy_value, 
    build_async_client,
    get_model_cache,
    get_cache_ttl
)

def test_model_cache_accessors():
    cache = get_model_cache()
    assert isinstance(cache, dict)
    assert get_cache_ttl() == 3600

def test_get_proxies_config_empty():
    assert _get_proxies_config({}) is None

def test_get_proxies_config_with_url():
    config = {"proxy_url": "http://proxy:8080"}
    proxies = _get_proxies_config(config)
    assert proxies["all://"] == "http://proxy:8080"
    assert proxies["all://localhost"] is None
    assert proxies["all://127.0.0.1"] is None

def test_get_proxies_config_with_no_proxy():
    config = {
        "proxy_url": "http://proxy:8080",
        "no_proxy": "example.com, api.test.org"
    }
    proxies = _get_proxies_config(config)
    assert proxies["all://example.com"] is None
    assert proxies["all://api.test.org"] is None

def test_build_no_proxy_value():
    assert "localhost" in _build_no_proxy_value(None)
    assert "custom.com" in _build_no_proxy_value("custom.com")
    assert "localhost" in _build_no_proxy_value("custom.com")

@pytest.mark.asyncio
async def test_build_async_client_basic():
    llm_config = {}
    async with build_async_client(timeout=10.0, verify=True, llm_config=llm_config) as client:
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.connect == 10.0

@pytest.mark.asyncio
async def test_build_async_client_with_proxy(monkeypatch):
    from unittest.mock import patch, MagicMock
    llm_config = {"proxy_url": "http://proxy:8080", "no_proxy": "local.net"}
    
    with patch("httpx.AsyncClient") as mock_client, \
         patch("app.services.llm.utils._client_supports_param", return_value=True):
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_client.return_value = mock_instance
        
        async with build_async_client(timeout=5.0, verify=False, llm_config=llm_config) as client:
            pass
            
        # Check if either 'proxies' or 'proxy' was passed to AsyncClient
        args, kwargs = mock_client.call_args
        assert "proxies" in kwargs or "proxy" in kwargs
        if "proxies" in kwargs:
            assert kwargs["proxies"]["all://"] == "http://proxy:8080"
        else:
            assert kwargs["proxy"] == "http://proxy:8080"
