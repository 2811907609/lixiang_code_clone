"""
LLM工具模块

提供各种基于大语言模型的工具和功能。
"""

from .intent_classifier import IntentClassifier

# 为了向后兼容，重新导出核心模块的内容
from ai_agents.core import (
    ModelManager, model_manager,
    get_model_for_task,
    ModelType, ModelConfig, TaskType
)

__all__ = [
    'IntentClassifier',
    # 核心模块重新导出（向后兼容）
    'ModelManager', 'model_manager',
    'get_model_for_task',
    'ModelType', 'ModelConfig', 'TaskType'
]
