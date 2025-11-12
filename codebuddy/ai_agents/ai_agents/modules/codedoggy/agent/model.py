"""
CodeDoggy 模型配置模块

提供针对 CodeDoggy 模块的模型配置功能，支持动态模型配置和 API_BASE 模板处理
"""

from typing import Optional, Dict, Any
from ai_agents.core import model_manager, TaskType
from ai_agents.core.model_types import ModelConfig
from ai_agents.modules.codedoggy.server.env import get_current_env
from smolagents import LiteLLMModel


def create_model_config_from_env(
    model_id: str,
    env_config: Optional[Dict[str, Any]] = None,
    api_base_key: str = "llmApiBase",
    api_key_key: str = "llmApiKey",
) -> LiteLLMModel:
    if env_config is None:
        env = get_current_env()
        env_config = env.get("config", {})

    # 获取API配置
    api_base_template = env_config.get(api_base_key, "")
    api_key = env_config.get(api_key_key, "")

    # 处理api_base中的{model}占位符
    api_base = api_base_template
    _model=model_id
    if api_base_template and "{model}" in api_base_template:
        _model =model_id.replace('/', '-')
        api_base = api_base_template.format(model=_model)

    model_config = ModelConfig(
        model_id=f"""openai/{_model}""",
        api_base=api_base,
        api_key=api_key,
        max_tokens=8192,
    )
    model = model_manager.get_model_by_task(
        task_type=TaskType.CODE_REVIEW,
        framework="smolagents",
        override_config=model_config,
    )
    return model
