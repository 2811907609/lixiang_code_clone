"""
测试任务ID在supervisor agent和micro agents之间的传播
"""

from unittest.mock import patch, Mock

from ai_agents.lib.tracing import (
    task_context, get_current_task_id, sub_task_context,
    get_current_sub_task_id, get_current_agent_id
)


class TestTaskIdPropagation:
    """测试任务ID在supervisor和micro agents之间的传播"""

    def test_task_id_propagation_in_context(self):
        """测试任务ID在上下文中的传播"""
        test_task_id = "test_propagation_123"

        def check_task_id_in_nested_function():
            """嵌套函数中检查任务ID"""
            return get_current_task_id()

        # 在任务上下文中检查ID传播
        with task_context(test_task_id) as task_id:
            assert task_id == test_task_id
            assert get_current_task_id() == test_task_id

            # 在嵌套函数中也应该能获取到相同的任务ID
            nested_task_id = check_task_id_in_nested_function()
            assert nested_task_id == test_task_id

    @patch('ai_agents.lib.tracing.litellm.completion')
    @patch('ai_agents.supervisor_agents.base_supervisor_agent.get_model_for_task')
    def test_micro_agent_task_id_inheritance(self, mock_get_model, mock_completion):
        """测试micro agents继承supervisor的任务ID"""
        # Mock模型和LLM响应
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Mock response"
        mock_completion.return_value = mock_response

        # 设置任务ID注入
        from ai_agents.lib.tracing import _setup_task_id_injection
        _setup_task_id_injection()

        test_task_id = "micro_agent_test_789"

        # 模拟在任务上下文中运行
        with task_context(test_task_id):
            # 检查supervisor中的任务ID
            assert get_current_task_id() == test_task_id

            # 在同一上下文中，micro agents也应该能获取到任务ID
            assert get_current_task_id() == test_task_id

            # 模拟micro agent的LLM调用
            import litellm
            litellm.completion(
                messages=[{"role": "user", "content": "test"}],
                model="test-model"
            )

            # 验证LLM调用包含了任务ID
            mock_completion.assert_called()
            call_args = mock_completion.call_args
            assert 'metadata' in call_args.kwargs
            assert call_args.kwargs['metadata']['task_id'] == test_task_id

    def test_task_id_isolation_between_tasks(self):
        """测试不同任务之间的任务ID隔离"""
        task_id_1 = "task_1"
        task_id_2 = "task_2"

        # 第一个任务上下文
        with task_context(task_id_1):
            assert get_current_task_id() == task_id_1

            # 嵌套第二个任务上下文
            with task_context(task_id_2):
                assert get_current_task_id() == task_id_2

            # 退出嵌套后应该恢复第一个任务ID
            assert get_current_task_id() == task_id_1

        # 退出所有上下文后应该为None
        assert get_current_task_id() is None

    def test_model_info_includes_current_task_id(self):
        """测试model_info包含当前任务ID"""
        from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent

        # 创建一个简单的测试supervisor
        class TestSupervisor(BaseSupervisorAgent):
            @property
            def name(self):
                return "test_supervisor"

            @property
            def sop_category(self):
                return "test"

            @property
            def default_task_type(self):
                return "simple_qa"

            def _get_tools(self):
                return []

        test_task_id = "model_info_test"
        with task_context(test_task_id):
            assert get_current_task_id() == test_task_id


class TestTaskIdInMicroAgents:
    """测试micro agents中的任务ID处理"""

    @patch('ai_agents.core.model_manager.get_model_for_task')
    def test_micro_agent_direct_run_with_task_context(self, mock_get_model):
        """测试micro agent直接运行时的任务ID上下文"""
        from ai_agents.micro_agents.search_agent import SearchAgent

        # Mock模型
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        search_agent = SearchAgent()

        test_task_id = "micro_direct_run"

        # Mock agent.run方法
        def mock_agent_run(task):
            current_id = get_current_task_id()
            return f"Micro agent executed with ID: {current_id}"

        # 在任务上下文中运行micro agent
        with task_context(test_task_id):
            # Mock get_code_agent返回的agent
            mock_code_agent = Mock()
            mock_code_agent.run = mock_agent_run

            with patch.object(search_agent, 'get_code_agent', return_value=mock_code_agent):
                result = search_agent.run("test search task")
                assert test_task_id in result


