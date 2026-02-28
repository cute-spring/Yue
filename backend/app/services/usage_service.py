import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class UsageStats(BaseModel):
    """
    统一的 Token 使用统计数据模型
    """
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    tps: Optional[float] = None
    finish_reason: Optional[str] = None
    cost: Optional[float] = None  # 预留成本计算

class UsageAdapter(ABC):
    """
    Token 统计适配器接口 (Adapter Pattern)
    """
    @abstractmethod
    def adapt(self, raw_usage: Any, duration: float, finish_reason: Optional[str] = None) -> UsageStats:
        pass

    def _to_int(self, v: Any) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except (ValueError, TypeError):
            return None

class PydanticAIUsageAdapter(UsageAdapter):
    """
    适配 Pydantic AI 的 Usage 对象
    """
    def adapt(self, raw_usage: Any, duration: float, finish_reason: Optional[str] = None) -> UsageStats:
        prompt_tokens = self._to_int(getattr(raw_usage, "request_tokens", None))
        completion_tokens = self._to_int(getattr(raw_usage, "response_tokens", None))
        total_tokens = self._to_int(getattr(raw_usage, "total_tokens", None))
        
        tps = None
        if completion_tokens and duration > 0:
            tps = completion_tokens / duration

        return UsageStats(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tps=tps,
            finish_reason=finish_reason
        )

class OllamaUsageAdapter(UsageAdapter):
    """
    适配 Ollama 特有的统计字段 (如果 Pydantic AI 未能完全覆盖)
    """
    def adapt(self, raw_usage: Any, duration: float, finish_reason: Optional[str] = None) -> UsageStats:
        # 默认回退到 Pydantic AI 的适配逻辑，除非有特殊字段
        adapter = PydanticAIUsageAdapter()
        return adapter.adapt(raw_usage, duration, finish_reason)

def get_usage_adapter(provider: str) -> UsageAdapter:
    """
    统计适配器工厂 (Factory Pattern)
    """
    adapters = {
        "ollama": OllamaUsageAdapter(),
        # 可以根据需要为 deepseek, openai 等添加特定适配器
    }
    return adapters.get(provider.lower(), PydanticAIUsageAdapter())

def calculate_usage(provider: str, raw_usage: Any, duration: float, finish_reason: Optional[str] = None) -> UsageStats:
    """
    便捷函数：计算并适配统计信息
    """
    adapter = get_usage_adapter(provider)
    return adapter.adapt(raw_usage, duration, finish_reason)
