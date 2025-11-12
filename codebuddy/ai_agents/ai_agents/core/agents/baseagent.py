"""
智能体抽象基类

定义了所有智能体的通用接口和行为模式。
提供了模型管理、执行环境、内存系统等通用功能。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
import threading

from ai_agents.core.model_manager import get_model_for_task
from ai_agents.core import TaskType
from ai_agents.lib.smolagents import AgentLogger, LogLevel, new_agent, CodeAgent
from ai_agents.lib.tracing import generate_task_id, task_context, get_current_task_id, get_current_agent_id
from ai_agents.memory.tree_store import HierarchicalMemorySystem
from ai_agents.core.runtime import runtime
from ai_agents.tools.execution.base.execution_environment import ExecutionEnvironment
from ai_agents.telemetry import (
    telemetry_context,
    AgentType,
)


# 按名字分别计数的全局计数器，用于生成唯一的agent序号
_agent_counters = {}
_counter_lock = threading.Lock()


class BaseAgent(ABC):
    """
    智能体抽象基类

    所有智能体都应该继承此类并实现必要的抽象方法。
    基类提供了通用的初始化逻辑、模型管理、执行环境和内存系统集成。
    """

    # 默认配置，子类可以覆盖
    tool_call_type = "tool_call"  # tool_call, code_act
    max_steps = 80
    with_memory = False

    @property
    @abstractmethod
    def name(self) -> str:
        """智能体名称"""
        pass

    @property
    @abstractmethod
    def default_task_type(self) -> Union[str, TaskType]:
        """默认任务类型，用于模型选择"""
        pass

    @abstractmethod
    def _get_tools(self) -> List:
        """获取智能体使用的工具列表"""
        pass

    def __init__(self,
                 model=None,
                 memory: Optional[HierarchicalMemorySystem] = None,
                 execution_env: Optional[ExecutionEnvironment] = None,
                 logger: Optional[AgentLogger] = None,
                 model_cache: bool = True):
        """
        初始化智能体

        Args:
            model: 可选的模型实例，如果不提供将使用模型管理器自动选择
            memory: 可选的 Memory 系统实例
            execution_env: 可选的执行环境实例
            logger: 可选的日志记录器
            model_cache: 是否启用模型缓存
        """
        # 初始化模型
        if model is None:
            custom_headers = runtime.get_custom_headers(type(self).__name__)
            override_config = dict(
                extra_headers=custom_headers
            )
            self._model = get_model_for_task(
                self.default_task_type,
                "smolagents",
                override_config,
                model_cache
            )
        else:
            self._model = model

        # 初始化内存系统
        self._memory: Optional[HierarchicalMemorySystem] = memory
        if self.with_memory and memory is None:
            self._memory = HierarchicalMemorySystem()

        # 初始化执行环境
        self._execution_env: Optional[ExecutionEnvironment] = execution_env

        # 初始化日志记录器
        self._logger = logger

        # 回调函数列表
        self._before_run_callbacks = []

        # 任务ID
        self._task_id = None

        # 生成唯一的agent ID
        self._agent_id = self._generate_agent_id()

        self._final_answer_checks = []

    def _generate_agent_id(self) -> str:
        """
        生成唯一的agent ID

        Returns:
            str: 格式为 "{name}_{序号}" 的agent ID，同名agent序号从001开始连续递增
        """
        global _agent_counters
        with _counter_lock:
            agent_name = self.name
            if agent_name not in _agent_counters:
                _agent_counters[agent_name] = 0
            _agent_counters[agent_name] += 1
            return f"{agent_name}_{_agent_counters[agent_name]:03d}"

    def get_agent_id(self) -> str:
        """
        获取agent ID

        Returns:
            str: agent的唯一标识符
        """
        return self._agent_id

    def set_memory(self, memory: HierarchicalMemorySystem):
        """设置 memory 系统"""
        self._memory = memory

    def set_execution_env(self, execution_env: ExecutionEnvironment):
        """设置执行环境"""
        self._execution_env = execution_env

    def inject_memory_instruction(self, instruction: str):
        """
        注入内存指导指令

        Args:
            instruction: 要注入的指导指令
        """
        def memory_callback(agent, task, *args, **kwargs):
            task = f"""<memory_instruction>
{instruction}
</memory_instruction>
{task}
"""
            return task
        self._before_run_callbacks.append(memory_callback)

    def set_final_answer_checks(self, check_func_list):
        """获取最终答案验证函数"""
        self._final_answer_checks = check_func_list

    def get_memory_tools(self, agent_type: str = "micro") -> List:
        """
        获取内存工具列表

        Args:
            agent_type: 智能体类型，用于确定权限级别

        Returns:
            List: 内存工具列表
        """
        if self._memory:
            return self._memory.tools(agent_type=agent_type)
        return []

    def get_execution_tools(self) -> List:
        """
        获取执行环境工具列表

        Returns:
            List: 执行环境工具列表
        """
        if self._execution_env:
            return self._execution_env.tools()
        return []

    def get_all_tools(self, agent_type: str = "micro") -> List:
        """
        获取所有可用的工具列表

        Args:
            agent_type: 智能体类型，用于确定内存工具权限级别

        Returns:
            List: 合并后的所有工具列表
        """
        memory_tools = self.get_memory_tools(agent_type)
        execution_tools = self.get_execution_tools()
        agent_tools = self._get_tools()

        return memory_tools + agent_tools + execution_tools

    def _create_agent(self,
                     tools: List = None,
                     additional_config: dict = None) -> CodeAgent:
        """
        创建配置好的智能体实例

        Args:
            tools: 工具列表，如果不提供则使用 get_all_tools()
            additional_config: 额外的配置参数

        Returns:
            CodeAgent: 配置好的智能体实例
        """
        if tools is None:
            tools = self.get_all_tools()

        # 默认配置
        config = {
            'tools': tools,
            'model': self._model,
            'verbosity_level': LogLevel.INFO,
            'use_tool_call': self.tool_call_type == 'tool_call',
            'max_steps': self.max_steps,
            'stream_outputs': self._model is not None,
            'logger': self._logger,
            'agent_name': self.name,
            'before_run_callbacks': self._before_run_callbacks,
            'final_answer_checks': self._final_answer_checks
        }

        # 合并额外配置
        if additional_config:
            config.update(additional_config)

        return new_agent(**config)

    def _validate_model(self) -> bool:
        """
        验证模型是否可用

        Returns:
            bool: 模型是否可用
        """
        return self._model is not None

    def _get_agent_type(self) -> AgentType:
        """
        获取智能体类型，子类应该覆盖此方法

        Returns:
            AgentType: 智能体类型
        """
        return AgentType.MICRO  # 默认为微智能体

    def run_with_telemetry(self,
                          task: str,
                          task_id: Optional[str] = None,
                          agent: Optional[CodeAgent] = None,
                          **telemetry_kwargs) -> str:
        """
        执行任务并包含telemetry上下文

        Args:
            task: 任务描述
            task_id: 任务ID
            agent: 可选的智能体实例，如果不提供则创建新的
            **telemetry_kwargs: 额外的telemetry参数

        Returns:
            str: 任务执行结果
        """
        from ai_agents.lib.tracing import set_current_agent_id, clear_current_agent_id

        if agent is None:
            agent = self._create_agent()

        # 准备telemetry参数
        telemetry_params = {
            'agent': agent,
            'agent_name': self.name,
            'task': task,
            'task_id': task_id,
            'agent_type': self._get_agent_type(),
            'task_type': (
                self.default_task_type.value
                if hasattr(self.default_task_type, 'value')
                else str(self.default_task_type)
            ),
        }
        telemetry_params.update(telemetry_kwargs)

        # 设置当前agent ID到tracing上下文
        previous_agent_id = None
        try:
            previous_agent_id = get_current_agent_id()
            set_current_agent_id(self.get_agent_id())

            # 使用telemetry上下文管理器
            with telemetry_context(**telemetry_params) as instrumented_agent:
                return instrumented_agent.run(task=task)
        finally:
            # 恢复之前的agent ID
            if previous_agent_id is not None:
                set_current_agent_id(previous_agent_id)
            else:
                clear_current_agent_id()

    def run(self, task: str, task_id: Optional[str] = None) -> str:
        """
        执行任务的基础方法

        Args:
            task: 任务描述
            task_id: 可选的任务ID，如果不提供则自动生成

        Returns:
            str: 任务执行结果
        """
        # 获取当前任务上下文
        current_task_id = get_current_task_id()

        if not current_task_id and task_id is None:
            task_id = generate_task_id(f"{self._get_agent_type().value.lower()}_{self.name}")

        if not current_task_id:
            # 创建新的任务上下文
            with task_context(task_id):
                return self.run_with_telemetry(task, task_id)
        else:
            # 已经在任务上下文中
            return self.run_with_telemetry(task, current_task_id)
