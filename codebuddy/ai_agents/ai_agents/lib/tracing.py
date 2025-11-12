import base64
import logging
import os
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional, Generator

import litellm

from ai_agents.config import config

logger = logging.getLogger(__name__)

# Context variables to store the current task/session ID and sub-task info
_current_task_id: ContextVar[Optional[str]] = ContextVar('current_task_id', default=None)
_current_sub_task_id: ContextVar[Optional[str]] = ContextVar('current_sub_task_id', default=None)
_current_agent_id: ContextVar[Optional[str]] = ContextVar('current_agent_id', default=None)

def generate_task_id(custom_name: str = None) -> str:
    """生成唯一的任务ID"""
    if custom_name:
        return f"task_{custom_name}_{uuid.uuid4().hex[:12]}"
    return f"task_{uuid.uuid4().hex[:12]}"



def generate_sub_task_id(agent_name: str) -> str:
    """生成子任务ID"""
    return f"sub_{agent_name}_{uuid.uuid4().hex[:8]}"


def set_current_task_id(task_id: str) -> None:
    """设置当前任务ID"""
    _current_task_id.set(task_id)
    logger.debug(f"设置任务ID: {task_id}")


def get_current_task_id() -> Optional[str]:
    """获取当前任务ID"""
    return _current_task_id.get()


def clear_current_task_id() -> None:
    """清除当前任务ID"""
    _current_task_id.set(None)
    logger.debug("清除任务ID")


def set_current_sub_task_id(sub_task_id: str) -> None:
    """设置当前子任务ID"""
    _current_sub_task_id.set(sub_task_id)
    logger.debug(f"设置子任务ID: {sub_task_id}")


def get_current_sub_task_id() -> Optional[str]:
    """获取当前子任务ID"""
    return _current_sub_task_id.get()


def clear_current_sub_task_id() -> None:
    """清除当前子任务ID"""
    _current_sub_task_id.set(None)
    logger.debug("清除子任务ID")


def set_current_agent_id(agent_id: str) -> None:
    """设置当前智能体ID"""
    _current_agent_id.set(agent_id)
    logger.debug(f"设置智能体ID: {agent_id}")


def get_current_agent_id() -> Optional[str]:
    """获取当前智能体ID"""
    return _current_agent_id.get()


def clear_current_agent_id() -> None:
    """清除当前智能体ID"""
    _current_agent_id.set(None)
    logger.debug("清除智能体ID")


@contextmanager
def task_context(task_id: Optional[str] = None) -> Generator[str, None, None]:
    """
    任务上下文管理器，自动管理任务ID的生命周期

    Args:
        task_id: 可选的任务ID，如果不提供则自动生成

    Yields:
        str: 当前任务ID

    Example:
        with task_context() as task_id:
            # 在此上下文中的所有LLM调用都会包含这个task_id
            result = agent.run("some task")
    """
    if task_id is None:
        task_id = generate_task_id()

    # 保存之前的任务ID
    previous_task_id = get_current_task_id()

    try:
        # 设置新的任务ID
        set_current_task_id(task_id)
        yield task_id
    finally:
        # 恢复之前的任务ID
        if previous_task_id is not None:
            set_current_task_id(previous_task_id)
        else:
            clear_current_task_id()


@contextmanager
def sub_task_context(agent_name: str, sub_task_id: Optional[str] = None) -> Generator[str, None, None]:
    """
    子任务上下文管理器，为micro agent创建独立的追踪链路

    Args:
        agent_name: 智能体名称
        sub_task_id: 可选的子任务ID，如果不提供则自动生成

    Yields:
        str: 当前子任务ID

    Example:
        with sub_task_context("search_agent") as sub_task_id:
            # 在此上下文中的所有LLM调用都会包含子任务信息
            result = micro_agent.run("some sub task")
    """
    if sub_task_id is None:
        sub_task_id = generate_sub_task_id(agent_name)

    # 保存之前的状态
    previous_sub_task_id = get_current_sub_task_id()
    previous_agent_id = get_current_agent_id()

    try:
        # 设置新的子任务和智能体ID
        set_current_sub_task_id(sub_task_id)
        set_current_agent_id(agent_name)
        yield sub_task_id
    finally:
        # 恢复之前的状态
        if previous_sub_task_id is not None:
            set_current_sub_task_id(previous_sub_task_id)
        else:
            clear_current_sub_task_id()

        if previous_agent_id is not None:
            set_current_agent_id(previous_agent_id)
        else:
            clear_current_agent_id()


