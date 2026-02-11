import pytest
import httpx
import time
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm.providers.openai import OpenAIProviderImpl, fetch_openai_models
from app.services.llm.providers.azure import AzureOpenAIProviderImpl, _get_azure_bearer_token
from app.services.llm.providers.ollama import OllamaProviderImpl, fetch_ollama_models
from app.services.llm.providers.gemini import GeminiProviderImpl
from app.services.llm.providers.litellm import LiteLLMProviderImpl
from app.services.llm.providers.custom import CustomProviderImpl
from app.services.llm.providers.zhipu import ZhipuProviderImpl
from app.services.llm.providers.deepseek import DeepSeekProviderImpl

@pytest.fixture
def mock_config():
    with patch("app.services.llm.providers.openai.config_service") as mock_openai_cfg, \
         patch("app.services.llm.providers.azure.config_service") as mock_azure_cfg, \
         patch("app.services.llm.providers.ollama.config_service") as mock_ollama_cfg, \
         patch("app.services.llm.providers.gemini.config_service") as mock_gemini_cfg, \
         patch("app.services.llm.providers.litellm.config_service") as mock_litellm_cfg, \
         patch("app.services.llm.providers.custom.config_service") as mock_custom_cfg, \
         patch("app.services.llm.providers.zhipu.config_service") as mock_zhipu_cfg, \
         patch("app.services.llm.providers.deepseek.config_service") as mock_deepseek_cfg:
        
        mock_openai_cfg.get_llm_config.return_value = {"openai_api_key": "sk-test"}
        mock_azure_cfg.get_llm_config.return_value = {
            "azure_openai_base_url": "https://test.openai.azure.com/",
            "azure_openai_deployment": "gpt-4",
            "azure_openai_token": "token"
        }
        mock_ollama_cfg.get_llm_config.return_value = {"ollama_base_url": "http://localhost:11434"}
        mock_gemini_cfg.get_llm_config.return_value = {"gemini_api_key": "test"}
        mock_litellm_cfg.get_llm_config.return_value = {"litellm_api_key": "test", "litellm_base_url": "http://test"}
        mock_custom_cfg.get_llm_config.return_value = {"custom_llm_configs": []}
        mock_zhipu_cfg.get_llm_config.return_value = {"zhipu_api_key": "test"}
        mock_deepseek_cfg.get_llm_config.return_value = {"deepseek_api_key": "test"}
        
        yield

@pytest.mark.asyncio
async def test_openai_provider(mock_config):
    provider = OpenAIProviderImpl()
    assert provider.configured()
    assert "gpt-4o" in await provider.list_models()
    
    # Test build
    model = provider.build("gpt-4o")
    assert model.model_name == "gpt-4o"

