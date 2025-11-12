"""
测试任务ID追踪功能
"""

from unittest.mock import patch, Mock

from ai_agents.lib.tracing import (
    generate_task_id,
    set_current_task_id,
    get_current_task_id,
    clear_current_task_id,
    task_context
)


class TestTaskIdManagement:
    """任务ID管理测试"""

    def test_generate_task_id(self):
        """测试生成任务ID"""
        task_id = generate_task_id()

        assert task_id is not None
        assert task_id.startswith("task_")
        assert len(task_id) == 17  # "task_" + 12字符的hex

        # 生成的ID应该是唯一的
        task_id2 = generate_task_id()
        assert task_id != task_id2

    def test_set_and_get_task_id(self):
        """测试设置和获取任务ID"""
        test_task_id = "test_task_123"

        # 初始状态应该为None
        assert get_current_task_id() is None

        # 设置任务ID
        set_current_task_id(test_task_id)
        assert get_current_task_id() == test_task_id

        # 清除任务ID
        clear_current_task_id()
        assert get_current_task_id() is None

    def test_task_context_manager(self):
        """测试任务上下文管理器"""
        # 测试自动生成任务ID
        with task_context() as task_id:
            assert task_id is not None
            assert task_id.startswith("task_")
            assert get_current_task_id() == task_id

        # 上下文结束后应该清除
        assert get_current_task_id() is None

        # 测试指定任务ID
        custom_task_id = "custom_task_456"
        with task_context(custom_task_id) as task_id:
            assert task_id == custom_task_id
            assert get_current_task_id() == custom_task_id

        assert get_current_task_id() is None

    def test_nested_task_context(self):
        """测试嵌套任务上下文"""
        outer_task_id = "outer_task"
        inner_task_id = "inner_task"

        with task_context(outer_task_id) as _:
            assert get_current_task_id() == outer_task_id

            with task_context(inner_task_id) as _:
                assert get_current_task_id() == inner_task_id

            # 内层上下文结束后应该恢复外层
            assert get_current_task_id() == outer_task_id

        # 所有上下文结束后应该清除
        assert get_current_task_id() is None


class TestLiteLLMIntegration:
    """测试与litellm的集成"""

    @patch('ai_agents.lib.tracing.litellm.completion')
    def test_task_id_injection(self, mock_completion):
        """测试任务ID注入到litellm调用中"""
        from ai_agents.lib.tracing import _setup_task_id_injection

        # 设置任务ID注入
        _setup_task_id_injection()

        # 模拟响应
        mock_response = Mock()
        mock_completion.return_value = mock_response

        test_task_id = "test_injection_123"

        with task_context(test_task_id):
            # 导入被修改的litellm.completion
            import litellm

            # 调用litellm.completion
            litellm.completion(
                messages=[{"role": "user", "content": "test"}],
                model="test-model"
            )

        # 验证调用参数
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args

        # 检查metadata是否包含任务ID
        assert 'metadata' in call_args.kwargs
        assert call_args.kwargs['metadata']['task_id'] == test_task_id
        assert call_args.kwargs['metadata']['session_id'] == test_task_id

    @patch('ai_agents.lib.tracing.litellm.completion')
    def test_no_task_id_injection_when_no_context(self, mock_completion):
        """测试没有任务上下文时不注入任务ID"""
        from ai_agents.lib.tracing import _setup_task_id_injection

        # 设置任务ID注入
        _setup_task_id_injection()

        # 模拟响应
        mock_response = Mock()
        mock_completion.return_value = mock_response

        # 确保没有任务上下文
        clear_current_task_id()

        # 导入被修改的litellm.completion
        import litellm

        # 调用litellm.completion
        litellm.completion(
            messages=[{"role": "user", "content": "test"}],
            model="test-model"
        )

        # 验证调用参数
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args

        # 检查是否没有注入metadata
        if 'metadata' in call_args.kwargs:
            # 如果有metadata，应该不包含task_id
            assert 'task_id' not in call_args.kwargs['metadata']
        # 或者完全没有metadata参数
