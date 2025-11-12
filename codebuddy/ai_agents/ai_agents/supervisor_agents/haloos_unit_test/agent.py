
"""
HaloOS Ceedling 单元测试智能体 - 为 HaloOS 项目创建完整的 Ceedling 测试工程
"""

from pathlib import Path
from smolagents.models import ChatMessage, MessageRole
from smolagents.agents import MultiStepAgent
from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent
from ai_agents.micro_agents.yaml_agent_factory import YamlAgentFactory
from ai_agents.sop_workflows.sop_manager import get_sop
from ai_agents.lib.smolagents import AgentLogger, LogLevel
from ai_agents.lib.tracing import get_current_sub_task_id,get_current_task_id
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.tools import get_coverage_report
from ai_agents.supervisor_agents.haloos_unit_test.ceedling_test_runner import compile_ceedling_repo
from ai_agents.supervisor_agents.haloos_unit_test.conditional_compile_tool import compile_with_configs
from ai_agents.tools import search_and_replace
# import litellm
# litellm.set_verbose = True
# HaloOS SOP 工作流目录路径
_haloos_sop_path = Path(__file__).parent.parent.parent / "sop_workflows" / "haloos_unit_test"

use_human_instruct = haloos_global_env_config.USE_HUMAN_INSTRUCT.lower() == 'true'

def custom_write_memory_to_messages(
    self,
    summary_mode: bool = False,
    human_instruction: str = ''
) -> list[ChatMessage]:
    """
    Reads past llm_outputs, actions, and observations or errors from the memory into a series of messages
    that can be used as input to the LLM. Adds a number of keywords (such as PLAN, error, etc) to help
    the LLM.
    """

    is_print_debug = True

    task_id = get_current_task_id()
    sub_task_id = get_current_sub_task_id()

    if is_print_debug:
        print("****task_id****",task_id)
        print("****sub_task_id****",sub_task_id)

    messages = self.memory.system_prompt.to_messages(summary_mode=summary_mode)
    for memory_step in self.memory.steps:
        messages.extend(memory_step.to_messages(summary_mode=summary_mode))

    # 可能为None
    if sub_task_id:
        if 'unit_test_agent' in sub_task_id:
            # 创建用户消息，可以尝试各种方式获取human_instruction
            user_msg = ChatMessage(
                role=MessageRole.USER,
                content=[{"type": "text", "text": human_instruction}]
            )
            # 可以考虑加入len(step)判断，每隔多少步加入
            messages.extend([user_msg.dict()])

    if use_human_instruct and is_print_debug:
        # 只打印最后两条消息
        for i in messages[-2:]:
            print(i)
    return messages

if use_human_instruct:
    MultiStepAgent.write_memory_to_messages = custom_write_memory_to_messages


class HaloOSUnitTestSupervisorAgent(BaseSupervisorAgent):
    """
    HaloOS Ceedling 单元测试任务执行智能体

    本智能体的核心职责是使用专业化的工具来完成 "为 HaloOS 项目创建单元测试" 的任务。
    它通过调用封装了微智能体能力的原子工具来执行具体的代码编写和测试生成工作。

    主要工具能力：
    - generate_unit_test: **核心工具**，负责根据指令生成 Ceedling 测试文件、测试用例和 Mock 对象
    - 文件操作工具: 用于分析项目结构、读取源码文件等辅助任务

    核心工作流程：
    1. 接收用户关于 HaloOS 单元测试的任务。
    2. 基于内置的 SOP 工作流，分析任务并制定执行计划。
    3. 使用文件操作工具分析项目结构和源码。
    4. 主要使用 `generate_unit_test` 工具执行测试生成任务。
    5. 整合工具执行结果，提供完整的任务完成报告。
    """

    with_memory = False

    @property
    def name(self) -> str:
        return "halo_os_unit_test_gen"

    @property
    def sop_category(self) -> str:
        return "haloos_unit_test"

    @property
    def default_task_type(self) -> str:
        # 测试生成需要复杂推理能力
        return "complex_reasoning"

    def __init__(self,
                 model=None,
                 execution_env=None,
                 execution_env_config=None,
                 logger: AgentLogger=None,
                 verbosity_level: LogLevel = LogLevel.INFO):
        """
        初始化 HaloOS Ceedling 单元测试监督智能体

        Args:
            model: 可选的模型实例，如果不提供将使用模型管理器自动选择
            execution_env: 可选的执行环境实例，如果不提供将创建默认的host环境
            execution_env_config: 执行环境的配置参数，仅在execution_env为None时使用
            logger: 可选的日志记录器，如果不提供将创建带时间戳的默认日志器
            verbosity_level: 日志详细程度级别，默认为 INFO
        """
        # 先调用基类初始化，获得 memory 系统
        super().__init__(model=model,
                         execution_env=execution_env,
                         execution_env_config=execution_env_config,
                         logger=logger)

    def _get_tools(self):
        """获取智能体使用的工具列表

        监督智能体主要依赖默认工具（Memory 工具 + 文件操作工具）
        以及管理的微智能体来完成任务，不需要额外的专业工具
        """

        # 额外工具的添加
        add_extra_tools_in_main_agent = True

        tools = []
        micro_agents_folder = _haloos_sop_path / 'micro_agents'

        if micro_agents_folder.exists():
            # 确保微智能体也使用时间增强的日志器
            enhanced_logger = self._logger
            micro_agent_tools = YamlAgentFactory.create_agents_as_tools_from_folder(
                micro_agents_folder,
                memory=self._memory,
                execution_env=self._execution_env,
                logger=enhanced_logger
            )
            tools.extend(micro_agent_tools)

        # 子agent内定制工具，主agent可能也需要用，比如一些检测和覆盖率工具
        if add_extra_tools_in_main_agent:
            # 'get_coverage_report','compile_ceedling_repo', 'compile_with_configs','search_and_replace'
            select_extra_tool_name = [get_coverage_report,compile_ceedling_repo,compile_with_configs]
            tools.extend(select_extra_tool_name)

            # 已有工具直接使用: 'search_and_replace'
            tools.append(search_and_replace)
        # original
        return tools


    def _get_enhanced_task(self, task: str) -> str:
        """
        构建增强任务描述，指导本监督智能体进行任务拆解和委派。

        Args:
            task: 原始任务描述

        Returns:
            str: 增强后的任务描述，包含如何作为监督者进行任务拆解和委派的明确指令。
        """

        sop_content = get_sop(self.sop_category)
        enhanced_task = f"""
作为 {self.name} 监督智能体，你的核心职责是 **任务拆解**。你需要将用户的任务拆解成一个详细的、可执行的计划，然后调用专门的微智能体去完成具体的每一步。

**SOP 工作流程**：
{sop_content}

**项目特定信息**：
- 目标项目：HaloOS（C 语言操作系统项目）
- 测试框架：Ceedling + CMock
- 验证命令：`ceedling clobber && ceedling test:all`

**核心指令**:
1.  **分析和拆解任务**: 详细阅读SOP和用户任务，生成一个清晰的步骤化计划。
2.  **委派任务给 UnitTestAgent**: 计划中所有和“生成/编写/修改测试代码”相关的步骤，都必须委派给 `UnitTestAgent` 来执行。
3.  **明确沟通**: 在调用 `UnitTestAgent` 时，必须在任务描述中明确告知它：“这是一个独立的测试生成任务，请直接完成并输出结果，不要将结果作为新的任务反馈给监督智能体。” 这是为了避免无限循环。

**用户原始任务**：{task}

请严格按照上述指令和SOP流程，生成计划并协调微智能体完成任务。
"""
        return enhanced_task
