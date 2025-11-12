"""
模型配置系统测试模块

测试模型配置是否正确从环境变量中读取。
"""

from ai_agents.core import ModelType, TaskType, get_model_for_task
from ai_agents.core.model_types import ModelTypeManager
from ai_agents.core.model_manager import model_manager


class TestModelConfigSystem:
    """模型配置系统测试类"""

    def test_default_config_values(self):
        """测试默认配置值"""
        # 测试强大模型默认配置
        powerful_config = model_manager.get_model_config(ModelType.POWERFUL)
        assert powerful_config.model_id == "openai/deepseek-v3"
        assert powerful_config.temperature == 0.2
        assert powerful_config.max_tokens == 8192
        assert powerful_config.timeout == 300

        # 测试快速模型默认配置
        fast_config = model_manager.get_model_config(ModelType.FAST)
        assert fast_config.model_id == "openai/gpt-4o-mini"
        assert fast_config.temperature == 0.1
        assert fast_config.max_tokens == 1024
        assert fast_config.timeout == 30

        # 测试摘要模型默认配置
        summary_config = model_manager.get_model_config(ModelType.SUMMARY)
        assert summary_config.model_id == "openai/gpt-4o-mini"
        assert summary_config.temperature == 0.0
        assert summary_config.max_tokens == 2048
        assert summary_config.timeout == 60

    def test_custom_config_from_env(self):
        """测试从环境变量读取自定义配置"""
        # 这个测试验证配置系统能够从环境变量读取配置
        # 我们通过检查当前配置是否来自环境变量来验证
        from ai_agents.config import config

        # 验证配置字段存在且类型正确
        assert hasattr(config, 'FAST_MODEL')
        assert hasattr(config, 'FAST_MODEL_TEMPERATURE')
        assert hasattr(config, 'FAST_MODEL_MAX_TOKENS')
        assert hasattr(config, 'FAST_MODEL_TIMEOUT')

        # 验证类型
        assert isinstance(config.FAST_MODEL, str)
        assert isinstance(config.FAST_MODEL_TEMPERATURE, float)
        assert isinstance(config.FAST_MODEL_MAX_TOKENS, int)
        assert isinstance(config.FAST_MODEL_TIMEOUT, int)

        # 验证配置能够被ModelTypeManager正确读取
        fast_config = ModelTypeManager.get_config(ModelType.FAST)
        assert fast_config.model_id == config.FAST_MODEL
        assert fast_config.temperature == config.FAST_MODEL_TEMPERATURE
        assert fast_config.max_tokens == config.FAST_MODEL_MAX_TOKENS
        assert fast_config.timeout == config.FAST_MODEL_TIMEOUT

    def test_litellm_config_generation(self):
        """测试litellm配置生成"""
        fast_litellm_config = model_manager.get_litellm_config(ModelType.FAST)

        # 验证必要字段存在
        required_fields = ["model", "temperature", "max_tokens"]
        for field in required_fields:
            assert field in fast_litellm_config

        # 验证值的类型
        assert isinstance(fast_litellm_config["model"], str)
        assert isinstance(fast_litellm_config["temperature"], (int, float))
        assert isinstance(fast_litellm_config["max_tokens"], int)

    def test_task_based_model_selection(self):
        """测试基于任务的模型选择"""
        # 测试意图识别任务选择快速模型
        intent_config = get_model_for_task(TaskType.INTENT_CLASSIFICATION)
        assert intent_config["model"] == "openai/gpt-4o-mini"

        # 测试代码生成任务选择强大模型
        code_config = get_model_for_task(TaskType.CODE_GENERATION)
        assert code_config["model"] == "openai/deepseek-v3"

        # 测试摘要任务选择摘要模型
        summary_config = get_model_for_task(TaskType.SUMMARIZATION)
        assert summary_config["model"] == "openai/gpt-4o-mini"

        # 测试分类任务选择快速模型
        classification_config = get_model_for_task(TaskType.CLASSIFICATION)
        assert classification_config["model"] == "openai/gpt-4o-mini"

        # 测试复杂推理任务选择强大模型
        reasoning_config = get_model_for_task(TaskType.COMPLEX_REASONING)
        assert reasoning_config["model"] == "openai/deepseek-v3"

    def test_api_config_fallback(self):
        """测试API配置回退机制"""
        # 测试模型管理器的API配置获取逻辑
        from ai_agents.core.model_manager import ModelManager

        test_manager = ModelManager()

        # 测试_get_api_config方法
        api_base, api_key = test_manager._get_api_config(ModelType.FAST)

        # 验证返回的是字符串或None
        assert api_base is None or isinstance(api_base, str)
        assert api_key is None or isinstance(api_key, str)

        # 测试litellm配置生成
        fast_config = test_manager.get_litellm_config(ModelType.FAST)

        # 验证配置结构
        assert "model" in fast_config
        assert "temperature" in fast_config
        assert "max_tokens" in fast_config

    def test_specific_model_api_config(self):
        """测试特定模型的API配置"""
        # 测试不同模型类型的API配置获取
        from ai_agents.core.model_manager import ModelManager

        test_manager = ModelManager()

        # 测试所有模型类型的API配置
        for model_type in [ModelType.FAST, ModelType.POWERFUL, ModelType.SUMMARY]:
            api_base, api_key = test_manager._get_api_config(model_type)

            # 验证返回值类型
            assert api_base is None or isinstance(api_base, str)
            assert api_key is None or isinstance(api_key, str)

            # 测试litellm配置生成
            config = test_manager.get_litellm_config(model_type)
            assert isinstance(config, dict)
            assert "model" in config

    def test_model_type_manager_dynamic_config(self):
        """测试ModelTypeManager的动态配置"""
        # 测试获取配置
        fast_config = ModelTypeManager.get_config(ModelType.FAST)
        assert fast_config.model_id == "openai/gpt-4o-mini"

        # 测试获取描述
        fast_desc = ModelTypeManager.get_description(ModelType.FAST)
        assert "快速模型" in fast_desc

        # 测试推荐类型
        recommended = ModelTypeManager.get_recommended_type("intent_classification")
        assert recommended == ModelType.FAST

    def test_config_parameter_types(self):
        """测试配置参数类型"""
        from ai_agents.config import config

        # 测试温度参数是float类型
        assert isinstance(config.FAST_MODEL_TEMPERATURE, float)
        assert isinstance(config.POWERFUL_MODEL_TEMPERATURE, float)
        assert isinstance(config.SUMMARY_MODEL_TEMPERATURE, float)

        # 测试max_tokens是int类型
        assert isinstance(config.FAST_MODEL_MAX_TOKENS, int)
        assert isinstance(config.POWERFUL_MODEL_MAX_TOKENS, int)
        assert isinstance(config.SUMMARY_MODEL_MAX_TOKENS, int)

        # 测试timeout是int类型
        assert isinstance(config.FAST_MODEL_TIMEOUT, int)
        assert isinstance(config.POWERFUL_MODEL_TIMEOUT, int)
        assert isinstance(config.SUMMARY_MODEL_TIMEOUT, int)

    def test_config_value_ranges(self):
        """测试配置值的合理范围"""
        from ai_agents.config import config

        # 测试温度值在合理范围内
        assert 0.0 <= config.FAST_MODEL_TEMPERATURE <= 1.0
        assert 0.0 <= config.POWERFUL_MODEL_TEMPERATURE <= 1.0
        assert 0.0 <= config.SUMMARY_MODEL_TEMPERATURE <= 1.0

        # 测试max_tokens为正数
        assert config.FAST_MODEL_MAX_TOKENS > 0
        assert config.POWERFUL_MODEL_MAX_TOKENS > 0
        assert config.SUMMARY_MODEL_MAX_TOKENS > 0

        # 测试timeout为正数
        assert config.FAST_MODEL_TIMEOUT > 0
        assert config.POWERFUL_MODEL_TIMEOUT > 0
        assert config.SUMMARY_MODEL_TIMEOUT > 0

    def test_model_cache_behavior(self):
        """测试模型缓存行为"""
        # 清空缓存
        model_manager.clear_cache()

        # 第一次获取配置
        config1 = model_manager.get_litellm_config(ModelType.FAST, cache=True)

        # 第二次获取应该使用缓存
        config2 = model_manager.get_litellm_config(ModelType.FAST, cache=True)

        # 应该是同一个对象（缓存命中）
        assert config1 is config2

        # 验证缓存信息
        cache_info = model_manager.get_cache_info()
        assert cache_info["cache_size"] > 0
        assert "litellm_config_fast" in cache_info["cached_models"]

        # 清空缓存后应该重新生成
        model_manager.clear_cache()
        config3 = model_manager.get_litellm_config(ModelType.FAST, cache=True)

        # 内容应该相同但不是同一个对象
        assert config1 == config3
        assert config1 is not config3


class TestModelConfigIntegration:
    """模型配置集成测试"""

    def test_intent_classifier_with_config_system(self):
        """测试意图识别器与配置系统的集成"""
        from ai_agents.llmtools import IntentClassifier

        # 使用模型管理器的分类器
        classifier = IntentClassifier(use_model_manager=True)

        # 应该使用快速模型
        assert classifier.model == "openai/gpt-4o-mini"
        assert "model" in classifier.litellm_config
        assert "temperature" in classifier.litellm_config
        assert "max_tokens" in classifier.litellm_config

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试从llmtools导入仍然有效
        from ai_agents.llmtools import ModelType, TaskType, get_model_for_task

        # 功能应该正常工作
        config = get_model_for_task(TaskType.INTENT_CLASSIFICATION)
        assert config["model"] == "openai/gpt-4o-mini"

        # 测试从core导入也有效
        from ai_agents.core import ModelType as CoreModelType
        assert ModelType.FAST == CoreModelType.FAST