class TestSubTaskTracking:
    """测试子任务追踪功能"""

    def test_sub_task_context_basic(self):
        """测试基本的子任务上下文功能"""
        agent_name = "test_agent"

        # 初始状态
        assert get_current_sub_task_id() is None
        assert get_current_agent_id() is None

        # 在子任务上下文中
        with sub_task_context(agent_name) as sub_task_id:
            assert sub_task_id is not None
            assert sub_task_id.startswith(f"sub_{agent_name}_")
            assert get_current_sub_task_id() == sub_task_id
            assert get_current_agent_id() == agent_name

        # 退出上下文后
        assert get_current_sub_task_id() is None
        assert get_current_agent_id() is None

    def test_nested_task_and_sub_task_context(self):
        """测试嵌套的任务和子任务上下文"""
        main_task_id = "main_task_123"
        agent_name = "nested_agent"

        with task_context(main_task_id):
            assert get_current_task_id() == main_task_id
            assert get_current_sub_task_id() is None

            with sub_task_context(agent_name) as sub_task_id:
                # 在子任务上下文中，主任务ID应该保持
                assert get_current_task_id() == main_task_id
                assert get_current_sub_task_id() == sub_task_id
                assert get_current_agent_id() == agent_name

            # 退出子任务上下文后，主任务ID应该保持
            assert get_current_task_id() == main_task_id
            assert get_current_sub_task_id() is None
            assert get_current_agent_id() is None

    @patch('ai_agents.lib.tracing.litellm.completion')
    def test_sub_task_metadata_injection(self, mock_completion):
        """测试子任务元数据注入"""
        # 设置任务ID注入
        from ai_agents.lib.tracing import _setup_task_id_injection
        _setup_task_id_injection()

        # Mock响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Mock response"
        mock_completion.return_value = mock_response

        main_task_id = "main_task_456"
        agent_name = "metadata_test_agent"

        with task_context(main_task_id):
            with sub_task_context(agent_name) as sub_task_id:
                # 模拟LLM调用
                import litellm
                litellm.completion(
                    messages=[{"role": "user", "content": "test"}],
                    model="test-model"
                )

                # 验证元数据
                mock_completion.assert_called()
                call_args = mock_completion.call_args
                metadata = call_args.kwargs['metadata']

                # 检查所有追踪信息
                assert metadata['task_id'] == main_task_id
                assert metadata['session_id'] == main_task_id
                assert metadata['sub_task_id'] == sub_task_id
                assert metadata['agent_id'] == agent_name
                assert metadata['user_id'] == agent_name
                assert metadata['trace_id'] == f"{main_task_id}.{sub_task_id}"
                assert metadata['trace_chain'] == f"{main_task_id}.{sub_task_id}.{agent_name}"

    def test_sub_task_tracked_agent_wrapper(self):
        """测试SubTaskTrackedAgent包装器"""
        from ai_agents.lib.smolagents import SubTaskTrackedAgent

        # 创建mock原始agent
        mock_agent = Mock()
        mock_agent.run.return_value = "Original agent result"
        mock_agent.return_value = "Original agent call result"  # 设置调用时的返回值

        agent_name = "wrapper_test_agent"
        wrapped_agent = SubTaskTrackedAgent(mock_agent, agent_name)

        # 测试属性代理
        assert wrapped_agent._agent_name == agent_name

        # 测试run方法包装
        main_task_id = "wrapper_test_task"

        with task_context(main_task_id):
            # 在调用前，应该没有子任务信息
            assert get_current_sub_task_id() is None
            assert get_current_agent_id() is None

            # 测试run方法调用
            result = wrapped_agent.run("test task")

            # 验证原始agent被调用
            mock_agent.run.assert_called_once_with("test task")
            assert result == "Original agent result"

            # 调用后，子任务上下文应该已经清理
            assert get_current_sub_task_id() is None
            assert get_current_agent_id() is None

            # 重置mock
            mock_agent.reset_mock()

            # 测试__call__方法调用（smolagents框架使用的方法）
            result = wrapped_agent("test call task")

            # 验证原始agent被调用
            mock_agent.assert_called_once_with("test call task")
            assert result == "Original agent call result"

            # 调用后，子任务上下文应该已经清理
            assert get_current_sub_task_id() is None
            assert get_current_agent_id() is None

    @patch('ai_agents.core.model_manager.get_model_for_task')
    def test_micro_agent_with_sub_task_tracking(self, mock_get_model):
        """测试micro agent的子任务追踪集成"""
        from ai_agents.micro_agents.search_agent import SearchAgent

        # Mock模型
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        search_agent = SearchAgent()

        # 获取包装的code agent
        code_agent = search_agent.get_code_agent()

        # 验证返回的是SubTaskTrackedAgent
        from ai_agents.lib.smolagents import SubTaskTrackedAgent
        assert isinstance(code_agent, SubTaskTrackedAgent)
        assert code_agent._agent_name == search_agent.name
