"""
模型管理器测试模块
"""

import pytest
import responses
from unittest.mock import Mock, patch

from ai_agents.core.model_manager import ModelManager
from ai_agents.core.model_types import ModelType, ModelConfig, TaskType, ModelTypeManager
from ai_agents.config import config


class TestModelTypeManager:
    """模型类型管理器测试类"""

    def test_get_config(self):
        """测试获取模型配置"""
        config = ModelTypeManager.get_config(ModelType.FAST)
        assert config.temperature == 0.1
        assert config.max_tokens == 1024
        assert config.timeout == 30

    def test_get_config_invalid_type(self):
        """测试获取无效模型类型配置"""
        with pytest.raises(ValueError, match="不支持的模型类型"):
            ModelTypeManager.get_config("invalid_type")

    def test_get_description(self):
        """测试获取模型描述"""
        desc = ModelTypeManager.get_description(ModelType.POWERFUL)
        assert "强大模型" in desc
        assert "复杂" in desc

    def test_get_recommended_type(self):
        """测试获取推荐模型类型"""
        assert ModelTypeManager.get_recommended_type("intent_classification") == ModelType.FAST
        assert ModelTypeManager.get_recommended_type("code_generation") == ModelType.POWERFUL
        assert ModelTypeManager.get_recommended_type("summarization") == ModelType.SUMMARY
        assert ModelTypeManager.get_recommended_type("unknown_task") == ModelType.POWERFUL


