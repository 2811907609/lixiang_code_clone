"""
监督智能体抽象基类

定义了所有监督智能体的通用接口和行为模式。
监督智能体的核心职责是协调多个微智能体完成复杂任务。
"""

from abc import abstractmethod
from typing import List, Optional

from ai_agents.core.agents.baseagent import BaseAgent
from ai_agents.lib.smolagents import AgentLogger
from ai_agents.lib.tracing import generate_task_id, task_context
from ai_agents.memory.tree_store.prompt import SUPERVISOR_AGENT_MEMORY_PROMPT
from ai_agents.sop_workflows.sop_manager import get_sop
from ai_agents.tools.execution import create_execution_environment
from ai_agents.tools.file_ops import (
    browse_directory,
    read_file_content,
    read_file_lines,
)
from ai_agents.telemetry import AgentType


class BaseSupervisorAgent(BaseAgent):
    """
    监督智能体抽象基类

    所有监督智能体都应该继承此类并实现必要的抽象方法。
    基类提供了通用的初始化逻辑和SOP集成功能。
    """

    # 监督智能体的默认配置
    with_memory = True
    tool_call_type = "code_act"  # tool_call, code_act
    max_steps = 80

    @property
    @abstractmethod
    def sop_category(self) -> str:
        """对应的SOP类别名称"""
        pass

    # 继承自BaseAgent的抽象方法已经定义，这里只需要添加监督智能体特有的抽象方法

    def __init__(self,
                 project_path: str = "",
                 model=None,
                 execution_env=None,
                 execution_env_config: Optional[dict] = None,
                 logger: Optional[AgentLogger] = None,
                 model_cache: bool = True):
        """
        初始化监督智能体

        Args:
            project_path: 项目路径
            model: 可选的模型实例，如果不提供将使用模型管理器自动选择
            execution_env: 可选的执行环境实例，如果不提供将创建默认的host环境
            execution_env_config: 执行环境的配置参数，仅在execution_env为None时使用
            logger: 可选的日志记录器
            model_cache: 是否启用模型缓存
        """
        # 初始化执行环境
        if execution_env is None:
            execution_env = create_execution_environment("host", **(execution_env_config or {}))

        # 调用父类初始化
        super().__init__(
            model=model,
            execution_env=execution_env,
            logger=logger,
            model_cache=model_cache
        )

        # 监督智能体特有的属性
        self._project_path = project_path
        self._agent = None

    def project_path(self):
        return self._project_path

    def _finalize_initialization(self):
        """完成初始化，创建 supervisor agent"""
        if self._agent is None:
            self._agent = self._create_supervisor_agent()

    def _create_supervisor_agent(self):
        """创建配置好的监督智能体"""
        tools = self._get_default_tools()

        additional_config = {
            'additional_authorized_imports': ['*'],
            'agent_name': None,  # 监督智能体不设置agent_name
        }

        return self._create_agent(tools=tools, additional_config=additional_config)

    def _get_default_tools(self) -> List:
        """获取监督智能体的默认工具"""
        # 获取基础工具（内存工具 + 执行环境工具）
        base_tools = self.get_all_tools(agent_type="supervisor")

        # 添加文件操作工具
        file_tools = [
            read_file_content,
            read_file_lines,
            browse_directory,
        ]

        return base_tools + file_tools

    def _get_enhanced_task(self, task: str) -> str:
        """
        构建增强的任务描述，包含SOP流程和基本指导原则

        Args:
            task: 原始任务描述

        Returns:
            str: 增强后的任务描述
        """
        sop_content = get_sop(self.sop_category)
        memory_prompt = ''
        if self.with_memory:
            memory_prompt = SUPERVISOR_AGENT_MEMORY_PROMPT + '\n'
        enhanced_task = f"""
{memory_prompt}

作为{self.name}监督智能体，协调微智能体团队完成任务。

**核心职责**：
1. 严格遵循SOP流程
2. 将大任务分解为具体的小任务
3. 委派给合适的微智能体
4. 整合结果并提供总结

**SOP流程**：
{sop_content}

**关键原则**：
- ✅ 任务分解：大任务→小任务→具体指令
- ✅ 精确委派：给微智能体清晰、具体的任务
- ✅ 结果加工：对微智能体结果进行分析、整合、补充上下文
{'- ✅ Memory更新：将加工后的结果以Markdown格式更新到Memory' if self.with_memory else ''}
- ❌ 避免：直接执行技术工作、直接转存原始结果

**用户任务**：{task}

请按SOP流程，通过任务分解、微智能体协调和结果加工完成任务。
"""
        return enhanced_task



    def _get_agent_type(self) -> AgentType:
        """获取智能体类型"""
        return AgentType.SUPERVISOR

    def run(self, task: str, task_id: str = None):
        """
        执行任务

        Args:
            task: 任务描述
            task_id: 可选的任务ID，如果不提供则自动生成

        Returns:
            str: 任务执行结果
        """
        if task_id is None:
            task_id = generate_task_id()

        self._task_id = task_id

        if self.with_memory and self._memory:
            self._memory.set_current_task(task_id)

        # Execute task with context tracking
        with task_context(task_id):
            self._finalize_initialization()

            # 增强任务描述
            enhanced_task = self._get_enhanced_task(task)

            # 使用基类的telemetry方法，传入额外的SOP参数
            return self.run_with_telemetry(
                enhanced_task,
                task_id,
                agent=self._agent,
                sop_category=self.sop_category
            )
