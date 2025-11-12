"""
动态模块函数加载器

提供运行时动态加载模块中函数的功能。
"""

import importlib
from typing import Any, Callable


def load_function(module: str, function: str) -> Callable[..., Any]:
    """
    根据模块路径和函数名动态加载函数

    Args:
        module: 模块路径，支持:
            - Python模块名: "ai_agents.micro_agents.test_generation_agent"
        function: 函数名，如 "generate_tests"

    Returns:
        加载的函数对象

    Raises:
        ImportError: 模块导入失败
        AttributeError: 函数不存在
        TypeError: 不是可调用函数

    Example:
        >>> func = load_function("ai_agents.micro_agents.test_generation_agent", "generate_tests")
        >>> result = func(args)
    """


    loaded_module = importlib.import_module(module)

    # 获取函数
    if not hasattr(loaded_module, function):
        raise AttributeError(
            f"模块 '{module}' 中未找到函数 '{function}'。"
        )

    func = getattr(loaded_module, function)

    if not callable(func):
        raise TypeError(
            f"'{function}' 不是一个可调用的函数，类型: {type(func)}"
        )

    return func
