from typing import List
from ai_agents.lib.smolagents import AgentLogger
from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent
from ai_agents.sop_workflows.sop_manager import get_sop
from ai_agents.tools.file_ops import (
    get_file_info,
    quick_browse_directory,
    create_new_file
)

from ai_agents.supervisor_agents.detected_static_repair.file_reader import get_json_info_by_key_from_jsonpath,match_misra_rule,extract_info_from_common_jsonfile_by_key
from ai_agents.tools.grep import (search_keyword_in_directory,search_keyword_with_context)
from ai_agents.supervisor_agents.detected_static_repair.build_runner import (execute_coverity_build_command)
from ai_agents.supervisor_agents.detected_static_repair.coverity_analysis_tool import execute_analyse_command
from ai_agents.supervisor_agents.detected_static_repair.file_writer import append_markdown_content_2_file


class DetectedStaticRepairAgent(BaseSupervisorAgent):
    tool_call_type = "code_act" # tool_call, code_act
    max_steps = 100
    with_memory = False
    # tool_call_type = "tool_call" # tool_call, code_act

    @property
    def name(self) -> str:
        return "detected_static_repair_supervisor"

    @property
    def sop_category(self) -> str:
        return "detected_static_repair"

    @property
    def default_task_type(self) -> str:
        return "complex_reasoning"

    def __init__(self,
                 model=None,
                 execution_env=None,
                 execution_env_config=None,
                 logger: AgentLogger=None):
        """初始化静态缺陷修复监督智能体。

        该智能体专门用于检测和修复代码中的静态分析问题，包括 MISRA 规则违规、
        Coverity 检测到的缺陷等静态代码质量问题。

        Args:
            model (Optional): 模型实例。如果未提供，将使用模型管理器自动选择
            execution_env (Optional): 执行环境实例。如果未提供，将创建默认的主机环境
            execution_env_config (Optional[dict]): 执行环境配置参数。
                仅在 execution_env 为 None 时使用
            logger (Optional[AgentLogger]): 日志记录器实例，用于记录智能体运行日志

        Note:
            该智能体继承自 BaseSupervisorAgent，具有代码分析、缺陷检测和修复建议的能力。
            支持通过 tool_call 和 code_act 两种模式进行操作。
        """
        # Call base class initialization first to get memory system
        super().__init__(model=model,
                         execution_env=execution_env,
                         execution_env_config=execution_env_config,
                         logger=logger)

    def _get_managed_agents(self):
        """获取管理的微智能体列表"""
        return []


    def _get_tools(self) -> List:
        """获取覆盖率分析智能体使用的工具列表"""
        tools=[]
        file_tools = [
            # ensure_all_tools,  # 这是一个函数而不是工具，应该在初始化时调用
            # read_file_content,
            create_new_file,
            get_file_info,
            quick_browse_directory,
            # read_file_content_no_truncate,  # 使用无截断版本
            # read_file_lines,  # 行读取工具不受截断影响
            match_misra_rule,
            get_json_info_by_key_from_jsonpath
        ]
        tools.extend(file_tools)
        search_tools = [
            search_keyword_in_directory,
            search_keyword_with_context,
        ]
        tools.extend(search_tools)
        select_extra_tool_name = [execute_coverity_build_command,execute_analyse_command,
                                    append_markdown_content_2_file,extract_info_from_common_jsonfile_by_key]
        tools.extend(select_extra_tool_name)
        return tools


    def _create_supervisor_agent(self):
        """创建配置好的监督智能体，添加内置函数支持"""
        # 只使用 _get_default_tools()，因为它已经通过 get_all_tools() 包含了 _get_tools()
        tools = self._get_default_tools()

        managed_agents = self._get_managed_agents()

        # 只有在有模型时才启用stream_outputs
        stream_outputs = self._model is not None

        use_tool_call = self.tool_call_type == 'tool_call'

        # 为代码执行环境添加内置函数支持
        from ai_agents.lib.smolagents import new_agent, LogLevel
        agent = new_agent(
            tools=tools,
            model=self._model,
            managed_agents=managed_agents,
            additional_authorized_imports=['*', 'builtins'],
            max_steps=self.max_steps,
            verbosity_level=LogLevel.INFO,
            use_tool_call=use_tool_call,
            stream_outputs=stream_outputs,
            logger=self._logger,
        )
        return agent

    def _get_enhanced_task(self, task: str) -> str:
        """
        Build enhanced task description to guide supervisor agent in task decomposition and delegation.

        Args:
            task: Original task description

        Returns:
            str: Enhanced task description including SOP process and clear execution instructions
        """

        sop_content = get_sop(self.sop_category)
        enhanced_task = f"""
            {sop_content}
            {task},
            """
        return enhanced_task