@pytest.mark.asyncio
async def test_fetch_openai_models_success(mock_config):
    with patch("app.services.llm.providers.openai.build_async_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "text-davinci"}]}
        
        async_client = AsyncMock()
        async_client.get.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = async_client
        
        models = await fetch_openai_models(refresh=True)
        assert "gpt-4o" in models
        assert "text-davinci" not in models # Filtered by prefix

@pytest.mark.asyncio
async def test_azure_provider(mock_config):
    provider = AzureOpenAIProviderImpl()
    models = await provider.list_models()
    assert "gpt-4" in models
    
    # Test list_models without deployment
    with patch("app.services.llm.providers.azure.config_service") as mock_cfg:
        mock_cfg.get_llm_config.return_value = {}
        assert await provider.list_models() == []
    
    model = provider.build("gpt-4")
    assert model.model_name == "gpt-4"
    assert provider.configured()
    assert "AZURE_TENANT_ID" in provider.requirements()
    
    # Test build error
    with patch("app.services.llm.providers.azure.config_service") as mock_cfg:
        mock_cfg.get_llm_config.return_value = {}
        with pytest.raises(ValueError, match="Azure OpenAI base_url or deployment missing"):
            provider.build()

@pytest.mark.asyncio
async def test_azure_token_fetch(mock_config):
    # Clear cache before test
    from app.services.llm.utils import get_model_cache
    get_model_cache().clear()
    
    with patch("app.services.llm.providers.azure.build_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "new-token", "expires_in": 3600}
        
        client = MagicMock()
        client.post.return_value = mock_resp
        mock_client.return_value.__enter__.return_value = client
        
        llm_cfg = {
            "azure_tenant_id": "tenant",
            "azure_client_id": "client",
            "azure_client_secret": "secret"
        }
        token = _get_azure_bearer_token(llm_cfg)
        assert token == "new-token"

@pytest.mark.asyncio
async def test_azure_token_provider(mock_config):
    from app.services.llm.providers.azure import _get_azure_token_provider
    
    # Test with token
    llm_cfg = {"azure_openai_token": "env-token"}
    provider = _get_azure_token_provider(llm_cfg)
    assert provider() == "env-token"
    
    # Test with proxy/ssl
    llm_cfg = {"proxy_url": "http://proxy"}
    with patch("app.services.llm.providers.azure._get_azure_bearer_token") as mock_fetch:
        mock_fetch.return_value = "fetched-token"
        provider = _get_azure_token_provider(llm_cfg)
        assert provider() == "fetched-token"
    
    # Test with azure.identity (mocking import)
    llm_cfg = {
        "azure_tenant_id": "t",
        "azure_client_id": "c",
        "azure_client_secret": "s"
    }
    with patch("azure.identity.ClientSecretCredential") as mock_cred, \
         patch("azure.identity.get_bearer_token_provider") as mock_get_p:
        mock_get_p.return_value = lambda: "identity-token"
        provider = _get_azure_token_provider(llm_cfg)
        assert provider() == "identity-token"
        
    # Test azure.identity error fallback
    with patch("azure.identity.ClientSecretCredential", side_effect=Exception("Import error")):
        with patch("app.services.llm.providers.azure._get_azure_bearer_token") as mock_fetch:
            mock_fetch.return_value = "fallback-token"
            provider = _get_azure_token_provider(llm_cfg)
            assert provider() == "fallback-token"

@pytest.mark.asyncio
async def test_azure_token_fetch_error(mock_config):
    # Clear cache before test
    from app.services.llm.utils import get_model_cache
    get_model_cache().clear()
    
    with patch("app.services.llm.providers.azure.build_client") as mock_client:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", 
            request=httpx.Request("POST", "https://test"), 
            response=mock_resp
        )
        
        client = MagicMock()
        client.post.return_value = mock_resp
        mock_client.return_value.__enter__.return_value = client
        
        llm_cfg = {
            "azure_tenant_id": "tenant",
            "azure_client_id": "client",
            "azure_client_secret": "secret"
        }
        with pytest.raises(httpx.HTTPStatusError):
            _get_azure_bearer_token(llm_cfg)

@pytest.mark.asyncio
async def test_ollama_provider(mock_config):
    # Clear cache before test
    from app.services.llm.utils import get_model_cache
    get_model_cache().clear()
    
    provider = OllamaProviderImpl()
    with patch("app.services.llm.providers.ollama.httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "llama3"}]}
        
        async_client = AsyncMock()
        async_client.get.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = async_client
        
        models = await provider.list_models(refresh=True)
        assert "llama3" in models
    
    # Test build
    model = provider.build("llama3")
    assert model.model_name == "llama3"
    assert provider.configured()
    assert any("OLLAMA_BASE_URL" in r for r in provider.requirements())

@pytest.mark.asyncio
async def test_ollama_fetch_error(mock_config):
    # Clear cache before test
    from app.services.llm.utils import get_model_cache
    get_model_cache().clear()
    
    with patch("app.services.llm.providers.ollama.httpx.AsyncClient") as mock_client:
        async_client = AsyncMock()
        async_client.get.side_effect = Exception("Connection error")
        mock_client.return_value.__aenter__.return_value = async_client
        
        models = await fetch_ollama_models(refresh=True)
        assert models == []

@pytest.mark.asyncio
async def test_ollama_fetch_cache(mock_config):
    with patch("app.services.llm.providers.ollama.get_model_cache") as mock_cache:
        mock_cache.return_value = {
            "ollama": {"models": ["cached-model"], "ts": time.time()}
        }
        models = await fetch_ollama_models(refresh=False)
        assert "cached-model" in models

@pytest.mark.asyncio
async def test_gemini_provider(mock_config):
    provider = GeminiProviderImpl()
    # Mock build_async_client to avoid real network call
    with patch("app.services.llm.providers.gemini.build_async_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "models/gemini-1.5-pro"}]}
        
        async_client = AsyncMock()
        async_client.get.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = async_client
        
        models = await provider.list_models(refresh=True)
        assert "gemini-1.5-pro" in models
    
    model = provider.build("gemini-1.5-pro")
    assert model.model_name == "gemini-1.5-pro"

@pytest.mark.asyncio
async def test_litellm_provider(mock_config):
    provider = LiteLLMProviderImpl()
    assert provider.configured()
    
    with patch("app.services.llm.providers.litellm.build_async_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "lite-model"}]}
        
        async_client = AsyncMock()
        async_client.get.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = async_client
        
        models = await provider.list_models(refresh=True)
        assert "lite-model" in models
    
    model = provider.build("lite-model")
    assert model.model_name == "lite-model"
    assert "LITELLM_API_KEY" in provider.requirements()

@pytest.mark.asyncio
async def test_custom_provider(mock_config):
    provider = CustomProviderImpl()
    with patch("app.services.llm.providers.custom.config_service") as mock_cfg:
        mock_cfg.get_llm_config.return_value = {
            "custom_models": [
                {"name": "my-model", "base_url": "http://test", "api_key": "test"}
            ]
        }
        models = await provider.list_models()
        assert "my-model" in models
        
        model = provider.build("my-model")
        assert model.model_name == "my-model"

@pytest.mark.asyncio
async def test_zhipu_provider(mock_config):
    provider = ZhipuProviderImpl()
    models = await provider.list_models()
    assert "glm-4v" in models
    assert provider.configured()
    
    model = provider.build("glm-4v")
    assert model.model_name == "glm-4v"
    assert "ZHIPU_API_KEY" in provider.requirements()

@pytest.mark.asyncio
async def test_deepseek_provider(mock_config):
    provider = DeepSeekProviderImpl()
    models = await provider.list_models()
    assert "deepseek-chat" in models
    assert provider.configured()
    
    model = provider.build("deepseek-chat")
    assert model.model_name == "deepseek-chat"
    assert "DEEPSEEK_API_KEY" in provider.requirements()
