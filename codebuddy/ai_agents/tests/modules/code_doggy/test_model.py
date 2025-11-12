"""
测试CodeDoggy模型配置模块
"""

import pytest
from unittest.mock import patch, MagicMock
from ai_agents.modules.codedoggy.agent.model import create_model_config_from_env
from ai_agents.core.model_types import ModelConfig
from ai_agents.core import TaskType
from smolagents import LiteLLMModel


class TestCreateModelConfigFromEnv:
    """测试从环境配置创建模型配置"""

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_create_config_with_model_placeholder(self, mock_get_model):
        """测试API_BASE中模型占位符的替换"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.example.com/v1/{model}/chat",
            "llmApiKey": "test_key",
        }

        result = create_model_config_from_env(
            model_id="volcengine/deepseek-v3", env_config=env_config
        )

        # 验证调用参数
        mock_get_model.assert_called_once()
        call_args = mock_get_model.call_args

        # 检查传递给 model_manager 的参数
        assert call_args.kwargs["task_type"] == TaskType.CODE_REVIEW
        assert call_args.kwargs["framework"] == "smolagents"

        override_config = call_args.kwargs["override_config"]
        assert override_config.model_id == "openai/volcengine/deepseek-v3"  # 实际格式
        assert (
            override_config.api_base
            == "https://api.example.com/v1/volcengine-deepseek-v3/chat"
        )
        assert override_config.api_key == "test_key"

        # 验证返回的是模拟的模型
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_create_config_without_placeholder(self, mock_get_model):
        """测试没有占位符的API_BASE"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.example.com/v1/chat",
            "llmApiKey": "test_key",
        }

        result = create_model_config_from_env(model_id="gpt-4o", env_config=env_config)

        # 验证调用参数
        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/gpt-4o"  # 实际格式
        assert override_config.api_base == "https://api.example.com/v1/chat"
        assert override_config.api_key == "test_key"
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_create_config_bailian_model(self, mock_get_model):
        """测试百炼模型配置"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://bailian.api.com/{model}/completions",
            "llmApiKey": "bailian_key",
        }

        result = create_model_config_from_env(
            model_id="bailian/deepseek-r1", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/bailian/deepseek-r1"  # 实际格式
        assert (
            override_config.api_base
            == "https://bailian.api.com/bailian-deepseek-r1/completions"
        )
        assert override_config.api_key == "bailian_key"
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_create_config_custom_api_keys(self, mock_get_model):
        """测试自定义API键名"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "CUSTOM_API_BASE": "https://custom.api.com/{model}",
            "CUSTOM_API_KEY": "custom_key",
        }

        result = create_model_config_from_env(
            model_id="custom/model",
            env_config=env_config,
            api_base_key="CUSTOM_API_BASE",
            api_key_key="CUSTOM_API_KEY",
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/custom/model"  # 实际格式
        assert override_config.api_base == "https://custom.api.com/custom-model"
        assert override_config.api_key == "custom_key"
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    @patch("ai_agents.modules.codedoggy.agent.model.get_current_env")
    def test_create_config_from_current_env(self, mock_get_env, mock_get_model):
        """测试从当前环境获取配置"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        mock_get_env.return_value = {
            "config": {
                "llmApiBase": "https://env.api.com/{model}",
                "llmApiKey": "env_key",
            }
        }

        result = create_model_config_from_env(model_id="volcengine/deepseek-v3")

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/volcengine/deepseek-v3"  # 实际格式
        assert override_config.api_base == "https://env.api.com/volcengine-deepseek-v3"
        assert override_config.api_key == "env_key"
        assert result == mock_model
        mock_get_env.assert_called_once()

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_create_config_openai_model(self, mock_get_model):
        """测试OpenAI模型配置"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.openai.com/v1",
            "llmApiKey": "openai_key",
        }

        result = create_model_config_from_env(model_id="gpt-4o", env_config=env_config)

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/gpt-4o"  # 实际格式
        assert override_config.api_base == "https://api.openai.com/v1"
        assert override_config.api_key == "openai_key"
        assert result == mock_model


