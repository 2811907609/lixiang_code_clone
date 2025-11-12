"""
模型类型定义和配置

定义不同类型的模型及其用途和配置。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ModelType(Enum):
    """模型类型枚举"""
    POWERFUL = "powerful"  # 强大模型，用于复杂任务
    FAST = "fast"          # 快速模型，用于简单任务
    SUMMARY = "summary"    # 摘要模型，专门用于文本摘要
    CUSTOM = "custom"      # 自定义模型


@dataclass
class ModelConfig:
    """模型配置"""
    model_id: str = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60 # seconds
    description: str = ""
    num_retries: int = 5
    retry_delay: float = 5.0
    max_retry_delay: float = 100.0
    extra_headers: Optional[dict] = None


class ModelTypeManager:
    """模型类型管理器"""

    @classmethod
    def _get_type_configs(cls) -> dict:
        """
        从配置中动态获取模型类型配置

        Returns:
            dict: 模型类型配置映射
        """
        from ai_agents.config import config

        return {
            ModelType.POWERFUL: ModelConfig(
                model_id=config.POWERFUL_MODEL,
                temperature=config.POWERFUL_MODEL_TEMPERATURE,
                max_tokens=config.POWERFUL_MODEL_MAX_TOKENS,
                timeout=config.POWERFUL_MODEL_TIMEOUT,
                description="强大模型，用于复杂的代码生成、分析和推理任务"
            ),
            ModelType.FAST: ModelConfig(
                model_id=config.FAST_MODEL,
                temperature=config.FAST_MODEL_TEMPERATURE,
                max_tokens=config.FAST_MODEL_MAX_TOKENS,
                timeout=config.FAST_MODEL_TIMEOUT,
                description="快速模型，用于简单的分类、意图识别等任务"
            ),
            ModelType.SUMMARY: ModelConfig(
                model_id=config.SUMMARY_MODEL,
                temperature=config.SUMMARY_MODEL_TEMPERATURE,
                max_tokens=config.SUMMARY_MODEL_MAX_TOKENS,
                timeout=config.SUMMARY_MODEL_TIMEOUT,
                description="摘要模型，专门用于文本摘要和内容提取"
            )
        }

    @classmethod
    def get_config(cls, model_type: ModelType) -> ModelConfig:
        """
        获取模型类型配置

        Args:
            model_type: 模型类型

        Returns:
            ModelConfig: 模型配置

        Raises:
            ValueError: 当模型类型不支持时
        """
        type_configs = cls._get_type_configs()
        if model_type not in type_configs:
            raise ValueError(f"不支持的模型类型: {model_type}")

        return type_configs[model_type]

    @classmethod
    def get_description(cls, model_type: ModelType) -> str:
        """
        获取模型类型描述

        Args:
            model_type: 模型类型

        Returns:
            str: 模型描述
        """
        config = cls.get_config(model_type)
        return config.description

    @classmethod
    def get_recommended_type(cls, task_type: str) -> ModelType:
        """
        根据任务类型推荐模型

        Args:
            task_type: 任务类型 (intent_classification, code_generation, summarization, etc.)

        Returns:
            ModelType: 推荐的模型类型
        """
        task_mapping = {
            "intent_classification": ModelType.FAST,
            "classification": ModelType.FAST,
            "simple_qa": ModelType.FAST,
            "code_generation": ModelType.POWERFUL,
            "code_review": ModelType.POWERFUL,
            "complex_reasoning": ModelType.POWERFUL,
            "summarization": ModelType.SUMMARY,
            "text_summary": ModelType.SUMMARY,
            "content_extraction": ModelType.SUMMARY,
        }

        return task_mapping.get(task_type.lower(), ModelType.POWERFUL)


# 任务类型常量
class TaskType:
    """任务类型常量"""
    INTENT_CLASSIFICATION = "intent_classification"
    CLASSIFICATION = "classification"
    SIMPLE_QA = "simple_qa"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    COMPLEX_REASONING = "complex_reasoning"
    SUMMARIZATION = "summarization"
    TEXT_SUMMARY = "text_summary"
    CONTENT_EXTRACTION = "content_extraction"
