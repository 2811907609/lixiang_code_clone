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
    PORTAL_BASE_URL: str = field(
        default_factory=lambda: os.getenv("PORTAL_BASE_URL", ""))
    PORTAL_TOKEN: str = field(
        default_factory=lambda: os.getenv("PORTAL_TOKEN", ""))
    LLM_API_BASE: str = field(
        default_factory=lambda: os.getenv("LLM_API_BASE", ""))
    LLM_API_KEY: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "not_provided"))
    REQUESTS_PER_MINUTE: int = field(
        default_factory=lambda: int(os.getenv("REQUESTS_PER_MINUTE", "10")))

    # 不同类型模型配置
    # 强大模型 - 用于复杂任务
    POWERFUL_MODEL: str = field(
        default_factory=lambda: os.getenv("POWERFUL_MODEL", "deepseek-v3"))
    POWERFUL_MODEL_API_BASE: str = field(
        default_factory=lambda: _get_api_config_with_fallback("POWERFUL_MODEL_API_BASE", "LLM_API_BASE"))
    POWERFUL_MODEL_API_KEY: str = field(
        default_factory=lambda: _get_api_config_with_fallback("POWERFUL_MODEL_API_KEY", "LLM_API_KEY"))
    POWERFUL_MODEL_TEMPERATURE: float = field(
        default_factory=lambda: float(os.getenv("POWERFUL_MODEL_TEMPERATURE", "0.2")))
    POWERFUL_MODEL_MAX_TOKENS: int = field(
        default_factory=lambda: int(os.getenv("POWERFUL_MODEL_MAX_TOKENS", "8192")))
    # timeout in seconds
    POWERFUL_MODEL_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("POWERFUL_MODEL_TIMEOUT", "300")))

    # 快速模型 - 用于简单任务如意图识别
    FAST_MODEL: str = field(
        default_factory=lambda: os.getenv("FAST_MODEL", "gpt-4o-mini"))
    FAST_MODEL_API_BASE: str = field(
        default_factory=lambda: _get_api_config_with_fallback("FAST_MODEL_API_BASE", "LLM_API_BASE"))
    FAST_MODEL_API_KEY: str = field(
        default_factory=lambda: _get_api_config_with_fallback("FAST_MODEL_API_KEY", "LLM_API_KEY"))
    FAST_MODEL_TEMPERATURE: float = field(
        default_factory=lambda: float(os.getenv("FAST_MODEL_TEMPERATURE", "0.1")))
    FAST_MODEL_MAX_TOKENS: int = field(
        default_factory=lambda: int(os.getenv("FAST_MODEL_MAX_TOKENS", "1024")))
    # timeout in seconds
    FAST_MODEL_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("FAST_MODEL_TIMEOUT", "60")))

    # 摘要模型 - 专门用于文本摘要
    SUMMARY_MODEL: str = field(
        default_factory=lambda: os.getenv("SUMMARY_MODEL", "gpt-4o-mini"))
    SUMMARY_MODEL_API_BASE: str = field(
        default_factory=lambda: _get_api_config_with_fallback("SUMMARY_MODEL_API_BASE", "LLM_API_BASE"))
    SUMMARY_MODEL_API_KEY: str = field(
        default_factory=lambda: _get_api_config_with_fallback("SUMMARY_MODEL_API_KEY", "LLM_API_KEY"))
    SUMMARY_MODEL_TEMPERATURE: float = field(
        default_factory=lambda: float(os.getenv("SUMMARY_MODEL_TEMPERATURE", "0.0")))
    SUMMARY_MODEL_MAX_TOKENS: int = field(
        default_factory=lambda: int(os.getenv("SUMMARY_MODEL_MAX_TOKENS", "2048")))
    # timeout in seconds
    SUMMARY_MODEL_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("SUMMARY_MODEL_TIMEOUT", "60")))

    # tracing related
    LANGFUSE_HOST = "https://liai-trace.chj.cloud"
    LANGFUSE_PUBLIC_KEY: str = field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY"))
    LANGFUSE_PRIVATE_KEY: str = field(default_factory=lambda: os.getenv("LANGFUSE_PRIVATE_KEY"))

config = Config()
