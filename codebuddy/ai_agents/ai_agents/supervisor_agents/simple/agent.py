
from pathlib import Path

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent
from ai_agents.sop_workflows.sop_manager import get_sop

_simple_sop_path = Path(__file__).parent.parent.parent / "sop_workflows" / "simple"


class SimpleSupervisorAgent(BaseSupervisorAgent):
    """
    A very simple SOP agent, for demo and test.
    """

    with_memory = False
    tool_call_type = "tool_call" # tool_call, code_act
    max_steps = 20

    @property
    def name(self) -> str:
        return "simple_supervisor"

    @property
    def sop_category(self) -> str:
        return "simple"

    @property
    def default_task_type(self) -> str:
        return "complex_reasoning"

    def __init__(self,
                 model=None,
                 execution_env=None,
                 execution_env_config=None,
                 logger: AgentLogger=None):
        """
        Initialize Simple Supervisor Agent

        Args:
            model: Optional model instance, will use model manager auto-selection if not provided
            execution_env: Optional execution environment instance, will create default host environment if not provided
            execution_env_config: Execution environment configuration parameters, only used when execution_env is None
            logger: Logger instance
        """
        # Call base class initialization first to get memory system
        super().__init__(model=model,
                         execution_env=execution_env,
                         execution_env_config=execution_env_config,
                         logger=logger)

    def _get_tools(self):
        """Get list of tools used by the agent

        Supervisor agent mainly relies on default tools (Memory tools + file operation tools)
        and managed micro-agents to complete tasks
        """
        tools = []

        return tools

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
**SOP Workflow**:
{sop_content}

**Task Execution Principles**:
- Progressive Solutions: Start with minimal changes, gradually expand
- Validation-Driven Development: Immediately validate after each modification
- Quality Assurance: Ensure no new regression problems are introduced

**User Original Task**: {task}

Please strictly follow the above SOP process and coordination strategy to generate detailed execution plans and coordinate micro-agents to complete the task.
"""
        return enhanced_task
