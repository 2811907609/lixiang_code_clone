"""
测试SubTaskTrackedAgent包装器
"""

from unittest.mock import Mock
from ai_agents.lib.smolagents import SubTaskTrackedAgent
from ai_agents.lib.tracing import task_context, get_current_sub_task_id, get_current_agent_id


def test_sub_task_tracked_agent_call_method():
    """测试SubTaskTrackedAgent的__call__方法"""
    # 创建mock原始agent
    mock_agent = Mock()
    # 设置Mock对象的调用行为
    mock_agent.return_value = "Call result"  # 当mock_agent()被调用时返回这个值

    agent_name = "test_agent"
    wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

    # 测试__call__方法是否存在
    assert callable(wrapped_agent), "SubTaskTrackedAgent应该是可调用的"

    # 测试调用
    with task_context("main_task"):
        result = wrapped_agent("test task")

        # 验证结果
        assert result == "Call result"

        # 验证原始agent被调用
        mock_agent.assert_called_once_with("test task")


def test_sub_task_tracked_agent_run_method():
    """测试SubTaskTrackedAgent的run方法"""
    # 创建mock原始agent
    mock_agent = Mock()
    mock_agent.run = Mock(return_value="Run result")

    agent_name = "test_agent"
    wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

    # 测试run方法
    with task_context("main_task"):
        result = wrapped_agent.run("test task")

        # 验证结果
        assert result == "Run result"

        # 验证原始agent的run被调用
        mock_agent.run.assert_called_once_with("test task")


def test_sub_task_context_creation():
    """测试子任务上下文的创建"""
    # 创建mock原始agent
    mock_agent = Mock()

    def mock_call(task, **kwargs):
        # 在调用时检查上下文
        sub_task_id = get_current_sub_task_id()
        agent_id = get_current_agent_id()
        return f"Task: {task}, SubTask: {sub_task_id}, Agent: {agent_id}"

    # 设置Mock对象的调用行为
    mock_agent.side_effect = mock_call

    agent_name = "context_test_agent"
    wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

    # 测试上下文创建
    with task_context("main_task"):
        result = wrapped_agent("test task")

        # 验证结果包含上下文信息
        assert "test task" in result
        assert "context_test_agent" in result
        assert "sub_context_test_agent_" in result  # 子任务ID应该包含agent名称


def test_attribute_delegation():
    """测试属性代理"""
    # 创建mock原始agent
    mock_agent = Mock()
    mock_agent.some_attribute = "test_value"
    mock_agent.some_method = Mock(return_value="method_result")

    agent_name = "delegation_test_agent"
    wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

    # 测试属性代理
    assert wrapped_agent.some_attribute == "test_value"

    # 测试方法代理
    result = wrapped_agent.some_method("arg1", "arg2")
    assert result == "method_result"
    mock_agent.some_method.assert_called_once_with("arg1", "arg2")


def test_callable_check():
    """测试包装后的agent是否可调用"""
    # 创建mock原始agent
    mock_agent = Mock()
    mock_agent.return_value = "callable_result"

    agent_name = "callable_test_agent"
    wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

    # 测试是否可调用
    assert callable(wrapped_agent), "SubTaskTrackedAgent应该是可调用的"

    # 测试直接调用
    with task_context("main_task"):
        result = wrapped_agent("direct call")
        assert result == "callable_result"
        mock_agent.assert_called_once_with("direct call")


if __name__ == "__main__":
    # 运行所有测试
    test_sub_task_tracked_agent_call_method()
    print("✓ __call__方法测试通过")

    test_sub_task_tracked_agent_run_method()
    print("✓ run方法测试通过")

    test_sub_task_context_creation()
    print("✓ 子任务上下文创建测试通过")

    test_attribute_delegation()
    print("✓ 属性代理测试通过")

    test_callable_check()
    print("✓ 可调用性测试通过")

    print("\n🎉 所有测试通过！")