class TestEdgeCases:
    """测试边界情况"""

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_empty_api_base(self, mock_get_model):
        """测试空的API_BASE"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {"llmApiBase": "", "llmApiKey": "test_key"}

        result = create_model_config_from_env(
            model_id="test-model", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/test-model"
        assert override_config.api_base == ""
        assert override_config.api_key == "test_key"
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_multiple_slashes_in_model_id(self, mock_get_model):
        """测试包含多个斜杠的模型ID"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.example.com/{model}/v1",
            "llmApiKey": "test_key",
        }

        result = create_model_config_from_env(
            model_id="provider/sub-provider/model-name", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/provider/sub-provider/model-name"
        assert (
            override_config.api_base
            == "https://api.example.com/provider-sub-provider-model-name/v1"
        )
        assert override_config.api_key == "test_key"
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_missing_config_keys(self, mock_get_model):
        """测试缺少配置键的情况"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {}  # 空配置

        result = create_model_config_from_env(
            model_id="test-model", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        assert override_config.model_id == "openai/test-model"
        assert override_config.api_base == ""  # 默认为空字符串
        assert override_config.api_key == ""  # 默认为空字符串
        assert result == mock_model

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_none_env_config(self, mock_get_model):
        """测试env_config为None的情况"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        with patch(
            "ai_agents.modules.codedoggy.agent.model.get_current_env"
        ) as mock_get_env:
            mock_get_env.return_value = {
                "config": {
                    "llmApiBase": "https://default.api.com/{model}",
                    "llmApiKey": "default_key",
                }
            }

            result = create_model_config_from_env(model_id="test-model")

            call_args = mock_get_model.call_args
            override_config = call_args.kwargs["override_config"]

            assert override_config.model_id == "openai/test-model"
            assert override_config.api_base == "https://default.api.com/test-model"
            assert override_config.api_key == "default_key"
            assert result == mock_model
            mock_get_env.assert_called_once()


class TestUrlTemplateProcessing:
    """测试URL模板处理"""

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_model_placeholder_replacement(self, mock_get_model):
        """测试{model}占位符替换逻辑"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        test_cases = [
            ("provider/model-name", "provider-model-name"),
            ("simple-model", "simple-model"),
            ("a/b/c", "a-b-c"),
            ("model_with_underscores", "model_with_underscores"),
        ]

        for original_model, expected_url_model in test_cases:
            env_config = {
                "llmApiBase": "https://api.example.com/{model}/endpoint",
                "llmApiKey": "test_key",
            }

            create_model_config_from_env(model_id=original_model, env_config=env_config)

            call_args = mock_get_model.call_args
            override_config = call_args.kwargs["override_config"]

            expected_api_base = f"https://api.example.com/{expected_url_model}/endpoint"
            assert override_config.api_base == expected_api_base

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_no_placeholder_no_replacement(self, mock_get_model):
        """测试没有占位符时不进行替换"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://static.api.com/endpoint",
            "llmApiKey": "test_key",
        }

        create_model_config_from_env(
            model_id="bailian/deepseek-r1", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        # 没有占位符时，API_BASE不应该被修改
        assert override_config.api_base == "https://static.api.com/endpoint"

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_placeholder_with_special_characters(self, mock_get_model):
        """测试包含特殊字符的模型ID占位符替换"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.example.com/{model}/chat",
            "llmApiKey": "test_key",
        }

        # 测试包含特殊字符的模型ID
        result = create_model_config_from_env(
            model_id="provider/model-name_v2.1", env_config=env_config
        )

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        # 只有斜杠被替换为破折号
        assert (
            override_config.api_base
            == "https://api.example.com/provider-model-name_v2.1/chat"
        )
        assert result == mock_model


class TestModelConfigCreation:
    """测试ModelConfig对象创建"""

    @patch("ai_agents.modules.codedoggy.agent.model.model_manager.get_model_by_task")
    def test_model_config_structure(self, mock_get_model):
        """测试ModelConfig对象的结构"""
        mock_model = MagicMock(spec=LiteLLMModel)
        mock_get_model.return_value = mock_model

        env_config = {
            "llmApiBase": "https://api.example.com/{model}",
            "llmApiKey": "test_key",
        }

        create_model_config_from_env(model_id="test/model", env_config=env_config)

        call_args = mock_get_model.call_args
        override_config = call_args.kwargs["override_config"]

        # 验证ModelConfig对象的类型和属性
        assert isinstance(override_config, ModelConfig)
        assert hasattr(override_config, "model_id")
        assert hasattr(override_config, "api_base")
        assert hasattr(override_config, "api_key")

        # 验证传递给model_manager的其他参数
        assert call_args.kwargs["task_type"] == TaskType.CODE_REVIEW
        assert call_args.kwargs["framework"] == "smolagents"


if __name__ == "__main__":
    pytest.main([__file__])
