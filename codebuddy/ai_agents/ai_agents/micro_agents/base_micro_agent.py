"""
微智能体抽象基类

定义了所有微智能体的通用接口和行为模式。
微智能体的核心职责是提供专业化的技术能力，通过 get_code_agent() 方法
返回配置好的 CodeAgent 实例供监督智能体使用。
"""

from abc import abstractmethod
from typing import Optional, Union

from ai_agents.core.agents.baseagent import BaseAgent
from ai_agents.lib.smolagents import AgentLogger
from ai_agents.core import TaskType
from ai_agents.memory.tree_store import HierarchicalMemorySystem
from ai_agents.memory.tree_store.prompt import MICRO_AGENT_MEMORY_PROMPT
from ai_agents.tools.execution.base.execution_environment import ExecutionEnvironment


class BaseMicroAgent(BaseAgent):
    """
    微智能体抽象基类

    所有微智能体都应该继承此类并实现必要的抽象方法。
    基类提供了通用的初始化逻辑和模型管理功能。

    微智能体的设计原则：
    1. 专业化：每个微智能体专注于特定的技术领域
    2. 标准化：通过 get_code_agent() 方法提供统一接口
    3. 可组合：可以被监督智能体作为 managed_agents 使用
    4. 自包含：包含完成任务所需的所有工具和配置
    """

    # 微智能体的默认配置
    tool_call_type = "tool_call"  # tool_call, code_act

    @property
    @abstractmethod
    def description(self) -> str:
        """智能体描述，说明其能力和用途"""
        pass

    @property
    @abstractmethod
    def default_task_type(self) -> Union[TaskType, str]:
        """默认任务类型，用于模型选择"""
        pass

    # _get_tools() 和 name 已经在BaseAgent中定义为抽象方法

    def __init__(self,
                 model=None,
                 memory: Optional[HierarchicalMemorySystem] = None,
                 execution_env: Optional[ExecutionEnvironment] = None,
                 logger: Optional[AgentLogger] = None):
        """
        初始化微智能体

        Args:
            model: 可选的模型实例，如果不提供将使用模型管理器自动选择
            memory: 可选的 Memory 系统实例，可以后续通过 set_memory() 设置
            execution_env: 可选的执行环境实例，通常由监督智能体传递
            logger: 可选的日志记录器
        """
        # 调用父类初始化
        super().__init__(
            model=model,
            memory=memory,
            execution_env=execution_env,
            logger=logger
        )

        # 微智能体特有的属性
        self._memory_instruction_injected = False

        # 注入统一的micro agent memory指导
        if self._memory:
            self.inject_memory_instruction(MICRO_AGENT_MEMORY_PROMPT)

    def inject_memory_instruction(self, instruction: str):
        """
        注入内存指导指令（微智能体版本，只注入一次）

        Args:
            instruction: 要注入的指导指令
        """
        def memory_callback(agent, task, *args, **kwargs):
            if not self._memory_instruction_injected:
                task = f"""<memory_instruction>
{instruction}
</memory_instruction>
{task}
"""
                self._memory_instruction_injected = True
            return task
        self._before_run_callbacks.append(memory_callback)

    # set_memory() 和 set_execution_env() 已经在BaseAgent中定义
    # get_all_tools() 已经在BaseAgent中定义，这里不需要重复

    def get_code_agent(self):
        """
        获取配置好的 CodeAgent 实例，用作 managed_agent

        这是微智能体的核心接口方法，监督智能体通过此方法获取
        配置好的 CodeAgent 实例来执行具体的技术任务。

        Returns:
            CodeAgent: 配置了专业工具的 CodeAgent 实例
        """
        # 获取所有工具（微智能体权限）
        tools = self.get_all_tools(agent_type="micro")

        additional_config = {
            'additional_authorized_imports': ["time", "pathlib", "json", "os", "sys"],
            'name': self.name,
            'description': self.description,
            'enable_sub_task_tracking': True,  # 启用子任务追踪
        }

        return self._create_agent(tools=tools, additional_config=additional_config)

    def run_with_telemetry(self, task: str, task_id: str = None):
        """
        执行任务并包含telemetry上下文，主要供监督智能体调用

        Args:
            task: 任务描述
            task_id: 任务ID

        Returns:
            str: 任务执行结果
        """
        agent = self.get_code_agent()
        return super().run_with_telemetry(task, task_id, agent)

    # run() 方法已经在BaseAgent中实现，这里不需要重复

    # _validate_model() 方法已经在BaseAgent中实现，这里不需要重复
