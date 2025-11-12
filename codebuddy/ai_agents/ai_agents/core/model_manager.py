"""
模型管理器

统一管理不同类型的模型，提供模型选择和配置功能。
"""

import logging
from dataclasses import replace
from typing import Optional, Union

import litellm

from ai_agents.config import config
from ai_agents.lib.litellm_retry import patch_litellm_completion
from ai_agents.lib.smolagents import LiteLLMModelV2

from .model_types import ModelConfig, ModelType, ModelTypeManager

logger = logging.getLogger(__name__)


class ModelManager:
    """
    模型管理器

    负责管理不同类型的模型，提供统一的模型获取接口。
    """

    def __init__(self):
        """初始化模型管理器"""
        self._model_cache = {}

        # 配置 litellm 全局重试设置
        self._configure_litellm_retry()

        logger.info("初始化模型管理器")

    def _configure_litellm_retry(self):
        """配置 litellm 的重试机制"""

        # 应用自定义重试包装器
        patch_litellm_completion(litellm)

        # 配置全局请求头（可选）
        litellm.default_headers = {
            "User-Agent": "ai-agents/1.0",
        }

        logger.info("已配置 litellm 重试机制: 使用 tenacity 实现指数退避")

    def get_model_config(
        self,
        model_type: ModelType,
        override_config: dict = None
    ) -> ModelConfig:
        """
        获取模型配置

        Args:
            model_type: 模型类型
            override_config: 覆盖配置

        Returns:
            ModelConfig: 完整的模型配置
        """
        # 获取基础配置
        base_config = ModelTypeManager.get_config(model_type)

        # 从环境变量获取API配置
        api_base, api_key = self._get_api_config(model_type)

        # 更新配置
        final_config = replace(
            base_config,
            api_base=api_base or base_config.api_base,
            api_key=api_key or base_config.api_key
        )

        # 应用覆盖配置
        if override_config:
            # 特殊处理：对于extra_headers，我们需要保留空字典，但过滤掉None
            override_dict = {}
            for k, v in override_config.items():
                if k == 'extra_headers':
                    # 对于extra_headers，只过滤None，保留空字典
                    if v is not None:
                        override_dict[k] = v
                else:
                    # 对于其他字段，过滤掉None值
                    if v is not None:
                        override_dict[k] = v

            final_config = replace(final_config, **override_dict)

        return final_config

    def _get_api_config(self, model_type: ModelType) -> tuple[Optional[str], Optional[str]]:
        """
        从配置中获取API配置

        Args:
            model_type: 模型类型

        Returns:
            tuple[Optional[str], Optional[str]]: (api_base, api_key)
        """
        # 定义模型类型到配置属性的映射
        config_mapping = {
            ModelType.POWERFUL: {
                'api_base': config.POWERFUL_MODEL_API_BASE,
                'api_key': config.POWERFUL_MODEL_API_KEY
            },
            ModelType.FAST: {
                'api_base': config.FAST_MODEL_API_BASE,
                'api_key': config.FAST_MODEL_API_KEY
            },
            ModelType.SUMMARY: {
                'api_base': config.SUMMARY_MODEL_API_BASE,
                'api_key': config.SUMMARY_MODEL_API_KEY
            }
        }

        # 获取特定模型类型的配置（配置本身已经处理了回退逻辑）
        model_config = config_mapping.get(model_type, {})
        api_base = model_config.get('api_base') or None
        api_key = model_config.get('api_key') or None

        return api_base, api_key

    def get_litellm_config(
        self,
        model_type: ModelType,
        override_config: dict = None,
        cache: bool = True
    ) -> dict:
        """
        获取用于litellm.completion的配置参数

        Args:
            model_type: 模型类型
            override_config: 覆盖配置
            cache: 是否使用缓存

        Returns:
            dict: litellm.completion的配置参数
        """
        cache_key = f"litellm_config_{model_type.value}"

        if cache and cache_key in self._model_cache:
            return self._model_cache[cache_key]

        model_config = self.get_model_config(model_type, override_config)

        # 构建litellm.completion的参数
        # ！这里如果添加参数需要查看是否是litellm所支持的参数，如果非支持参数会透传到调用llm的api中，
        # 当前anthropic的api如果存在不能接受参数会直接异常。
        # 这里重试相关参数 retry_delay 、max_retry_delay 非litellm支持参数，在retry中进行处理pop，不会向后透传
        litellm_params = {
            "model": model_config.model_id,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            # 添加重试相关参数
            "num_retries": model_config.num_retries,
            "retry_delay": model_config.retry_delay,
            "max_retry_delay": model_config.max_retry_delay,
            "timeout": model_config.timeout or 60.0,
        }

        # 添加自定义请求头（如果配置了的话）
        if model_config.extra_headers is not None:
            litellm_params["extra_headers"] = model_config.extra_headers

        # 只有在配置了API参数时才添加
        if model_config.api_base:
            litellm_params["api_base"] = model_config.api_base
        if model_config.api_key:
            litellm_params["api_key"] = model_config.api_key

        if cache:
            self._model_cache[cache_key] = litellm_params

        logger.debug(f"获取litellm配置: {model_type.value} -> {model_config.model_id}")
        return litellm_params

    def get_smolagents_model(
        self,
        model_type: ModelType,
        override_config: dict = None,
        cache: bool = True
    ) -> LiteLLMModelV2:
        """
        获取用于smolagents的模型实例

        Args:
            model_type: 模型类型
            override_config: 覆盖配置
            cache: 是否使用缓存

        Returns:
            LiteLLMModelV2: smolagents模型实例
        """
        cache_key = f"smolagents_{model_type.value}"

        if cache and cache_key in self._model_cache:
            return self._model_cache[cache_key]

        model_config = self.get_model_config(model_type, override_config)
        logging.info(f"获取smolagents模型: model_config={model_config}")


        # 创建smolagents模型，包含重试配置
        # ！这里如果添加参数需要查看是否是litellm所支持的参数，如果非支持参数会透传到调用llm的api中，
        # 当前anthropic的api如果存在不能接受参数会直接异常。
        # 这里重试相关参数 retry_delay 、max_retry_delay 非litellm支持参数，在retry中进行处理pop，不会向后透传
        model = LiteLLMModelV2(
            model_id=model_config.model_id,
            api_base=model_config.api_base,
            api_key=model_config.api_key,
            timeout=model_config.timeout or 30.0,
            max_tokens=model_config.max_tokens,
            temperature=model_config.temperature,
            requests_per_minute=config.REQUESTS_PER_MINUTE or 10,
            # 添加重试相关参数
            num_retries=model_config.num_retries,
            retry_delay=model_config.retry_delay,
            max_retry_delay=model_config.max_retry_delay,
            extra_headers=model_config.extra_headers,
        )

        if cache:
            self._model_cache[cache_key] = model

        logger.debug(f"获取smolagents模型: {model_type.value} -> {model_config.model_id}")
        return model

    def get_model_by_task(
        self,
        task_type: str,
        framework: str = "litellm",
        override_config: dict = None,
        cache: bool = True
    ) -> Union[dict, LiteLLMModelV2]:
        """
        根据任务类型自动选择合适的模型

        Args:
            task_type: 任务类型
            framework: 使用的框架 ("litellm" 或 "smolagents")
            override_config: 覆盖配置
            cache: 是否使用缓存

        Returns:
            Union[dict, LiteLLMModelV2]: litellm配置字典或smolagents模型实例
        """
        recommended_type = ModelTypeManager.get_recommended_type(task_type)

        logger.info(f"任务 '{task_type}' 推荐使用模型类型: {recommended_type.value}")
        if framework.lower() == "litellm":
            return self.get_litellm_config(recommended_type, override_config, cache)
        elif framework.lower() == "smolagents":
            return self.get_smolagents_model(recommended_type, override_config, cache)
        else:
            raise ValueError(f"不支持的框架: {framework}")

    def clear_cache(self):
        """清空模型缓存"""
        self._model_cache.clear()
        logger.info("已清空模型缓存")

    def get_cache_info(self) -> dict:
        """
        获取缓存信息

        Returns:
            dict: 缓存信息
        """
        return {
            "cached_models": list(self._model_cache.keys()),
            "cache_size": len(self._model_cache)
        }

# 全局模型管理器实例
model_manager = ModelManager()


def get_model_for_task(
    task_type: str,
    framework: str = "litellm",
    override_config: dict = None,
    model_cache : bool = True
) -> Union[dict, LiteLLMModelV2]:
    """
    便捷函数：根据任务类型获取模型

    Args:
        task_type: 任务类型
        framework: 使用的框架
        override_config: 覆盖配置

    Returns:
        Union[dict, LiteLLMModelV2]: litellm配置字典或smolagents模型实例
    """
    return model_manager.get_model_by_task(task_type, framework, override_config, model_cache)
