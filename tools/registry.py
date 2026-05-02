from tools.base import Tool
from typing import Dict, Type

_tool_registry: Dict[str, Type[Tool]] = {}

def register_tool(name: str| None  = None):
    """装饰器: 将工具类自动注册进全局表"""
    def decorator(cls):
        tool_name = name if name else cls.__name__
        _tool_registry[tool_name] = cls
        return cls
    return decorator

def get_all_tools() -> Dict[str, Type[Tool]]:
    """返回所有已注册的工具类字典"""
    return _tool_registry.copy()