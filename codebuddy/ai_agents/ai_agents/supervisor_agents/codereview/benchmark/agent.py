from typing import List

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.sop_workflows.sop_manager import get_sop
from ai_agents.supervisor_agents.base_supervisor_agent import (
    BaseSupervisorAgent,
)


class CodeReviewBenchMarkAgent(BaseSupervisorAgent):
    with_memory = False
    tool_call_type = 'code_act'

    @property
    def sop_category(self) -> str:
        """对应的SOP类别名称"""
        return 'code_review_benchmark'

    @property
    def name(self) -> str:
        return '代码审查基准测试审查智能体'

    @property
    def default_task_type(self) -> str:
        return 'code_review'

    def __init__(
        self,
        project_path='',
        model=None,
        execution_env=None,
        execution_env_config=None,
        logger: AgentLogger = None,
    ):
        super().__init__(
            project_path=project_path,
            model=model,
            execution_env=execution_env,
            execution_env_config=execution_env_config,
            logger=logger,
            model_cache=False
        )

    def _get_managed_agents(self) -> List:
        return []

    def _get_tools(self) -> List:
        return []

    def _get_enhanced_task(self, task: str) -> str:
        sop_content = get_sop(self.sop_category)
        enhanced_task = f"""

        遵循 {sop_content} 工作流，完成以下用户任务：

        {task}

"""
        return enhanced_task
