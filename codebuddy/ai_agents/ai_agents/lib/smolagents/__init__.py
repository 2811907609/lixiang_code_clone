
import logging
from pathlib import Path
from typing import Union

import yaml
from smolagents import CodeAgent, ToolCallingAgent, AgentLogger, LogLevel, Tool  # noqa: F401
from ai_agents.lib.rich_console import Console, DualConsole
from .models import LiteLLMModelV2  # noqa: F401
from ai_agents.lib.smolagents.logger.time_enhanced_logger import TimeEnhancedAgentLogger

logger = logging.getLogger(__name__)

_parent_dir = Path(__file__).parent
_prompt_dir = _parent_dir / "prompts"
_code_agent_prompt_path = _prompt_dir / "code_agent.yaml"

class CodeAgentV2(CodeAgent):
    def __init__(self, *args, before_run_callbacks: list = None, **kwargs):
        self._before_run_callbacks = before_run_callbacks or []
        super().__init__(*args, **kwargs)

    def run(self, task: str, *args, **kwargs):
        for callback in self._before_run_callbacks:
            callback(self, task, *args, **kwargs)
        return super().run(task, *args, **kwargs)


class ToolCallingAgentV2(ToolCallingAgent):
    def __init__(self, *args, before_run_callbacks: list = None, **kwargs):
        self._before_run_callbacks = before_run_callbacks or []
        super().__init__(*args, **kwargs)

    def run(self, task: str, *args, **kwargs):
        for callback in self._before_run_callbacks:
            task = callback(self, task, *args, **kwargs)
        return super().run(task, *args, **kwargs)


