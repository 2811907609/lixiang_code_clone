"""
简单的配置回退机制测试

测试配置回退函数本身的逻辑，不依赖于模块重载。
"""

import os
from unittest.mock import patch

from ai_agents.config import _get_api_config_with_fallback


class TestConfigFallbackFunction:
    """配置回退函数测试类"""

    def test_specific_config_exists(self):
        """测试特定配置存在时的行为"""
        with patch.dict(os.environ, {
            'SPECIFIC_VAR': 'specific_value',
            'FALLBACK_VAR': 'fallback_value'
        }):
            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR', 'default_value')
            assert result == 'specific_value'

    def test_fallback_to_common_config(self):
        """测试回退到通用配置"""
        with patch.dict(os.environ, {
            'FALLBACK_VAR': 'fallback_value'
        }, clear=True):
            # 确保特定变量不存在
            os.environ.pop('SPECIFIC_VAR', None)

            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR', 'default_value')
            assert result == 'fallback_value'

    def test_fallback_to_default(self):
        """测试回退到默认值"""
        with patch.dict(os.environ, {}, clear=True):
            # 确保两个变量都不存在
            os.environ.pop('SPECIFIC_VAR', None)
            os.environ.pop('FALLBACK_VAR', None)

            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR', 'default_value')
            assert result == 'default_value'

    def test_empty_specific_config_fallback(self):
        """测试特定配置为空时的回退"""
        with patch.dict(os.environ, {
            'SPECIFIC_VAR': '',  # 空字符串
            'FALLBACK_VAR': 'fallback_value'
        }):
            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR', 'default_value')
            assert result == 'fallback_value'

    def test_empty_fallback_config(self):
        """测试回退配置也为空时的行为"""
        with patch.dict(os.environ, {
            'FALLBACK_VAR': ''  # 空字符串
        }, clear=True):
            # 确保特定变量不存在
            os.environ.pop('SPECIFIC_VAR', None)

            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR', 'default_value')
            assert result == 'default_value'

    def test_no_default_value(self):
        """测试没有默认值的情况"""
        with patch.dict(os.environ, {}, clear=True):
            # 确保两个变量都不存在
            os.environ.pop('SPECIFIC_VAR', None)
            os.environ.pop('FALLBACK_VAR', None)

            result = _get_api_config_with_fallback('SPECIFIC_VAR', 'FALLBACK_VAR')
            assert result == ""


class TestCurrentConfigBehavior:
    """测试当前配置的行为"""

    def test_current_config_structure(self):
        """测试当前配置结构"""
        from ai_agents.config import config

        # 验证所有必要的配置字段都存在
        required_fields = [
            'LLM_API_BASE', 'LLM_API_KEY',
            'FAST_MODEL', 'FAST_MODEL_API_BASE', 'FAST_MODEL_API_KEY',
            'FAST_MODEL_TEMPERATURE', 'FAST_MODEL_MAX_TOKENS', 'FAST_MODEL_TIMEOUT',
            'POWERFUL_MODEL', 'POWERFUL_MODEL_API_BASE', 'POWERFUL_MODEL_API_KEY',
            'POWERFUL_MODEL_TEMPERATURE', 'POWERFUL_MODEL_MAX_TOKENS', 'POWERFUL_MODEL_TIMEOUT',
            'SUMMARY_MODEL', 'SUMMARY_MODEL_API_BASE', 'SUMMARY_MODEL_API_KEY',
            'SUMMARY_MODEL_TEMPERATURE', 'SUMMARY_MODEL_MAX_TOKENS', 'SUMMARY_MODEL_TIMEOUT'
        ]

        for field in required_fields:
            assert hasattr(config, field), f"配置缺少字段: {field}"

    def test_config_types(self):
        """测试配置字段的类型"""
        from ai_agents.config import config

        # 字符串字段
        string_fields = [
            'LLM_API_BASE', 'LLM_API_KEY',
            'FAST_MODEL', 'FAST_MODEL_API_BASE', 'FAST_MODEL_API_KEY',
            'POWERFUL_MODEL', 'POWERFUL_MODEL_API_BASE', 'POWERFUL_MODEL_API_KEY',
            'SUMMARY_MODEL', 'SUMMARY_MODEL_API_BASE', 'SUMMARY_MODEL_API_KEY'
        ]

        for field in string_fields:
            value = getattr(config, field)
            assert isinstance(value, str), f"字段 {field} 应该是字符串类型，实际是 {type(value)}"

        # 浮点数字段
        float_fields = [
            'FAST_MODEL_TEMPERATURE', 'POWERFUL_MODEL_TEMPERATURE', 'SUMMARY_MODEL_TEMPERATURE'
        ]

        for field in float_fields:
            value = getattr(config, field)
            assert isinstance(value, float), f"字段 {field} 应该是浮点数类型，实际是 {type(value)}"

        # 整数字段
        int_fields = [
            'FAST_MODEL_MAX_TOKENS', 'FAST_MODEL_TIMEOUT',
            'POWERFUL_MODEL_MAX_TOKENS', 'POWERFUL_MODEL_TIMEOUT',
            'SUMMARY_MODEL_MAX_TOKENS', 'SUMMARY_MODEL_TIMEOUT'
        ]

        for field in int_fields:
            value = getattr(config, field)
            assert isinstance(value, int), f"字段 {field} 应该是整数类型，实际是 {type(value)}"

    def test_model_manager_basic_functionality(self):
        """测试模型管理器基本功能"""
        from ai_agents.core import model_manager, ModelType

        # 测试获取配置不会出错
        for model_type in [ModelType.FAST, ModelType.POWERFUL, ModelType.SUMMARY]:
            config = model_manager.get_model_config(model_type)
            assert config.model_id is not None
            assert isinstance(config.temperature, (int, float))
            assert isinstance(config.max_tokens, int)
            assert isinstance(config.timeout, int)

            # 测试获取litellm配置
            litellm_config = model_manager.get_litellm_config(model_type)
            assert isinstance(litellm_config, dict)
            assert 'model' in litellm_config
            assert 'temperature' in litellm_config
            assert 'max_tokens' in litellm_config

    def test_intent_classifier_basic_functionality(self):
        """测试意图识别器基本功能"""
        from ai_agents.llmtools import IntentClassifier

        # 测试创建分类器不会出错
        classifier = IntentClassifier(use_model_manager=True)

        # 验证基本属性
        assert classifier.model is not None
        assert isinstance(classifier.litellm_config, dict)
        assert 'model' in classifier.litellm_config
        assert 'temperature' in classifier.litellm_config
        assert 'max_tokens' in classifier.litellm_config
        assert classifier.confidence_threshold > 0
        assert classifier.use_model_manager is True