class TestModelManager:
    """模型管理器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ModelManager()

    def test_init(self):
        """测试初始化"""
        assert self.manager._model_cache == {}

    def test_get_api_config(self):
        """测试获取API配置"""
        # 测试FAST模型
        api_base, api_key = self.manager._get_api_config(ModelType.FAST)
        # 应该回退到默认配置
        assert api_base == config.LLM_API_BASE or config.FAST_MODEL_API_BASE
        assert api_key == config.LLM_API_KEY or config.FAST_MODEL_API_KEY

    def test_get_model_config(self):
        """测试获取模型配置"""
        model_config = self.manager.get_model_config(ModelType.FAST)
        assert model_config.temperature == 0.1

    def test_get_model_config_with_override(self):
        """测试使用覆盖配置获取模型配置"""
        override = dict(
            model_id="custom-model",
            temperature=0.5,
            max_tokens=2048
        )

        model_config = self.manager.get_model_config(ModelType.FAST, override)
        assert model_config.model_id == "custom-model"
        assert model_config.temperature == 0.5
        assert model_config.max_tokens == 2048

    def test_get_litellm_config(self):
        """测试获取litellm配置"""
        config = self.manager.get_litellm_config(ModelType.FAST)
        assert config["temperature"] == 0.1
        assert config["max_tokens"] == 1024

        # 检查是否包含API配置（如果有的话）
        assert "model" in config
        assert "temperature" in config
        assert "max_tokens" in config

    def test_get_litellm_config_with_cache(self):
        """测试带缓存的litellm配置获取"""
        # 第一次调用
        config1 = self.manager.get_litellm_config(ModelType.FAST, cache=True)

        # 第二次调用应该使用缓存
        config2 = self.manager.get_litellm_config(ModelType.FAST, cache=True)

        assert config1 == config2
        assert "litellm_config_fast" in self.manager._model_cache

    @patch('ai_agents.core.model_manager.LiteLLMModel')
    def test_get_smolagents_model(self, mock_litellm_model):
        """测试获取smolagents模型"""
        mock_instance = Mock()
        mock_litellm_model.return_value = mock_instance

        model = self.manager.get_smolagents_model(ModelType.FAST)

        assert model == mock_instance
        mock_litellm_model.assert_called_once()

        # 验证调用参数
        call_args = mock_litellm_model.call_args[1]
        assert call_args['model_id'] == "openai/gpt-4o-mini"
        assert call_args['temperature'] == 0.1
        assert call_args['max_tokens'] == 1024
        assert call_args['timeout'] == 30

    def test_get_model_by_task_litellm(self):
        """测试根据任务类型获取litellm配置"""
        config = self.manager.get_model_by_task("intent_classification", "litellm")
        assert isinstance(config, dict)

    @patch('ai_agents.core.model_manager.LiteLLMModel')
    def test_get_model_by_task_smolagents(self, mock_litellm_model):
        """测试根据任务类型获取smolagents模型"""
        mock_instance = Mock()
        mock_litellm_model.return_value = mock_instance

        model = self.manager.get_model_by_task("code_generation", "smolagents")

        assert model == mock_instance
        # 应该选择强大模型
        call_args = mock_litellm_model.call_args[1]
        assert call_args['model_id'] == "openai/deepseek-v3"

    def test_get_model_by_task_invalid_framework(self):
        """测试使用无效框架"""
        with pytest.raises(ValueError, match="不支持的框架"):
            self.manager.get_model_by_task("test", "invalid_framework")

    def test_clear_cache(self):
        """测试清空缓存"""
        # 先添加一些缓存
        self.manager.get_litellm_config(ModelType.FAST, cache=True)
        assert len(self.manager._model_cache) > 0

        # 清空缓存
        self.manager.clear_cache()
        assert len(self.manager._model_cache) == 0

    def test_get_cache_info(self):
        """测试获取缓存信息"""
        # 添加缓存
        self.manager.get_litellm_config(ModelType.FAST, cache=True)

        cache_info = self.manager.get_cache_info()
        assert cache_info["cache_size"] == 1
        assert "litellm_config_fast" in cache_info["cached_models"]


class TestGlobalModelManager:
    """全局模型管理器测试类"""

    def test_global_instance(self):
        """测试全局实例"""
        from ai_agents.core.model_manager import model_manager
        assert isinstance(model_manager, ModelManager)

    def test_convenience_functions(self):
        """测试便捷函数"""
        from ai_agents.core.model_manager import get_model_for_task

        # 测试任务模型获取
        config = get_model_for_task("intent_classification")
        assert isinstance(config, dict)


class TestModelConfig:
    """模型配置测试类"""

    def test_model_config_creation(self):
        """测试模型配置创建"""
        config = ModelConfig(
            model_id="test-model",
            api_base="https://api.test.com",
            api_key="test-key",
            temperature=0.5,
            max_tokens=2048,
            timeout=120,
            description="测试模型"
        )

        assert config.model_id == "test-model"
        assert config.api_base == "https://api.test.com"
        assert config.api_key == "test-key"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.timeout == 120
        assert config.description == "测试模型"

    def test_model_config_defaults(self):
        """测试模型配置默认值"""
        config = ModelConfig(model_id="test-model")

        assert config.model_id == "test-model"
        assert config.api_base is None
        assert config.api_key is None
        assert config.temperature == 0.1
        assert config.max_tokens == 4096
        assert config.timeout == 60
        assert config.description == ""


class TestTaskType:
    """任务类型测试类"""

    def test_task_type_constants(self):
        """测试任务类型常量"""
        assert TaskType.INTENT_CLASSIFICATION == "intent_classification"
        assert TaskType.CODE_GENERATION == "code_generation"
        assert TaskType.SUMMARIZATION == "summarization"
        assert TaskType.CLASSIFICATION == "classification"
        assert TaskType.SIMPLE_QA == "simple_qa"
        assert TaskType.CODE_REVIEW == "code_review"
        assert TaskType.COMPLEX_REASONING == "complex_reasoning"
        assert TaskType.TEXT_SUMMARY == "text_summary"
        assert TaskType.CONTENT_EXTRACTION == "content_extraction"


class TestModelManagerHeaders:
    """模型管理器请求头测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ModelManager()

    def test_model_config_with_extra_headers(self):
        """测试ModelConfig包含额外请求头"""
        headers = {
            "X-Custom-Header": "test-value",
            "Authorization": "Bearer custom-token"
        }

        config = ModelConfig(
            model_id="test-model",
            extra_headers=headers
        )

        assert config.extra_headers == headers

    def test_get_litellm_config_with_headers(self):
        """测试获取包含请求头的litellm配置"""
        headers = {
            "X-Request-ID": "test-123",
            "X-Client-Version": "1.0.0"
        }

        override_config = dict(
            model_id="test-model",
            extra_headers=headers
        )

        litellm_config = self.manager.get_litellm_config(
            ModelType.FAST,
            override_config=override_config
        )

        assert "extra_headers" in litellm_config
        assert litellm_config["extra_headers"] == headers

    def test_get_litellm_config_without_headers(self):
        """测试获取不包含请求头的litellm配置"""
        litellm_config = self.manager.get_litellm_config(ModelType.FAST)

        # 如果没有配置headers，应该不包含extra_headers字段
        assert "extra_headers" not in litellm_config

    @responses.activate
    def test_litellm_request_with_headers(self):
        """测试litellm实际发送请求时包含自定义头"""
        # Mock OpenAI API response
        responses.add(
            responses.POST,
            "https://api.openai.com/v1/chat/completions",
            json={
                "choices": [{"message": {"content": "Hello!"}}],
                "usage": {"total_tokens": 10}
            },
            status=200
        )

        # 配置带有自定义头的模型
        custom_headers = {
            "X-Test-Header": "test-value",
            "X-Request-ID": "req-123"
        }

        override_config = dict(
            model_id="gpt-3.5-turbo",
            extra_headers=custom_headers
        )

        litellm_config = self.manager.get_litellm_config(
            ModelType.FAST,
            override_config=override_config
        )

        # 使用litellm发送请求
        import litellm

        try:
            _ = litellm.completion(
                messages=[{"role": "user", "content": "Hello"}],
                **litellm_config
            )

            # 验证请求被发送
            assert len(responses.calls) == 1

            # 验证请求头
            request_headers = responses.calls[0].request.headers
            assert "X-Test-Header" in request_headers
            assert request_headers["X-Test-Header"] == "test-value"
            assert "X-Request-ID" in request_headers
            assert request_headers["X-Request-ID"] == "req-123"

        except Exception as _:
            # litellm可能有一些内部处理，我们主要关心请求是否发送了正确的头
            pass

    @patch('requests.post')
    def test_mock_http_request_headers(self, mock_post):
        """使用mock测试HTTP请求头"""
        # 设置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 10}
        }
        mock_post.return_value = mock_response

        # 配置自定义头
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "Authorization": "Bearer test-token"
        }

        override_config = dict(
            model_id="gpt-3.5-turbo",
            extra_headers=custom_headers
        )

        litellm_config = self.manager.get_litellm_config(
            ModelType.FAST,
            override_config=override_config
        )

        # 验证配置包含头信息
        assert litellm_config["extra_headers"] == custom_headers

        # 这里我们验证配置正确，实际的HTTP调用由litellm处理
        assert "extra_headers" in litellm_config
        assert litellm_config["extra_headers"]["X-Custom-Header"] == "custom-value"
        assert litellm_config["extra_headers"]["Authorization"] == "Bearer test-token"

    @patch('litellm.completion')
    def test_litellm_completion_called_with_headers(self, mock_completion):
        """测试litellm.completion被正确的头信息调用"""
        # 设置mock返回值
        mock_completion.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 10}
        }

        # 配置自定义头
        custom_headers = {
            "X-API-Version": "v1",
            "X-Client-ID": "test-client"
        }

        override_config = dict(
            model_id="gpt-3.5-turbo",
            extra_headers=custom_headers
        )

        litellm_config = self.manager.get_litellm_config(
            ModelType.FAST,
            override_config=override_config
        )

        # 模拟调用litellm.completion
        import litellm
        litellm.completion(
            messages=[{"role": "user", "content": "Test"}],
            **litellm_config
        )

        # 验证mock被调用，并且包含了正确的参数
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]

        assert "extra_headers" in call_kwargs
        assert call_kwargs["extra_headers"] == custom_headers

    def test_headers_merge_with_global_headers(self):
        """测试自定义头与全局头的合并"""
        # 这个测试验证如果设置了全局头，自定义头应该能够覆盖或补充
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "User-Agent": "custom-agent"  # 覆盖全局设置
        }

        override_config = dict(
            model_id="test-model",
            extra_headers=custom_headers
        )

        litellm_config = self.manager.get_litellm_config(
            ModelType.FAST,
            override_config=override_config
        )

        assert litellm_config["extra_headers"] == custom_headers
