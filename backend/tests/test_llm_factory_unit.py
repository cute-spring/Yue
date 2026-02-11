import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm.factory import (
    get_model,
    list_supported_providers,
    list_providers,
    list_providers_structured,
    _supports_model_refresh
)
from app.services.llm.base import LLMProvider, SimpleProvider

class MockProvider(SimpleProvider):
    name = "mock_provider"
    def build(self, model_name=None):
        return f"model_{model_name}" if model_name else "default_model"
    async def list_models(self, refresh=bool):
        return ["model1", "model2"]
    def requirements(self):
        return ["API_KEY"]
    def configured(self):
        return True

@pytest.fixture
def mock_registry():
    with patch("app.services.llm.factory.get_registered_providers") as mock_get:
        mock_p = MockProvider()
        mock_p.list_models = AsyncMock(return_value=["model1", "model2"])
        mock_get.return_value = {"mock_provider": mock_p}
        yield mock_get, mock_p

@pytest.fixture
def mock_config():
    with patch("app.services.llm.factory.config_service") as mock_cfg:
        mock_cfg.get_llm_config.return_value = {
            "mock_provider_enabled_models": ["model1"],
            "mock_provider_enabled_models_mode": "allowlist",
            "mock_provider_model": "model1"
        }
        yield mock_cfg

def test_supports_model_refresh():
    assert _supports_model_refresh("openai") is True
    assert _supports_model_refresh("ollama") is True
    assert _supports_model_refresh("unknown") is False

def test_get_model_success(mock_registry):
    mock_get, mock_p = mock_registry
    model = get_model("mock_provider", "test_model")
    assert model == "model_test_model"

def test_get_model_fallback(mock_registry):
    mock_get, mock_p = mock_registry
    # Add openai to mock registry for fallback
    openai_p = MagicMock()
    openai_p.build.return_value = "openai_model"
    mock_get.return_value["openai"] = openai_p
    
    model = get_model("non_existent")
    assert model == "openai_model"
    openai_p.build.assert_called_once_with(None)

def test_get_model_fail_no_fallback(mock_registry):
    mock_get, mock_p = mock_registry
    mock_get.return_value = {} # Empty registry
    with pytest.raises(ValueError, match="Provider non_existent not found and fallback to OpenAI failed"):
        get_model("non_existent")

def test_list_supported_providers():
    with patch("app.services.llm.factory.list_registered_providers") as mock_list:
        mock_list.return_value = ["openai", "ollama"]
        assert list_supported_providers() == ["openai", "ollama"]

@pytest.mark.asyncio
async def test_list_providers_basic(mock_registry, mock_config):
    _, mock_p = mock_registry
    providers = await list_providers()
    
    assert len(providers) == 1
    p = providers[0]
    assert p["name"] == "mock_provider"
    assert p["available_models"] == ["model1"] # Filtered by allowlist
    assert p["models"] == ["model1", "model2"] # All models
    assert p["supports_model_refresh"] is False
    assert p["current_model"] == "model1"

@pytest.mark.asyncio
async def test_list_providers_no_allowlist(mock_registry, mock_config):
    mock_config.get_llm_config.return_value = {
        "mock_provider_enabled_models": [],
        "mock_provider_enabled_models_mode": "off"
    }
    providers = await list_providers()
    assert providers[0]["available_models"] == ["model1", "model2"]

@pytest.mark.asyncio
async def test_list_providers_error_handling(mock_registry, mock_config):
    _, mock_p = mock_registry
    mock_p.list_models.side_effect = Exception("API Error")
    
    providers = await list_providers()
    assert providers[0]["models"] == ["model1"] # Fallback to config_enabled if list_models fails
    assert providers[0]["available_models"] == ["model1"]

@pytest.mark.asyncio
async def test_list_providers_structured(mock_registry, mock_config):
    providers = await list_providers_structured()
    assert len(providers) == 1
    assert providers[0].name == "mock_provider"
    assert providers[0].available_models == ["model1"]
