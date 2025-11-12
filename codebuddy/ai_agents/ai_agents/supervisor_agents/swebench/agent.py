"""
SWE-Bench Agent - Specialized for software engineering benchmark tasks
"""

from pathlib import Path

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent
from ai_agents.micro_agents.yaml_agent_factory import YamlAgentFactory
from ai_agents.sop_workflows.sop_manager import get_sop

# SWE-Bench SOP workflow directory path
_swebench_sop_path = Path(__file__).parent.parent.parent / "sop_workflows" / "swebench"


class SWEBenchSupervisorAgent(BaseSupervisorAgent):
    """
    SWE-Bench Task Execution Supervisor Agent

    This agent specializes in handling SWE-Bench (Software Engineering Benchmark) tasks,
    coordinating multiple specialized micro-agents to solve complex software engineering problems.

    Main Responsibilities:
    - Problem Analysis: Understanding SWE-Bench task descriptions and reproduction steps
    - Solution Design: Creating progressive fix solutions
    - Code Operations: Coordinating code search, analysis and modifications
    - Test Validation: Ensuring fixes work correctly without regressions
    - Quality Assurance: Ensuring fixes don't introduce new problems

    Core Workflow:
    1. Deeply analyze problem descriptions and error messages
    2. Search, locate and analyze relevant code files and modules
    3. Design minimal fix solutions
    4. Implement code modifications with integrated search-edit workflow
    5. Validate fix effectiveness and regression testing
    6. Generate comprehensive solution reports
    """

    with_memory = False
    tool_call_type = "tool_call" # tool_call, code_act
    max_steps = 100

    @property
    def name(self) -> str:
        return "swe_bench_supervisor"

    @property
    def sop_category(self) -> str:
        return "swebench"

    @property
    def default_task_type(self) -> str:
        # SWE-Bench tasks require complex reasoning and code analysis capabilities
        return "complex_reasoning"

    def __init__(self,
                 model=None,
                 execution_env=None,
                 execution_env_config=None,
                 logger: AgentLogger=None):
        """
        Initialize SWE-Bench Supervisor Agent

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

        # Load all micro-agents from the micro_agents folder
        micro_agents_folder = _swebench_sop_path / 'micro_agents'
        if micro_agents_folder.exists():
            micro_agent_tools = YamlAgentFactory.create_agents_as_tools_from_folder(
                micro_agents_folder,
                memory=self._memory,
                execution_env=self._execution_env,
                logger=self._logger
            )
            tools.extend(micro_agent_tools)

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
As {self.name} supervisor agent, your core responsibility is coordinating micro-agent teams to complete SWE-Bench tasks.

**SOP Workflow**:
{sop_content}

**Task Execution Principles**:
- Progressive Solutions: Start with minimal changes, gradually expand
- Validation-Driven Development: Immediately validate after each modification
- Quality Assurance: Ensure no new regression problems are introduced

**Micro-Agent Coordination Strategy**:
1. **AnalysisAgent**: Responsible for problem understanding, solution design, failure cause analysis, and basic search assistance
2. **CodeOperationAgent**: Responsible for code search, location, deep analysis, and code modifications while maintaining style consistency
3. **TestAgent**: Responsible for test execution, validation, and regression testing

**Core Instructions**:
1. **Strictly follow SOP process**: Don't skip problem analysis and directly modify code
2. **Task decomposition and delegation**: Break complex tasks into specific steps executable by micro-agents
3. **Result validation and integration**: Validate micro-agent results to ensure task completion quality
4. **Clear communication**: When delegating tasks, clearly inform micro-agents of specific execution requirements and expected results

**User Original Task**: {task}

Please strictly follow the above SOP process and coordination strategy to generate detailed execution plans and coordinate micro-agents to complete the task.
"""
        return enhanced_task
