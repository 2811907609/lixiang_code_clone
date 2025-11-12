#!/usr/bin/env python3
"""
测试 BaseMicroAgent 抽象基类和重构后的 micro agents
"""

import pytest
from ai_agents.micro_agents import (
    BaseMicroAgent,
    SearchAgent,
    TestExecutionAgent,
)
from ai_agents.core import TaskType


def test_base_micro_agent_interface():
    """测试 BaseMicroAgent 抽象基类接口"""
    # 验证 BaseMicroAgent 是抽象类
    with pytest.raises(TypeError):
        # 这应该失败，因为 BaseMicroAgent 是抽象类
        BaseMicroAgent()


@pytest.mark.parametrize("agent_class,agent_name", [
    (SearchAgent, "SearchAgent"),
    (TestExecutionAgent, "TestExecutionAgent"),
])
def test_micro_agent_inheritance(agent_class, agent_name):
    """测试 micro agent 继承 BaseMicroAgent"""
    # 创建 agent 实例（不使用模型管理器避免依赖）
    agent = agent_class(model=None)

    # 验证继承关系
    assert isinstance(agent, BaseMicroAgent)

    # 测试抽象属性
    assert agent.name is not None
    assert agent.default_task_type is not None
    assert len(agent.description) > 0

    # 测试 get_code_agent 方法
    code_agent = agent.get_code_agent()
    assert code_agent is not None
    assert hasattr(code_agent, 'name')

    # 测试工具列表
    tools = agent._get_tools()
    assert len(tools) > 0

    # 验证所有工具都是可调用的
    for tool in tools:
        assert callable(tool)


def test_interface_consistency():
    """测试接口一致性"""
    search_agent = SearchAgent(model=None)

    # 验证必需的方法存在
    required_methods = ['get_code_agent', 'run', '_get_tools']
    for method_name in required_methods:
        assert hasattr(search_agent, method_name), f"{method_name} 方法缺失"

    # 验证必需的属性存在
    required_properties = ['name', 'description', 'default_task_type']
    for prop_name in required_properties:
        assert hasattr(search_agent, prop_name), f"{prop_name} 属性缺失"
        value = getattr(search_agent, prop_name)
        assert value is not None, f"{prop_name} 属性值为 None"


@pytest.mark.unit
def test_search_agent_specific():
    """测试 SearchAgent 特定功能"""
    agent = SearchAgent(model=None)

    # 验证名称
    assert agent.name == "search_agent"

    # 验证任务类型
    assert agent.default_task_type == TaskType.COMPLEX_REASONING

    # 验证描述包含关键词
    assert "搜索" in agent.description
    assert "关键词" in agent.description

    # 验证工具数量
    tools = agent._get_tools()
    assert len(tools) == 7  # SearchAgent 应该有 7 个工具
