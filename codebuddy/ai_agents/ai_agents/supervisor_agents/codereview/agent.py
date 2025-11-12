from pathlib import Path
from typing import List
import time
import logging

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.lib.tracing import generate_task_id
from ai_agents.micro_agents.yaml_agent_factory import YamlAgentFactory
from ai_agents.supervisor_agents.base_supervisor_agent import (
    BaseSupervisorAgent,
)
from ai_agents.supervisor_agents.codereview.codereview_yaml_agent import CodeReviewYamlAgent
from ai_agents.supervisor_agents.codereview.call_tracker import get_call_tracker
from ai_agents.tools.codereview import (
    create_review_content_file,
    update_review_content_file_with_result
)

logger = logging.getLogger(__name__)

_code_review_sop_path = (
    Path(__file__).parent.parent.parent / "sop_workflows" / "code_review"
)


class CodeReviewSupervisorAgent(BaseSupervisorAgent):
    with_memory = False
    tool_call_type = 'code_act'
    max_steps=30

    @property
    def sop_category(self) -> str:
        """对应的SOP类别名称"""
        return "code_review"

    @property
    def name(self) -> str:
        """智能体名称"""
        return "代码审查"

    @property
    def default_task_type(self) -> str:
        """默认任务类型，用于模型选择"""
        return "complex_reasoning"

    def __init__(
        self,
        project_path="",
        model=None,
        execution_env=None,
        execution_env_config=None,
        logger: AgentLogger = None,
        agent_tool_template_vars: dict = None,
        final_answer_checks: List = None
    ):
        """
        初始化代码审查监督智能体

        Args:
            project_path: 项目路径
            model: 可选的模型实例，如果不提供将使用模型管理器自动选择
            execution_env: 可选的执行环境实例，如果不提供将创建默认的host环境
            execution_env_config: 执行环境的配置参数
            logger: 日志记录器
            agent_tool_template_vars: Agent工具的模板变量
            final_answer_checks: 最终答案验证函数列表
        """
        super().__init__(
            project_path=project_path,
            model=model,
            execution_env=execution_env,
            execution_env_config=execution_env_config,
            logger=logger,
        )

        self._agent_tool_template_vars = agent_tool_template_vars
        if final_answer_checks or len(final_answer_checks) > 0:
            self.set_final_answer_checks(final_answer_checks)

        # 真实调用状态跟踪变量
        self._actual_calls_made = {
            'review_agent_called': False,
            'verify_agent_called': False
        }


    def _get_managed_agents(self) -> List:
        return []

    def _get_tools(self) -> List:
        """获取智能体使用的工具列表"""
        tools = []
        micro_agents_folder = _code_review_sop_path / 'micro_agents'
        if micro_agents_folder.exists():
            micro_agent_tools = YamlAgentFactory.create_agents_as_tools_from_folder(
                micro_agents_folder,
                memory=self._memory,
                execution_env=self._execution_env,
                logger=self._logger,
                agent_class=CodeReviewYamlAgent,
                agent_tool_template_vars=self._agent_tool_template_vars
            )
            tools.extend(micro_agent_tools)
        tools.append(create_review_content_file)
        tools.append(update_review_content_file_with_result)
        return tools

    def _get_enhanced_task(self, task: str) -> str:
        """
        构建增强任务描述，指导本监督智能体进行任务拆解和委派。

        Args:
            task: 原始任务描述

        Returns:
            str: 增强后的任务描述，包含如何作为监督者进行任务拆解和委派的明确指令。
        """
        print(self._agent.prompt_templates.get('system_prompt'))

        from ai_agents.sop_workflows.sop_manager import get_sop

        sop_content = get_sop(self.sop_category)
        enhanced_task = f"""
作为 {self.name} 监督智能体，你是资深代码审查专家，具备丰富的代码质量管理和团队协作经验。你的核心职责是 **任务拆解和Agent协调**。

**重要执行原则**：
1. **禁止模拟执行**：绝对不要手工模拟Review Agent或Verify Agent的工作
2. **必须使用工具调用**：严格使用 `code_review_agent` 和 `verify_code_review_agent` 工具
3. **真实Agent调用**：每个步骤都必须调用对应的真实Agent工具，获取实际执行结果
4. **禁止虚构结果**：不能自己构造JSON响应，必须基于Agent工具的真实返回结果
5. **任务ID传递约束**：在调用Agent工具时，必须传递当前任务的task_id: {self._task_id}

**SOP 工作流程**：
{sop_content}

**当前任务ID**：{self._task_id}

**用户原始任务**：{task}

请严格按照SOP流程，**真实调用Agent工具**完成用户任务！
**关键要求**：
1. 每次调用Agent工具时，参数中必须包含task_id: "{self._task_id}"，否则状态跟踪会失败！
2. 若用户定义返回结果格式，请严格参照用户定义格式！

"""
        return enhanced_task

    def run(self, task: str, task_id: str = None):
        """
        执行任务，包含真实调用检测和重试机制

        Args:
            task: 任务描述
            task_id: 可选的任务ID，如果不提供则自动生成

        Returns:
            str: 任务执行结果
        """
        # 确保 agent 已经创建
        self._finalize_initialization()

        if task_id is None:
            task_id = generate_task_id()

        self._task_id = task_id

        if self.with_memory:
            self._memory.set_current_task(task_id)

        # 初始化调用跟踪
        call_tracker = get_call_tracker()
        call_tracker.init_task(task_id)

        max_retries = 3
        # 这里使用 kivy-qwen3-coder-480b-a35b-instruct 时会偶尔出现模拟调用Agent(不实际调用agent，而是自己模拟输出agent tool)的情况，这里基于hook机制在调用之前更新下状态。
        # 任务执行后判断是否实际调用了 agent，如果没有认为任务失败重试
        for attempt in range(max_retries):
            logger.info(f"开始执行代码审查任务，尝试次数: {attempt + 1}/{max_retries}, task_id={task_id}")
            try:
                enhanced_task = self._get_enhanced_task(task)

                # 重置调用状态（除了第一次尝试）
                if attempt > 0:
                    call_tracker.reset_agent_status(task_id, "review")
                    logger.info(f"第{attempt + 1}次重试，已重置调用状态")

                # 执行任务
                result = self._agent.run(task=enhanced_task)

                # 等待一小段时间确保hook完成标记
                time.sleep(0.5)

                # 检查是否进行了真实调用
                review_called = call_tracker.is_agent_called(task_id, "review")

                logger.info(f"调用状态检查: review_called={review_called}")

                if review_called:
                    logger.info(f"检测到真实Agent调用，任务执行成功: task_id={task_id}")
                    call_tracker.cleanup_task(task_id)
                    return result
                else:
                    # 如果是最后一次尝试，记录失败并返回错误
                    if attempt == max_retries - 1:
                        error_msg = f"检测到模拟调用而非真实调用，已重试{max_retries}次均失败。review_called={review_called}"
                        logger.error(error_msg)
                        call_tracker.cleanup_task(task_id)
                        return f"任务执行失败: {error_msg}"
                    else:
                        logger.warning(f"检测到模拟调用，准备重试。review_called={review_called}")

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"任务执行异常，已重试{max_retries}次: {str(e)}")
                    call_tracker.cleanup_task(task_id)
                    return f"任务执行失败: {str(e)}"
                else:
                    logger.warning(f"任务执行异常，准备重试: {str(e)}")

        # 理论上不会到达这里，但作为保险
        call_tracker.cleanup_task(task_id)
        return "任务执行失败: 未知错误"
