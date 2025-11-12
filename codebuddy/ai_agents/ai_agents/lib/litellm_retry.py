"""
litellm 自定义重试机制

为 litellm.completion 添加指数退避重试逻辑，支持自定义 retry_delay 和 max_retry_delay 参数。
"""

import logging
from functools import wraps
from typing import Any, Callable

from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)



def is_retryable_litellm_error(exception: Exception) -> bool:
    """
    判断是否为 litellm 可重试的错误类型

    使用 litellm 原生的异常类型判断，覆盖 model_manager 中 retry_policy 配置的所有错误类型：
    - timeout -> Timeout
    - rate_limit -> RateLimitError
    - connection_error -> APIConnectionError
    - server_error / internal_server_error -> InternalServerError
    - service_unavailable -> ServiceUnavailableError
    - authentication_error -> AuthenticationError
    - authorization_error -> PermissionDeniedError
    - bad_gateway / gateway_timeout -> status_code 502/504

    参考：
    https://github.com/BerriAI/litellm/blob/main/litellm/router_utils/get_retry_from_policy.py

    Args:
        exception: 异常对象

    Returns:
        bool: 是否应该重试
    """
    # 使用 isinstance 检查 litellm 的异常类型
    # 这是 litellm 官方的判断方式
    if isinstance(exception, (
        Timeout,                  # timeout
        RateLimitError,           # rate_limit
        APIConnectionError,       # connection_error
        InternalServerError,      # server_error, internal_server_error
        ServiceUnavailableError,  # service_unavailable
        AuthenticationError,      # authentication_error
        PermissionDeniedError,    # authorization_error
    )):
        return True

    # 检查 status_code (对于其他可能的错误)
    status_code = getattr(exception, "status_code", None)
    if status_code:
        # 基于 litellm._should_retry 的逻辑
        # https://github.com/BerriAI/litellm/blob/main/litellm/utils.py
        if status_code in [408, 409, 429] or status_code >= 500:
            return True

    return False


def create_retry_wrapper(
    original_func: Callable,
    default_num_retries: int = 3,
    default_retry_delay: float = 1.0,
    default_max_retry_delay: float = 60.0,
) -> Callable:
    """
    创建带重试逻辑的包装函数

    Args:
        original_func: 原始函数（litellm.completion）
        default_num_retries: 默认最大重试次数
        default_retry_delay: 默认初始重试延迟（秒）
        default_max_retry_delay: 默认最大重试延迟（秒）

    Returns:
        Callable: 包装后的函数
    """

    @wraps(original_func)
    def wrapper(*args, **kwargs):
        # 从 kwargs 中提取自定义重试参数（并移除，避免传给 litellm）
        retry_delay = kwargs.pop("retry_delay", default_retry_delay)
        max_retry_delay = kwargs.pop("max_retry_delay", default_max_retry_delay)
        num_retries = kwargs.pop("num_retries", default_num_retries)

        logger.info(
            f"[调试] 重试参数: num_retries={num_retries}, "
            f"retry_delay={retry_delay}, max_retry_delay={max_retry_delay}"
        )

        # 如果没有配置重试参数，直接调用原函数
        if retry_delay is None or num_retries == 0:
            return original_func(*args, **kwargs)

        # 禁用 litellm 自己的重试机制，避免双重重试
        # 我们的 tenacity 重试已经处理了所有重试逻辑
        kwargs["num_retries"] = 0

        # 使用 tenacity 构建重试装饰器
        retry_decorator = retry(
            stop=stop_after_attempt(num_retries),
            wait=wait_exponential(
                multiplier=retry_delay,
                max=max_retry_delay,
            ),
            retry=retry_if_exception(is_retryable_litellm_error),
            reraise=True,
            before_sleep=lambda retry_state: _log_retry_attempt(retry_state, num_retries),
        )

        # 创建可重试的函数
        retryable_func = retry_decorator(original_func)

        # 执行
        return retryable_func(*args, **kwargs)

    return wrapper


def _log_retry_attempt(retry_state: RetryCallState, max_retries: int):
    """
    记录重试日志

    Args:
        retry_state: tenacity 的重试状态
        max_retries: 最大重试次数
    """
    attempt = retry_state.attempt_number
    exception = retry_state.outcome.exception()
    next_sleep = retry_state.next_action.sleep if retry_state.next_action else 0

    logger.warning(
        f"litellm.completion 调用失败 (尝试 {attempt}/{max_retries}): "
        f"{type(exception).__name__}: {exception}. "
        f"将在 {next_sleep:.2f}秒 后重试"
    )


def patch_litellm_completion(litellm_module: Any):
    """
    对 litellm.completion 进行 monkey patch，添加自定义重试逻辑

    Args:
        litellm_module: litellm 模块对象
    """
    # 检查是否已经 patch 过（避免重复 patch）
    if hasattr(litellm_module.completion, "_ai_agents_retry_patched"):
        logger.debug("litellm.completion 已经被 patch，跳过重复 patch")
        return

    original_completion = litellm_module.completion

    # 创建包装函数
    wrapped_completion = create_retry_wrapper(
        original_completion
    )

    # 标记已经 patch 过
    wrapped_completion._ai_agents_retry_patched = True

    # 替换
    litellm_module.completion = wrapped_completion

    logger.info(
        "已为 litellm.completion 添加自定义重试机制 "
        "(支持 retry_delay 和 max_retry_delay 参数)"
    )