class SubTaskTrackedAgent:
    """
    子任务追踪包装器，为micro agent提供独立的追踪链路

    这个类包装原始的CodeAgent/ToolCallingAgent，在执行时自动创建子任务上下文。
    Telemetry收集现在通过telemetry_context在更高层级管理。
    """

    def __init__(self, agent, agent_name: str):
        """
        初始化子任务追踪包装器

        Args:
            agent: 原始的CodeAgent或ToolCallingAgent实例
            agent_name: 智能体名称，用于生成子任务ID
        """
        self._agent = agent
        self._agent_name = agent_name

        # 代理所有属性到原始agent（除了我们要重写的方法）
        excluded_attrs = {'run', '__call__'}
        for attr in dir(self._agent):
            if (not attr.startswith('_') and
                attr not in excluded_attrs and
                hasattr(self._agent, attr) and
                not callable(getattr(self._agent, attr, None))):
                setattr(self, attr, getattr(self._agent, attr))

    def run(self, task: str, *args, **kwargs):
        """
        在子任务上下文中运行任务

        Args:
            task: 任务描述
            *args, **kwargs: 传递给原始agent的参数

        Returns:
            任务执行结果
        """
        from ai_agents.lib.tracing import sub_task_context

        # 在子任务上下文中执行
        with sub_task_context(self._agent_name) as sub_task_id:
            logger.debug(f"开始执行子任务 {sub_task_id} (智能体: {self._agent_name})")
            result = self._agent.run(task, *args, **kwargs)
            logger.debug(f"完成执行子任务 {sub_task_id}")
            return result

    def __call__(self, task: str, **kwargs):
        """
        在子任务上下文中调用agent（smolagents框架使用的方法）

        Args:
            task: 任务描述
            **kwargs: 传递给原始agent的参数

        Returns:
            任务执行结果
        """
        from ai_agents.lib.tracing import sub_task_context

        # 在子任务上下文中执行
        with sub_task_context(self._agent_name) as sub_task_id:
            logger.debug(f"开始执行子任务 {sub_task_id} (智能体: {self._agent_name}) via __call__")
            result = self._agent(task, **kwargs)
            logger.debug(f"完成执行子任务 {sub_task_id}")
            return result

    def __getattr__(self, name):
        """代理未定义的属性到原始agent"""
        # 不要代理我们已经重写的方法
        if name in ('run', '__call__'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return getattr(self._agent, name)


def new_agent(*args,
              tools=None,
              use_tool_call=None,
              stream_outputs=False,
              additional_authorized_imports: list[str] | None = None,
              enable_sub_task_tracking=False,
              agent_name=None,
              use_customized_prompt=True,
              **kwargs):
    """
    创建新的智能体实例

    Args:
        *args: 传递给智能体构造函数的位置参数
        use_tool_call: 是否使用ToolCallingAgent
        stream_outputs: 是否启用流式输出
        enable_sub_task_tracking: 是否启用子任务追踪
        agent_name: 智能体名称（启用子任务追踪时必需）
        **kwargs: 传递给智能体构造函数的关键字参数

    Returns:
        智能体实例（可能被子任务追踪包装器包装）
    """
    if not tools:
        tools = []

    uniq_tools = []
    _seen = set()
    for _t in tools:
        _k = _t.name if isinstance(_t, Tool) else _t
        if _k in _seen:
            continue
        _seen.add(_k)
        uniq_tools.append(_t)

    from ai_agents.core.tools import tool  # noqa: F401
    all_wrapped_tools = []
    for t in uniq_tools:
        if not is_tool_decorated(t):
            # 如果工具没有被装饰为工具，则使用 tool 装饰器包装
            wrapped_tool = tool(t)
            all_wrapped_tools.append(wrapped_tool)
        else:
            all_wrapped_tools.append(t)

    if use_tool_call:
        agent = ToolCallingAgentV2(*args, tools=all_wrapped_tools, **kwargs)
    else:
        prompt_templates = None
        if use_customized_prompt:
            prompt_templates = yaml.safe_load(_code_agent_prompt_path.read_text())
        agent = CodeAgentV2(*args,
                            tools=all_wrapped_tools,
                            stream_outputs=stream_outputs,
                            prompt_templates=prompt_templates,
                            additional_authorized_imports=additional_authorized_imports,
                            **kwargs)

    # 如果启用子任务追踪，则包装智能体
    if enable_sub_task_tracking:
        if not agent_name:
            raise ValueError("启用子任务追踪时必须提供agent_name参数")
        agent = SubTaskTrackedAgent(agent, agent_name)

    return agent


AgentType = Union["ToolCallingAgentV2", "CodeAgentV2", "SubTaskTrackedAgent"]


def new_agent_logger(log_file_path: str=None, level: LogLevel=LogLevel.INFO, use_time_logger=True):
    if log_file_path:
        console = DualConsole(log_file_path=log_file_path)
    else:
        console = Console()

    # 如果没有提供 logger，创建一个带时间信息的 AgentLogger
    if use_time_logger:
        logger = TimeEnhancedAgentLogger(
            level=level,
            show_timestamp=True,
            timestamp_format="%Y-%m-%d %H:%M:%S"
        )
    else:
        #原始用法
        logger = AgentLogger(level=level, console=console)
    return logger


def is_tool_decorated(obj) -> bool:
    """
    检查给定的对象是否被 @tool 装饰器装饰过

    @tool 装饰器会将普通函数转换为 Tool 类的实例，因此我们可以通过检查对象是否为 Tool 实例来判断

    Args:
        obj: 要检查的对象

    Returns:
        bool: 如果对象被 @tool 装饰过则返回 True，否则返回 False

    Examples:
        >>> @tool
        ... def my_function(x: int) -> int:
        ...     '''测试函数'''
        ...     return x * 2
        >>>
        >>> def regular_function(x: int) -> int:
        ...     return x * 2
        >>>
        >>> is_tool_decorated(my_function)  # True
        >>> is_tool_decorated(regular_function)  # False
    """
    # 检查对象是否是 Tool 类的实例
    if not isinstance(obj, Tool):
        return False

    # 进一步检查是否具有 Tool 的关键属性
    # 这些属性是 @tool 装饰器创建的 SimpleTool 类必须具备的
    required_attrs = ['name', 'description', 'output_type', 'forward', 'is_initialized']

    for attr in required_attrs:
        if not hasattr(obj, attr):
            return False
    # 检查是否有 forward 方法且可调用
    if not callable(getattr(obj, 'forward', None)):
        return False
    # 检查 name 和 description 是否为字符串类型
    if not isinstance(getattr(obj, 'name', None), str):
        return False
    if not isinstance(getattr(obj, 'description', None), str):
        return False
    return True