def langfuse_configured():
    return config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_PRIVATE_KEY

def litellm_tracing():
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]

    # 设置预处理回调来注入任务ID
    _setup_task_id_injection()

def enable_litellm_tracing():
    public_key = config.LANGFUSE_PUBLIC_KEY
    private_key = config.LANGFUSE_PRIVATE_KEY
    host = config.LANGFUSE_HOST

    os.environ["LANGFUSE_HOST"] = host
    os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    os.environ["LANGFUSE_SECRET_KEY"] = private_key
    litellm_tracing()


def _setup_task_id_injection():
    """设置litellm的预处理回调来自动注入任务ID和子任务信息"""
    original_completion = litellm.completion

    def completion_with_task_id(*args, **kwargs):
        # 获取当前追踪信息
        task_id = get_current_task_id()
        sub_task_id = get_current_sub_task_id()
        agent_id = get_current_agent_id()

        if task_id:
            # 注入追踪信息到metadata中
            if 'metadata' not in kwargs:
                kwargs['metadata'] = {}

            # 添加主任务ID
            kwargs['metadata']['task_id'] = task_id
            kwargs['metadata']['session_id'] = task_id  # 同时作为session_id

            # 添加子任务信息（如果存在）
            if sub_task_id:
                kwargs['metadata']['sub_task_id'] = sub_task_id
                kwargs['metadata']['trace_id'] = f"{task_id}.{sub_task_id}"  # 层次化trace_id

            # 添加智能体信息（如果存在）
            if agent_id:
                kwargs['metadata']['agent_id'] = agent_id
                kwargs['metadata']['user_id'] = agent_id  # 也可以作为user_id用于区分

            # 构建完整的追踪链路标识
            trace_chain = [task_id]
            if sub_task_id:
                trace_chain.append(sub_task_id)
            if agent_id:
                trace_chain.append(agent_id)
            kwargs['metadata']['trace_chain'] = ".".join(trace_chain)

            logger.debug(f"注入追踪信息到LLM调用: {kwargs['metadata']}")

        return original_completion(*args, **kwargs)

    # 替换litellm.completion函数
    litellm.completion = completion_with_task_id


def try_enable_litellm_tracing():
    if not langfuse_configured():
        print("Langfuse tracing is not configured, skipping.")
        return

    print("Enabling Langfuse tracing for litellm.")
    enable_litellm_tracing()


def enable_smolagents_tracing():
    public_key = config.LANGFUSE_PUBLIC_KEY
    private_key = config.LANGFUSE_PRIVATE_KEY
    host = config.LANGFUSE_HOST
    langfuse_auth = base64.b64encode(
        f'{public_key}:{private_key}'.encode()).decode()

    os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = f'{host}/api/public/otel'
    os.environ['OTEL_EXPORTER_OTLP_HEADERS'] = f'Authorization=Bearer {langfuse_auth}'


    from opentelemetry.sdk.trace import TracerProvider

    from openinference.instrumentation.smolagents import SmolagentsInstrumentor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))

    SmolagentsInstrumentor().instrument(tracer_provider=trace_provider)


# we don't enable it now, since our tracing platform don't support it atm.
def try_enable_tracing():
    if not langfuse_configured():
        logger.info("Langfuse tracing is not configured, skipping.")
        return

    enable_smolagents_tracing()



try_enable_litellm_tracing()
