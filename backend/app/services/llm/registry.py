from typing import Dict, List
from .base import SimpleProvider

_dynamic_providers: Dict[str, SimpleProvider] = {}
"""运行时注册的 Provider 存储表；键为 provider.name 的小写"""

def register_provider(provider: SimpleProvider) -> None:
    """注册一个新的 Provider；重复名称会覆盖旧的实现"""
    _dynamic_providers[provider.name.lower()] = provider

def unregister_provider(name: str) -> None:
    """卸载指定名称的 Provider"""
    _dynamic_providers.pop(name.lower(), None)

def list_registered_providers() -> List[str]:
    """列出当前已注册的 Provider 名称（小写）"""
    return list(_dynamic_providers.keys())

def get_registered_providers() -> Dict[str, SimpleProvider]:
    """返回所有已注册的 Provider 字典"""
    return _dynamic_providers
