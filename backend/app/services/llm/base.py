from enum import Enum
from typing import Optional, List, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel

class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    ZHIPU = "zhipu"
    CUSTOM = "custom"
    AZURE_OPENAI = "azure_openai"
    LITELLM = "litellm"

class SimpleProvider(ABC):
    """
    轻量 Provider 接口：用于以编程方式扩展新的 LLM。
    - name: 注册名（小写唯一）
    - build: 根据可选的 model_name 返回具体可用的模型实例
    - list_models: 异步返回当前可用的模型列表（可选支持 refresh）
    - requirements/configured: 用于展示与管理端判断可用性
    """
    name: str

    @abstractmethod
    def build(self, model_name: Optional[str] = None) -> Any:
        """返回一个可用的模型实例；model_name 为空时应返回默认模型"""
        pass

    @abstractmethod
    async def list_models(self, refresh: bool = False) -> List[str]:
        """返回可用的模型名称列表；出错时建议返回空列表"""
        pass

    def requirements(self) -> List[str]:
        """返回该 Provider 所需的环境或配置说明（如 API_KEY）"""
        return []

    def configured(self) -> bool:
        """是否已配置完成，可用于 UI 显示和过滤"""
        return True

class ProviderInfo(BaseModel):
    name: str
    configured: bool
    requirements: List[str]
    available_models: List[str]
    models: List[str]
    supports_model_refresh: bool = False
    current_model: Optional[str] = None
