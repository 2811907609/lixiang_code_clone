"""
TelemetryCollector implementation for collecting telemetry data from agents and tools.

This module provides the primary interface for collecting telemetry data across
the SOP Agents system, including token usage tracking, execution time measurement,
task metadata collection, and environment information gathering.
"""

import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
import threading

from .types import (
    TaskStatus,
    AgentType,
    TelemetrySession,
    TaskExecution,
    EnvironmentInfo,
    AgentExecution,
    ToolExecution,
    LLMCall,
    CodeMetrics,
)
from .error_handler import (
    safe_telemetry_call,
    with_fallback_data,
    create_fallback_session,
)


logger = logging.getLogger(__name__)


class TelemetryCollector:
    """
    Primary interface for collecting telemetry data from agents and tools.

    This class provides methods for recording different types of telemetry data
    including token usage, execution times, task metadata, and environment information.
    It's designed to be thread-safe and fail-safe, never blocking core functionality.
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the telemetry collector.

        Args:
            session_id: Optional session ID. If not provided, a new UUID will be generated.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self._lock = threading.RLock()

        # Active tracking
        self._active_tasks: Dict[str, TaskExecution] = {}
        self._active_agents: Dict[str, AgentExecution] = {}
        self._active_tools: Dict[str, ToolExecution] = {}

        # Session data
        self._session = TelemetrySession(
            session_id=self.session_id,
            start_time=datetime.now(timezone.utc),
            environment=self._collect_environment_info(),
        )

        logger.debug(f"TelemetryCollector initialized with session_id: {self.session_id}")

    @with_fallback_data(EnvironmentInfo("unknown", "unknown", "unknown", "unknown", "unknown"))
    def _collect_environment_info(self) -> EnvironmentInfo:
        """Collect environment information for the current system."""
        # Get working directory and project root
        working_dir = str(Path.cwd())
        project_root = self._find_project_root(Path.cwd())

        # Get user name from environment
        user_name = os.getenv('USER') or os.getenv('USERNAME') or os.getenv('LOGNAME')

        # Get timezone
        try:
            import time
            timezone_name = time.tzname[0] if time.tzname else "UTC"
        except (AttributeError, IndexError, ImportError):
            timezone_name = "UTC"

        # Collect relevant environment variables
        env_vars = {}
        relevant_vars = ['PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'HOME', 'PWD']
        for var in relevant_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value

        return EnvironmentInfo(
            os_type=platform.system(),
            os_version=platform.release(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            working_directory=working_dir,
            project_root=project_root,
            user_name=user_name,
            timezone=timezone_name,
            environment_variables=env_vars,
        )

    def _find_project_root(self, start_path: Path) -> str:
        """Find the project root by looking for common project markers."""
        try:
            current = start_path.resolve()
            markers = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt']

            while current != current.parent:
                for marker in markers:
                    if (current / marker).exists():
                        return str(current)
                current = current.parent

            # If no markers found, return the starting directory
            return str(start_path)
        except Exception:
            return str(start_path)

    @safe_telemetry_call("start_supervisor_task")
    def start_supervisor_task(
        self,
        task_id: str,
        description: str,
        agent_name: str,
        sop_category: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> str:
        """
        Start tracking a supervisor agent task (convenience method).

        This method combines start_task and start_agent_execution for supervisor agents.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable description of the task
            agent_name: Name of the supervisor agent
            sop_category: SOP category/workflow being used
            task_type: Type of task (e.g., "code_generation", "bug_fix")

        Returns:
            Agent execution ID for later use in end_supervisor_task
        """
        # Start task tracking
        self.start_task(task_id, description, sop_category, task_type)

        # Start agent execution tracking
        agent_execution_id = f"{task_id}_supervisor_{agent_name}"
        self.start_agent_execution(
            agent_id=agent_execution_id,
            agent_type=AgentType.SUPERVISOR,
            agent_name=agent_name,
            task_id=task_id
        )

        return agent_execution_id

    @safe_telemetry_call("end_supervisor_task")
    def end_supervisor_task(
        self,
        task_id: str,
        agent_execution_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """
        End tracking for a supervisor agent task (convenience method).

        This method combines end_agent_execution and end_task for supervisor agents.

        Args:
            task_id: Unique identifier for the task
            agent_execution_id: Agent execution ID returned from start_supervisor_task
            status: Final status of the task/agent execution
            error_message: Optional error message if task failed
        """
        # End agent execution tracking
        self.end_agent_execution(
            agent_id=agent_execution_id,
            status=status,
            task_id=task_id,
            error_message=error_message
        )

        # End task tracking
        self.end_task(
            task_id=task_id,
            status=status,
            error_message=error_message
        )

    @safe_telemetry_call("start_task")
    def start_task(
        self,
        task_id: str,
        description: str,
        sop_category: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> None:
        """
        Start tracking a new task.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable description of the task
            sop_category: SOP category/workflow being used
            task_type: Type of task (e.g., "code_generation", "bug_fix")
        """
        with self._lock:
            if task_id in self._active_tasks:
                logger.warning(f"Task {task_id} is already active")
                return

            task = TaskExecution(
                task_id=task_id,
                description=description,
                start_time=datetime.now(timezone.utc),
                status=TaskStatus.IN_PROGRESS,
                sop_category=sop_category,
            )

            self._active_tasks[task_id] = task
            logger.debug(f"Started tracking task: {task_id}")

    @safe_telemetry_call("end_task")
    def end_task(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        code_changes: Optional[CodeMetrics] = None,
    ) -> None:
        """
        End tracking for a task.

        Args:
            task_id: Unique identifier for the task
            status: Final status of the task
            error_message: Optional error message if task failed
            code_changes: Optional code metrics for the task
        """
        with self._lock:
            if task_id not in self._active_tasks:
                logger.warning(f"Task {task_id} is not active")
                return

            task = self._active_tasks[task_id]
            task.end_time = datetime.now(timezone.utc)
            task.status = status
            task.error_message = error_message

            if code_changes:
                task.code_changes = code_changes

            # Move to session
            self._session.add_task(task)
            del self._active_tasks[task_id]

            logger.debug(f"Ended tracking task: {task_id} with status: {status.value}")

    @safe_telemetry_call("record_llm_call")
    def record_llm_call(
        self,
        llm_call_or_model: Union[LLMCall, str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        duration: Optional[float] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        cost_estimate: Optional[float] = None,
        model: Optional[str] = None,  # Backward compatibility parameter
    ) -> None:
        """
        Record an LLM call with token usage information.

        Args:
            llm_call_or_model: Either an LLMCall object or model name string
            prompt_tokens: Number of tokens in the prompt (if model string provided)
            completion_tokens: Number of tokens in the completion (if model string provided)
            duration: Time taken for the LLM call in seconds (if model string provided)
            task_id: Optional task ID to associate the call with
            agent_id: Optional agent ID to associate the call with
            cost_estimate: Optional estimated cost of the call (if model string provided)
            model: Backward compatibility parameter for model name
        """
        with self._lock:
            # Handle backward compatibility - if model parameter is provided, use it
            if model is not None and llm_call_or_model is None:
                llm_call_or_model = model

            # Handle both LLMCall objects and individual parameters
            if isinstance(llm_call_or_model, LLMCall):
                llm_call = llm_call_or_model
            else:
                # Create LLMCall from individual parameters
                model_name = llm_call_or_model
                llm_call = LLMCall(
                    model=model_name,
                    prompt_tokens=prompt_tokens or 0,
                    completion_tokens=completion_tokens or 0,
                    total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
                    duration=duration or 0.0,
                    timestamp=datetime.now(timezone.utc),
                    cost_estimate=cost_estimate,
                )

            # Add to appropriate containers
            if agent_id and agent_id in self._active_agents:
                self._active_agents[agent_id].llm_calls.append(llm_call)
            elif task_id and task_id in self._active_tasks:
                self._active_tasks[task_id].llm_calls.append(llm_call)
            else:
                # Add to session level if no specific container
                # Note: This would require adding llm_calls to TelemetrySession
                # For now, we'll add it to the most recent active task
                if self._active_tasks:
                    most_recent_task = max(
                        self._active_tasks.values(),
                        key=lambda t: t.start_time
                    )
                    most_recent_task.llm_calls.append(llm_call)

            logger.debug(f"Recorded LLM call: {llm_call.model}, {llm_call.prompt_tokens}+{llm_call.completion_tokens} tokens")

    def start_agent_execution(
        self,
        agent_id: str,
        agent_type: AgentType,
        agent_name: str,
        task_id: Optional[str] = None,
    ) -> None:
        """
        Start tracking agent execution.

        Args:
            agent_id: Unique identifier for this agent execution
            agent_type: Type of agent (supervisor, micro, etc.)
            agent_name: Human-readable name of the agent
            task_id: Optional task ID to associate the agent with
        """
        try:
            with self._lock:
                if agent_id in self._active_agents:
                    logger.warning(f"Agent {agent_id} is already active")
                    return

                agent = AgentExecution(
                    agent_type=agent_type,
                    agent_name=agent_name,
                    start_time=datetime.now(timezone.utc),
                    status=TaskStatus.IN_PROGRESS,
                )

                self._active_agents[agent_id] = agent
                logger.debug(f"Started tracking agent: {agent_id} ({agent_name})")
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")

    def end_agent_execution(
        self,
        agent_id: str,
        status: TaskStatus,
        task_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        End tracking for agent execution.

        Args:
            agent_id: Unique identifier for the agent execution
            status: Final status of the agent execution
            task_id: Optional task ID to associate the agent with
            error_message: Optional error message if agent failed
        """
        try:
            with self._lock:
                if agent_id not in self._active_agents:
                    logger.warning(f"Agent {agent_id} is not active")
                    return

                agent = self._active_agents[agent_id]
                agent.end_time = datetime.now(timezone.utc)
                agent.status = status
                agent.error_message = error_message

                # Calculate duration
                if agent.end_time and agent.start_time:
                    agent.duration = (agent.end_time - agent.start_time).total_seconds()

                # Add to appropriate task
                if task_id and task_id in self._active_tasks:
                    self._active_tasks[task_id].agents.append(agent)
                else:
                    # Add to most recent active task if no specific task
                    if self._active_tasks:
                        most_recent_task = max(
                            self._active_tasks.values(),
                            key=lambda t: t.start_time
                        )
                        most_recent_task.agents.append(agent)

                del self._active_agents[agent_id]
                logger.debug(f"Ended tracking agent: {agent_id} with status: {status.value}")
        except Exception as e:
            logger.error(f"Failed to end agent {agent_id}: {e}")

    def record_agent_execution(
        self,
        agent_type: str,
        agent_name: str,
        duration: float,
        task_id: Optional[str] = None,
        status: TaskStatus = TaskStatus.COMPLETED,
        llm_calls: Optional[List[LLMCall]] = None,
        tools_used: Optional[List[ToolExecution]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record a completed agent execution (convenience method for short-lived agents).

        Args:
            agent_type: Type of agent as string
            agent_name: Human-readable name of the agent
            duration: Total execution time in seconds
            task_id: Optional task ID to associate the agent with
            status: Final status of the agent execution
            llm_calls: Optional list of LLM calls made by the agent
            tools_used: Optional list of tools used by the agent
            error_message: Optional error message if agent failed
        """
        try:
            # Convert string agent_type to enum
            try:
                agent_type_enum = AgentType(agent_type.lower())
            except ValueError:
                # Default to MICRO if unknown type
                agent_type_enum = AgentType.MICRO
                logger.warning(f"Unknown agent type '{agent_type}', defaulting to MICRO")

            with self._lock:
                end_time = datetime.now(timezone.utc)
                # Calculate start time by subtracting duration
                start_time = datetime.fromtimestamp(
                    end_time.timestamp() - duration,
                    tz=timezone.utc
                )

                agent = AgentExecution(
                    agent_type=agent_type_enum,
                    agent_name=agent_name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    status=status,
                    llm_calls=llm_calls or [],
                    tools_used=tools_used or [],
                    error_message=error_message,
                )

                # Add to appropriate task
                if task_id and task_id in self._active_tasks:
                    self._active_tasks[task_id].agents.append(agent)
                else:
                    # Add to most recent active task if no specific task
                    if self._active_tasks:
                        most_recent_task = max(
                            self._active_tasks.values(),
                            key=lambda t: t.start_time
                        )
                        most_recent_task.agents.append(agent)

                logger.debug(f"Recorded agent execution: {agent_name} ({duration:.2f}s)")
        except Exception as e:
            logger.error(f"Failed to record agent execution: {e}")

    def start_tool_execution(
        self,
        tool_id: str,
        tool_name: str,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Start tracking tool execution.

        Args:
            tool_id: Unique identifier for this tool execution
            tool_name: Name of the tool being executed
            agent_id: Optional agent ID that's using the tool
        """
        try:
            with self._lock:
                if tool_id in self._active_tools:
                    logger.warning(f"Tool {tool_id} is already active")
                    return

                tool = ToolExecution(
                    tool_name=tool_name,
                    start_time=datetime.now(timezone.utc),
                    status=TaskStatus.IN_PROGRESS,
                )

                self._active_tools[tool_id] = tool
                logger.debug(f"Started tracking tool: {tool_id} ({tool_name})")
        except Exception as e:
            logger.error(f"Failed to start tool {tool_id}: {e}")

    def end_tool_execution(
        self,
        tool_id: str,
        status: TaskStatus,
        agent_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        End tracking for tool execution.

        Args:
            tool_id: Unique identifier for the tool execution
            status: Final status of the tool execution
            agent_id: Optional agent ID that was using the tool
            error_message: Optional error message if tool failed
        """
        try:
            with self._lock:
                if tool_id not in self._active_tools:
                    logger.warning(f"Tool {tool_id} is not active")
                    return

                tool = self._active_tools[tool_id]
                tool.end_time = datetime.now(timezone.utc)
                tool.status = status
                tool.error_message = error_message

                # Calculate duration
                if tool.end_time and tool.start_time:
                    tool.duration = (tool.end_time - tool.start_time).total_seconds()

                # Add to appropriate agent
                if agent_id and agent_id in self._active_agents:
                    self._active_agents[agent_id].tools_used.append(tool)
                else:
                    # Add to most recent active task if no specific agent
                    if self._active_tasks:
                        most_recent_task = max(
                            self._active_tasks.values(),
                            key=lambda t: t.start_time
                        )
                        most_recent_task.tools.append(tool)

                del self._active_tools[tool_id]
                logger.debug(f"Ended tracking tool: {tool_id} with status: {status.value}")
        except Exception as e:
            logger.error(f"Failed to end tool {tool_id}: {e}")

    def record_tool_usage(
        self,
        tool_name: str,
        duration: float,
        agent_id: Optional[str] = None,
        status: TaskStatus = TaskStatus.COMPLETED,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record a completed tool usage (convenience method for short-lived tools).

        Args:
            tool_name: Name of the tool that was used
            duration: Total execution time in seconds
            agent_id: Optional agent ID that used the tool
            status: Final status of the tool execution
            error_message: Optional error message if tool failed
        """
        try:
            with self._lock:
                end_time = datetime.now(timezone.utc)
                # Calculate start time by subtracting duration
                start_time = datetime.fromtimestamp(
                    end_time.timestamp() - duration,
                    tz=timezone.utc
                )

                tool = ToolExecution(
                    tool_name=tool_name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    status=status,
                    error_message=error_message,
                )

                # Add to appropriate agent
                if agent_id and agent_id in self._active_agents:
                    self._active_agents[agent_id].tools_used.append(tool)
                else:
                    # Add to most recent active task if no specific agent
                    if self._active_tasks:
                        most_recent_task = max(
                            self._active_tasks.values(),
                            key=lambda t: t.start_time
                        )
                        most_recent_task.tools.append(tool)

                logger.debug(f"Recorded tool usage: {tool_name} ({duration:.2f}s)")
        except Exception as e:
            logger.error(f"Failed to record tool usage: {e}")

    def record_code_changes(
        self,
        task_id: str,
        files_created: int = 0,
        files_modified: int = 0,
        files_deleted: int = 0,
        lines_added: int = 0,
        lines_removed: int = 0,
        lines_modified: int = 0,
    ) -> None:
        """
        Record code changes for a task.

        Args:
            task_id: Task ID to associate the code changes with
            files_created: Number of files created
            files_modified: Number of files modified
            files_deleted: Number of files deleted
            lines_added: Number of lines added
            lines_removed: Number of lines removed
            lines_modified: Number of lines modified
        """
        try:
            with self._lock:
                if task_id not in self._active_tasks:
                    logger.warning(f"Task {task_id} is not active")
                    return

                task = self._active_tasks[task_id]
                task.code_changes = CodeMetrics(
                    files_created=files_created,
                    files_modified=files_modified,
                    files_deleted=files_deleted,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    lines_modified=lines_modified,
                )

                logger.debug(f"Recorded code changes for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to record code changes for task {task_id}: {e}")

    @with_fallback_data(None)
    def get_session_data(self) -> TelemetrySession:
        """
        Get the current session data.

        Returns:
            TelemetrySession object with all collected data
        """
        with self._lock:
            # Create a copy of the session to avoid external modifications
            session_copy = TelemetrySession(
                session_id=self._session.session_id,
                start_time=self._session.start_time,
                end_time=self._session.end_time,
                environment=self._session.environment,
                tasks=self._session.tasks.copy(),
                total_tokens=self._session.total_tokens,
                total_duration=self._session.total_duration,
            )
            return session_copy or create_fallback_session(self.session_id)

    def get_active_tasks(self) -> Dict[str, TaskExecution]:
        """Get currently active tasks."""
        try:
            with self._lock:
                return self._active_tasks.copy()
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return {}

    def get_active_agents(self) -> Dict[str, AgentExecution]:
        """Get currently active agents."""
        try:
            with self._lock:
                return self._active_agents.copy()
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return {}

    def get_active_tools(self) -> Dict[str, ToolExecution]:
        """Get currently active tools."""
        try:
            with self._lock:
                return self._active_tools.copy()
        except Exception as e:
            logger.error(f"Failed to get active tools: {e}")
            return {}

    def finalize_session(self) -> TelemetrySession:
        """
        Finalize the session and return the complete data.

        This method should be called when the session is ending to ensure
        all active items are properly closed.

        Returns:
            Complete TelemetrySession object
        """
        try:
            with self._lock:
                # End any remaining active tasks
                for task_id, task in list(self._active_tasks.items()):
                    task.end_time = datetime.now(timezone.utc)
                    task.status = TaskStatus.PARTIAL  # Mark as partial since not explicitly ended
                    self._session.add_task(task)
                    del self._active_tasks[task_id]

                # End any remaining active agents
                for agent_id, agent in list(self._active_agents.items()):
                    agent.end_time = datetime.now(timezone.utc)
                    agent.status = TaskStatus.PARTIAL
                    # Add to most recent task if available
                    if self._session.tasks:
                        self._session.tasks[-1].agents.append(agent)
                    del self._active_agents[agent_id]

                # End any remaining active tools
                for tool_id, tool in list(self._active_tools.items()):
                    tool.end_time = datetime.now(timezone.utc)
                    tool.status = TaskStatus.PARTIAL
                    # Add to most recent task if available
                    if self._session.tasks:
                        self._session.tasks[-1].tools.append(tool)
                    del self._active_tools[tool_id]

                # Set session end time
                self._session.end_time = datetime.now(timezone.utc)

                logger.debug(f"Finalized session {self.session_id}")
                return self._session
        except Exception as e:
            logger.error(f"Failed to finalize session: {e}")
            return self._session
