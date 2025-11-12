"""
测试监督智能体与执行环境的集成
"""

import pytest
from ai_agents.tools.execution import create_execution_environment


class TestSupervisorAgentExecutionIntegration:
    """测试监督智能体与执行环境的集成"""

    def test_base_supervisor_agent_import_and_init(self):
        """测试基础监督智能体的导入和初始化"""
        from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent

        # 测试导入成功
        assert BaseSupervisorAgent is not None

        # 由于 BaseSupervisorAgent 是抽象类，我们创建一个简单的实现来测试
        class TestSupervisorAgent(BaseSupervisorAgent):
            @property
            def sop_category(self) -> str:
                return "test"

            @property
            def name(self) -> str:
                return "test_supervisor"

            @property
            def default_task_type(self) -> str:
                return "simple"

            def _get_tools(self):
                return []

        # 测试默认初始化（使用默认host环境）
        agent = TestSupervisorAgent(model=None)
        assert agent._execution_env is not None
        assert hasattr(agent._execution_env, 'tools')

        # 测试获取默认工具包含执行环境工具
        tools = agent._get_default_tools()
        assert len(tools) > 0

        # 验证执行环境工具在工具列表中
        execution_tools = agent._execution_env.tools()
        assert len(execution_tools) > 0

    def test_supervisor_agent_with_custom_execution_env(self):
        """测试监督智能体使用自定义执行环境"""
        from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent

        class TestSupervisorAgent(BaseSupervisorAgent):
            @property
            def sop_category(self) -> str:
                return "test"

            @property
            def name(self) -> str:
                return "test_supervisor"

            @property
            def default_task_type(self) -> str:
                return "simple"

            def _get_tools(self):
                return []

        # 创建自定义执行环境
        custom_env = create_execution_environment(
            "host",
            timeout_seconds=60.0,
            allow_dangerous_commands=False
        )

        # 使用自定义执行环境初始化智能体
        agent = TestSupervisorAgent(model=None, execution_env=custom_env)
        assert agent._execution_env is custom_env

        # 验证工具正确获取
        execution_tools = custom_env.tools()
        assert len(execution_tools) > 0

    def test_supervisor_agent_with_execution_env_config(self):
        """测试监督智能体使用执行环境配置"""
        from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent

        class TestSupervisorAgent(BaseSupervisorAgent):
            @property
            def sop_category(self) -> str:
                return "test"

            @property
            def name(self) -> str:
                return "test_supervisor"

            @property
            def default_task_type(self) -> str:
                return "simple"

            def _get_tools(self):
                return []

        # 使用执行环境配置
        config = {
            "timeout_seconds": 45.0,
            "validate_commands": True,
            "allow_dangerous_commands": False
        }

        agent = TestSupervisorAgent(model=None, execution_env_config=config)
        assert agent._execution_env is not None
        assert agent._execution_env.timeout_seconds == 45.0

class TestExecutionEnvironmentMigration:

    def test_execution_environment_factory_functionality(self):
        """测试执行环境工厂函数的功能"""
        # 测试创建host环境
        host_env = create_execution_environment("host")
        assert host_env is not None
        assert host_env.is_started

        # 测试获取工具
        tools = host_env.tools()
        assert len(tools) == 1
        assert callable(tools[0])

        # 测试工具执行（简单命令）
        execute_command = tools[0]
        result = execute_command("echo 'test'")
        assert "test" in result
        assert "SUCCESS" in result

    @pytest.mark.docker
    def test_execution_environment_interface_consistency(self):
        """测试执行环境接口的一致性"""
        # 创建不同类型的执行环境
        host_env = create_execution_environment("host")
        docker_env = create_execution_environment(
            "docker",
            session_id="test_consistency",
            auto_start=False
        )

        # 测试接口一致性
        for env in [host_env, docker_env]:
            assert hasattr(env, 'tools')
            assert hasattr(env, 'start')
            assert hasattr(env, 'stop')
            assert hasattr(env, 'is_started')

            tools = env.tools()
            assert isinstance(tools, list)
            assert len(tools) == 1
            assert callable(tools[0])

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        host_env = create_execution_environment("host")
        execute_command = host_env.tools()[0]

        # 测试基本命令执行
        result = execute_command("echo 'hello world'")
        assert "hello world" in result
        assert "Command:" in result
        assert "Exit Code:" in result
        assert "Execution Status:" in result

        # 测试错误处理
        result = execute_command("false")
        assert "FAILED" in result
        assert "Exit Code: 1" in result
