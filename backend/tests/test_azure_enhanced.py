import pytest
import re
from unittest.mock import MagicMock, patch
from app.services.llm.providers.azure import AzureOpenAIProviderImpl, fetch_azure_deployments
from app.services.llm.factory import list_providers

@pytest.fixture
def mock_config():
    with patch("app.services.llm.providers.azure.config_service") as mock_azure_cfg, \
         patch("app.services.llm.factory.config_service") as mock_factory_cfg:
        
        # Default mock config for Azure
        azure_config = {
            "azure_openai_base_url": "https://test-resource.openai.azure.com",
            "azure_openai_deployment": "gpt-4o:2024-06-01,o1-preview:2024-09-01-preview,gpt-35-turbo",
            "azure_openai_api_version": "2024-02-01",
            "azure_openai_token": "test-key"
        }
        mock_azure_cfg.get_llm_config.return_value = azure_config
        mock_factory_cfg.get_llm_config.return_value = azure_config
        
        yield {
            "azure": mock_azure_cfg,
            "factory": mock_factory_cfg
        }

@pytest.mark.asyncio
async def test_azure_fetch_multiple_deployments(mock_config):
    """验证能够正确解析多个部署名称，且忽略版本号"""
    deployments = await fetch_azure_deployments()
    assert deployments == ["gpt-4o", "o1-preview", "gpt-35-turbo"]

@pytest.mark.asyncio
async def test_azure_build_with_specific_version(mock_config):
    """验证 build 方法能根据部署名匹配对应的 API 版本"""
    provider = AzureOpenAIProviderImpl()
    
    # 1. 测试显式指定版本的部署
    with patch("app.services.llm.providers.azure.AsyncAzureOpenAI") as mock_client:
        provider.build("gpt-4o")
        # 检查 AsyncAzureOpenAI 初始化参数
        args, kwargs = mock_client.call_args
        assert kwargs["api_version"] == "2024-06-01"
        # 验证 api-version 同时也通过 default_query 传递
        assert kwargs["default_query"] == {"api-version": "2024-06-01"}
        # 验证 base_url (azure_endpoint) 不包含 api-version
        assert "api-version" not in str(kwargs["azure_endpoint"])
        
    # 2. 测试另一个显式指定版本的部署
    with patch("app.services.llm.providers.azure.AsyncAzureOpenAI") as mock_client:
        provider.build("o1-preview")
        args, kwargs = mock_client.call_args
        assert kwargs["api_version"] == "2024-09-01-preview"
        assert kwargs["default_query"] == {"api-version": "2024-09-01-preview"}
        
    # 3. 测试未指定版本的部署（应回退到全局配置或默认值）
    with patch("app.services.llm.providers.azure.AsyncAzureOpenAI") as mock_client:
        provider.build("gpt-35-turbo")
        args, kwargs = mock_client.call_args
        # 在 mock_config 中设置了 azure_openai_api_version 为 2024-02-01
        assert kwargs["api_version"] == "2024-02-01"
        assert kwargs["default_query"] == {"api-version": "2024-02-01"}

@pytest.mark.asyncio
async def test_azure_configured_validation(mock_config):
    """验证 Azure 配置校验逻辑，包括版本号格式"""
    provider = AzureOpenAIProviderImpl()
    
    # 正确配置
    assert provider.configured() is True
    
    # 测试错误的版本号格式（虽然目前只是 warning，但逻辑应能跑通）
    mock_config["azure"].get_llm_config.return_value["azure_openai_deployment"] = "bad-model:invalid-version"
    assert provider.configured() is True # 依然返回 True，但内部会有 warning

@pytest.mark.asyncio
async def test_provider_filtering_logic(mock_config):
    """验证 factory 中的 Provider 过滤逻辑"""
    # 模拟只开启 openai 和 azure_openai
    mock_config["factory"].get_llm_config.return_value["enabled_providers"] = "openai,azure_openai"
    
    providers = await list_providers()
    provider_names = [p["name"] for p in providers]
    
    assert "openai" in provider_names
    assert "azure_openai" in provider_names
    assert "deepseek" not in provider_names
    assert "zhipu" not in provider_names
    
    # 模拟开启全部 (空字符串或 None)
    mock_config["factory"].get_llm_config.return_value["enabled_providers"] = ""
    providers = await list_providers()
    assert len(providers) > 2
    assert any(p["name"] == "deepseek" for p in providers)

@pytest.mark.asyncio
async def test_azure_build_default_model(mock_config):
    """验证不传 model_name 时，build 默认使用第一个部署"""
    provider = AzureOpenAIProviderImpl()
    
    with patch("app.services.llm.providers.azure.AsyncAzureOpenAI") as mock_client:
        # 不传参数
        provider.build()
        # 应该使用了列表中的第一个：gpt-4o
        model = provider.build()
        # 注意：build 返回的是 OpenAIChatModel，其 model 属性是 deployment name
        assert model.model_name == "gpt-4o"
