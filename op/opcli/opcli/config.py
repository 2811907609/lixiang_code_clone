"""
配置模块 - 管理飞书项目相关配置
"""

import os
from dataclasses import dataclass, field


def _get_api_config_with_fallback(specific_env_var: str, fallback_env_var: str, default: str = "") -> str:
    """
    获取API配置，支持回退机制

    Args:
        specific_env_var: 特定的环境变量名
        fallback_env_var: 回退的环境变量名
        default: 默认值

    Returns:
        str: 配置值
    """
    # 首先尝试获取特定的环境变量
    specific_value = os.getenv(specific_env_var)
    if specific_value:
        return specific_value

    # 如果特定环境变量不存在或为空，回退到通用环境变量
    fallback_value = os.getenv(fallback_env_var)
    if fallback_value:
        return fallback_value

    # 如果都没有，返回默认值
    return default


@dataclass
class Config:
    # 飞书相关配置
    FEISHU_APP_ID: str = field(
        default_factory=lambda: os.getenv("FEISHU_APP_ID", ""))
    FEISHU_APP_SECRET: str = field(
        default_factory=lambda: os.getenv("FEISHU_APP_SECRET", ""))

    # 飞书日志级别
    FEISHU_LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("FEISHU_LOG_LEVEL", "DEBUG"))

    # 飞书超时配置
    FEISHU_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("FEISHU_TIMEOUT", "30")))

    # 其他可能的IM平台配置（为扩展预留）
    SLACK_BOT_TOKEN: str = field(
        default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    SLACK_SIGNING_SECRET: str = field(
        default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", ""))


# 创建全局配置实例
config = Config()
