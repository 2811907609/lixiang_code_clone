"""
测试 smolagents 相关功能
"""

from ai_agents.lib.smolagents import tool, is_tool_decorated


@tool
def sample_tool_function(x: int, message: str) -> str:
    """
    示例工具函数

    Args:
        x: 整数参数
        message: 字符串消息

    Returns:
        str: 格式化的结果
    """
    return f"结果: {x} - {message}"


def regular_function(x: int, message: str) -> str:
    """
    普通函数，未被装饰

    Args:
        x: 整数参数
        message: 字符串消息

    Returns:
        str: 格式化的结果
    """
    return f"结果: {x} - {message}"


class TestIsToolDecorated:
    """测试 is_tool_decorated 函数"""

    def test_tool_decorated_function_returns_true(self):
        """测试被 @tool 装饰的函数返回 True"""
        assert is_tool_decorated(sample_tool_function) is True

    def test_regular_function_returns_false(self):
        """测试普通函数返回 False"""
        assert is_tool_decorated(regular_function) is False

    def test_non_function_objects_return_false(self):
        """测试非函数对象返回 False"""
        assert is_tool_decorated("string") is False
        assert is_tool_decorated(123) is False
        assert is_tool_decorated([1, 2, 3]) is False
        assert is_tool_decorated({"key": "value"}) is False
        assert is_tool_decorated(None) is False

    def test_tool_decorated_function_has_tool_attributes(self):
        """测试被装饰的函数具有工具属性"""
        assert hasattr(sample_tool_function, 'name')
        assert hasattr(sample_tool_function, 'description')
        assert hasattr(sample_tool_function, 'inputs')
        assert hasattr(sample_tool_function, 'output_type')
        assert hasattr(sample_tool_function, 'forward')

    def test_regular_function_lacks_tool_attributes(self):
        """测试普通函数缺少工具属性"""
        assert not hasattr(regular_function, 'name')
        assert not hasattr(regular_function, 'description')
        assert not hasattr(regular_function, 'inputs')
        assert not hasattr(regular_function, 'output_type')
        assert not hasattr(regular_function, 'forward')
