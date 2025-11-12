"""
Tests for TelemetryCollector implementation.

This module tests the telemetry collection functionality including token usage tracking,
execution time measurement, task metadata collection, and environment information gathering.
"""

import os
import platform
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

from ai_agents.telemetry.collector import TelemetryCollector
from ai_agents.telemetry.types import (
    TaskStatus,
    AgentType,
    TelemetrySession,
    EnvironmentInfo,
    CodeMetrics,
)


class TestTelemetryCollector:
    """Test cases for TelemetryCollector."""

    def test_initialization(self):
        """Test TelemetryCollector initialization."""
        collector = TelemetryCollector()

        # Check that session_id is generated
        assert collector.session_id is not None
        assert len(collector.session_id) > 0

        # Check that session is initialized
        session = collector.get_session_data()
        assert isinstance(session, TelemetrySession)
        assert session.session_id == collector.session_id
        assert session.start_time is not None
        assert isinstance(session.environment, EnvironmentInfo)

    def test_initialization_with_session_id(self):
        """Test TelemetryCollector initialization with provided session ID."""
        session_id = "test-session-123"
        collector = TelemetryCollector(session_id=session_id)

        assert collector.session_id == session_id
        session = collector.get_session_data()
        assert session.session_id == session_id

    def test_environment_info_collection(self):
        """Test environment information collection."""
        collector = TelemetryCollector()
        session = collector.get_session_data()
        env = session.environment

        # Check basic environment info
        assert env.os_type == platform.system()
        assert env.os_version == platform.release()
        assert env.python_version.startswith(f"{sys.version_info.major}.{sys.version_info.minor}")
        assert env.working_directory == str(Path.cwd())
        assert env.project_root is not None

        # Check environment variables
        assert isinstance(env.environment_variables, dict)
        if 'PATH' in os.environ:
            assert 'PATH' in env.environment_variables

    @patch('ai_agents.telemetry.collector.platform.system')
    @patch('ai_agents.telemetry.collector.platform.release')
    def test_environment_info_collection_error_handling(self, mock_release, mock_system):
        """Test environment info collection with errors."""
        # Simulate platform errors
        mock_system.side_effect = Exception("Platform error")
        mock_release.side_effect = Exception("Release error")

        collector = TelemetryCollector()
        session = collector.get_session_data()
        env = session.environment

        # Should have fallback values
        assert env.os_type == "unknown"
        assert env.os_version == "unknown"
        assert env.python_version == "unknown"

    def test_project_root_detection(self):
        """Test project root detection logic."""
        collector = TelemetryCollector()

        # Test with current directory (should find .git or other markers)
        project_root = collector._find_project_root(Path.cwd())
        assert isinstance(project_root, str)
        assert Path(project_root).exists()

    def test_start_and_end_task(self):
        """Test task lifecycle tracking."""
        collector = TelemetryCollector()
        task_id = "test-task-1"
        description = "Test task description"
        sop_category = "test_sop"

        # Start task
        collector.start_task(task_id, description, sop_category=sop_category)

        # Check active tasks
        active_tasks = collector.get_active_tasks()
        assert task_id in active_tasks
        task = active_tasks[task_id]
        assert task.task_id == task_id
        assert task.description == description
        assert task.sop_category == sop_category
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.start_time is not None
        assert task.end_time is None

        # End task
        code_changes = CodeMetrics(files_created=2, lines_added=100)
        collector.end_task(task_id, TaskStatus.COMPLETED, code_changes=code_changes)

        # Check task is no longer active
        active_tasks = collector.get_active_tasks()
        assert task_id not in active_tasks

        # Check task is in session
        session = collector.get_session_data()
        assert len(session.tasks) == 1
        completed_task = session.tasks[0]
        assert completed_task.task_id == task_id
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.end_time is not None
        assert completed_task.code_changes.files_created == 2
        assert completed_task.code_changes.lines_added == 100

    def test_start_task_duplicate(self):
        """Test starting a task that's already active."""
        collector = TelemetryCollector()
        task_id = "duplicate-task"

        # Start task twice
        collector.start_task(task_id, "First description")
        collector.start_task(task_id, "Second description")

        # Should only have one active task
        active_tasks = collector.get_active_tasks()
        assert len(active_tasks) == 1
        assert active_tasks[task_id].description == "First description"

    def test_end_task_not_active(self):
        """Test ending a task that's not active."""
        collector = TelemetryCollector()

        # Try to end non-existent task
        collector.end_task("non-existent", TaskStatus.COMPLETED)

        # Should not crash and session should be empty
        session = collector.get_session_data()
        assert len(session.tasks) == 0

    def test_record_llm_call(self):
        """Test LLM call recording."""
        collector = TelemetryCollector()
        task_id = "test-task"

        # Start a task first
        collector.start_task(task_id, "Test task")

        # Record LLM call
        model = "gpt-4"
        prompt_tokens = 100
        completion_tokens = 50
        duration = 2.5
        cost_estimate = 0.01

        collector.record_llm_call(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration=duration,
            task_id=task_id,
            cost_estimate=cost_estimate,
        )

        # Check LLM call was recorded
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        assert len(task.llm_calls) == 1

        llm_call = task.llm_calls[0]
        assert llm_call.model == model
        assert llm_call.prompt_tokens == prompt_tokens
        assert llm_call.completion_tokens == completion_tokens
        assert llm_call.total_tokens == prompt_tokens + completion_tokens
        assert llm_call.duration == duration
        assert llm_call.cost_estimate == cost_estimate
        assert llm_call.timestamp is not None

    def test_record_llm_call_without_task(self):
        """Test LLM call recording without specific task."""
        collector = TelemetryCollector()

        # Start a task to receive the LLM call
        collector.start_task("background-task", "Background task")

        # Record LLM call without specifying task_id
        collector.record_llm_call(
            model="gpt-3.5-turbo",
            prompt_tokens=50,
            completion_tokens=25,
            duration=1.0,
        )

        # Should be added to the most recent task
        active_tasks = collector.get_active_tasks()
        task = list(active_tasks.values())[0]
        assert len(task.llm_calls) == 1

    def test_agent_execution_lifecycle(self):
        """Test agent execution tracking."""
        collector = TelemetryCollector()
        task_id = "test-task"
        agent_id = "test-agent-1"
        agent_name = "TestAgent"
        agent_type = AgentType.SUPERVISOR

        # Start task and agent
        collector.start_task(task_id, "Test task")
        collector.start_agent_execution(agent_id, agent_type, agent_name, task_id)

        # Check active agents
        active_agents = collector.get_active_agents()
        assert agent_id in active_agents
        agent = active_agents[agent_id]
        assert agent.agent_name == agent_name
        assert agent.agent_type == agent_type
        assert agent.status == TaskStatus.IN_PROGRESS

        # End agent
        collector.end_agent_execution(agent_id, TaskStatus.COMPLETED, task_id)

        # Check agent is no longer active
        active_agents = collector.get_active_agents()
        assert agent_id not in active_agents

        # Check agent is in task
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        assert len(task.agents) == 1
        completed_agent = task.agents[0]
        assert completed_agent.agent_name == agent_name
        assert completed_agent.status == TaskStatus.COMPLETED
        assert completed_agent.end_time is not None

    def test_record_agent_execution_convenience_method(self):
        """Test the convenience method for recording agent execution."""
        collector = TelemetryCollector()
        task_id = "test-task"

        collector.start_task(task_id, "Test task")

        # Record agent execution with convenience method
        agent_type = "supervisor"
        agent_name = "QuickAgent"
        duration = 5.0

        collector.record_agent_execution(
            agent_type=agent_type,
            agent_name=agent_name,
            duration=duration,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
        )

        # Check agent was recorded
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        assert len(task.agents) == 1

        agent = task.agents[0]
        assert agent.agent_name == agent_name
        assert agent.agent_type == AgentType.SUPERVISOR
        assert agent.duration == duration
        assert agent.status == TaskStatus.COMPLETED

    def test_record_agent_execution_unknown_type(self):
        """Test recording agent execution with unknown agent type."""
        collector = TelemetryCollector()
        task_id = "test-task"

        collector.start_task(task_id, "Test task")

        # Record with unknown agent type
        collector.record_agent_execution(
            agent_type="unknown_type",
            agent_name="UnknownAgent",
            duration=1.0,
            task_id=task_id,
        )

        # Should default to MICRO
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        agent = task.agents[0]
        assert agent.agent_type == AgentType.MICRO

    def test_tool_execution_lifecycle(self):
        """Test tool execution tracking."""
        collector = TelemetryCollector()
        agent_id = "test-agent"
        tool_id = "test-tool-1"
        tool_name = "TestTool"

        # Start agent and tool
        collector.start_agent_execution(agent_id, AgentType.MICRO, "TestAgent")
        collector.start_tool_execution(tool_id, tool_name, agent_id)

        # Check active tools
        active_tools = collector.get_active_tools()
        assert tool_id in active_tools
        tool = active_tools[tool_id]
        assert tool.tool_name == tool_name
        assert tool.status == TaskStatus.IN_PROGRESS

        # End tool
        collector.end_tool_execution(tool_id, TaskStatus.COMPLETED, agent_id)

        # Check tool is no longer active
        active_tools = collector.get_active_tools()
        assert tool_id not in active_tools

        # Check tool is in agent
        active_agents = collector.get_active_agents()
        agent = active_agents[agent_id]
        assert len(agent.tools_used) == 1
        completed_tool = agent.tools_used[0]
        assert completed_tool.tool_name == tool_name
        assert completed_tool.status == TaskStatus.COMPLETED

    def test_record_tool_usage_convenience_method(self):
        """Test the convenience method for recording tool usage."""
        collector = TelemetryCollector()
        task_id = "test-task"

        collector.start_task(task_id, "Test task")

        # Record tool usage with convenience method
        tool_name = "QuickTool"
        duration = 2.0

        collector.record_tool_usage(
            tool_name=tool_name,
            duration=duration,
            status=TaskStatus.COMPLETED,
        )

        # Check tool was recorded in task
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        assert len(task.tools) == 1

        tool = task.tools[0]
        assert tool.tool_name == tool_name
        assert tool.duration == duration
        assert tool.status == TaskStatus.COMPLETED

    def test_record_code_changes(self):
        """Test code changes recording."""
        collector = TelemetryCollector()
        task_id = "test-task"

        collector.start_task(task_id, "Test task")

        # Record code changes
        collector.record_code_changes(
            task_id=task_id,
            files_created=3,
            files_modified=2,
            files_deleted=1,
            lines_added=150,
            lines_removed=50,
            lines_modified=25,
        )

        # Check code changes were recorded
        active_tasks = collector.get_active_tasks()
        task = active_tasks[task_id]
        code_changes = task.code_changes

        assert code_changes.files_created == 3
        assert code_changes.files_modified == 2
        assert code_changes.files_deleted == 1
        assert code_changes.lines_added == 150
        assert code_changes.lines_removed == 50
        assert code_changes.lines_modified == 25

    def test_record_code_changes_invalid_task(self):
        """Test recording code changes for invalid task."""
        collector = TelemetryCollector()

        # Try to record code changes for non-existent task
        collector.record_code_changes("non-existent", files_created=1)

        # Should not crash
        session = collector.get_session_data()
        assert len(session.tasks) == 0

    def test_finalize_session(self):
        """Test session finalization."""
        collector = TelemetryCollector()
        task_id = "test-task"
        agent_id = "test-agent"
        tool_id = "test-tool"

        # Start some active items
        collector.start_task(task_id, "Test task")
        collector.start_agent_execution(agent_id, AgentType.MICRO, "TestAgent")
        collector.start_tool_execution(tool_id, "TestTool")

        # Finalize session
        final_session = collector.finalize_session()

        # Check that all active items were finalized
        assert len(collector.get_active_tasks()) == 0
        assert len(collector.get_active_agents()) == 0
        assert len(collector.get_active_tools()) == 0

        # Check session has the finalized data
        assert final_session.end_time is not None
        assert len(final_session.tasks) == 1

        task = final_session.tasks[0]
        assert task.status == TaskStatus.PARTIAL  # Since not explicitly ended
        assert len(task.agents) == 1
        assert len(task.tools) == 1

    def test_complex_workflow(self):
        """Test a complex workflow with multiple agents and tools."""
        collector = TelemetryCollector()

        # Start main task
        main_task_id = "main-task"
        collector.start_task(main_task_id, "Complex workflow task", sop_category="complex_sop")

        # Start supervisor agent
        supervisor_id = "supervisor-1"
        collector.start_agent_execution(supervisor_id, AgentType.SUPERVISOR, "MainSupervisor", main_task_id)

        # Record LLM call for supervisor
        collector.record_llm_call(
            model="gpt-4",
            prompt_tokens=200,
            completion_tokens=100,
            duration=3.0,
            agent_id=supervisor_id,
        )

        # Start micro agent
        micro_id = "micro-1"
        collector.start_agent_execution(micro_id, AgentType.MICRO, "CodeAgent", main_task_id)

        # Record tool usage for micro agent
        collector.record_tool_usage(
            tool_name="file_editor",
            duration=1.5,
            agent_id=micro_id,
        )

        # Record LLM call for micro agent
        collector.record_llm_call(
            model="gpt-3.5-turbo",
            prompt_tokens=150,
            completion_tokens=75,
            duration=2.0,
            agent_id=micro_id,
        )

        # End agents
        collector.end_agent_execution(supervisor_id, TaskStatus.COMPLETED, main_task_id)
        collector.end_agent_execution(micro_id, TaskStatus.COMPLETED, main_task_id)

        # Record code changes
        collector.record_code_changes(
            task_id=main_task_id,
            files_created=2,
            lines_added=200,
        )

        # End main task
        collector.end_task(main_task_id, TaskStatus.COMPLETED)

        # Verify the complete workflow
        session = collector.get_session_data()
        assert len(session.tasks) == 1

        task = session.tasks[0]
        assert task.task_id == main_task_id
        assert task.sop_category == "complex_sop"
        assert task.status == TaskStatus.COMPLETED
        assert len(task.agents) == 2
        assert len(task.llm_calls) == 0  # LLM calls should be in agents
        assert task.code_changes.files_created == 2
        assert task.code_changes.lines_added == 200

        # Check supervisor agent
        supervisor = next(a for a in task.agents if a.agent_type == AgentType.SUPERVISOR)
        assert supervisor.agent_name == "MainSupervisor"
        assert len(supervisor.llm_calls) == 1
        assert supervisor.llm_calls[0].model == "gpt-4"

        # Check micro agent
        micro = next(a for a in task.agents if a.agent_type == AgentType.MICRO)
        assert micro.agent_name == "CodeAgent"
        assert len(micro.llm_calls) == 1
        assert len(micro.tools_used) == 1
        assert micro.llm_calls[0].model == "gpt-3.5-turbo"
        assert micro.tools_used[0].tool_name == "file_editor"

    def test_error_handling(self):
        """Test error handling in various methods."""
        collector = TelemetryCollector()

        # These should not crash even with invalid inputs
        collector.start_task("", "")  # Empty strings
        collector.end_task("non-existent", TaskStatus.COMPLETED)
        collector.record_llm_call("", 0, 0, 0.0)
        collector.start_agent_execution("", AgentType.MICRO, "")
        collector.end_agent_execution("non-existent", TaskStatus.COMPLETED)
        collector.record_agent_execution("", "", 0.0)
        collector.start_tool_execution("", "")
        collector.end_tool_execution("non-existent", TaskStatus.COMPLETED)
        collector.record_tool_usage("", 0.0)
        collector.record_code_changes("non-existent")

        # Session should still be valid
        session = collector.get_session_data()
        assert isinstance(session, TelemetrySession)

    def test_thread_safety_basic(self):
        """Basic test for thread safety (more comprehensive tests would require threading)."""
        collector = TelemetryCollector()

        # Multiple rapid operations should not cause issues
        for i in range(10):
            task_id = f"task-{i}"
            collector.start_task(task_id, f"Task {i}")
            collector.record_llm_call(f"model-{i}", 10, 5, 0.1, task_id=task_id)
            collector.end_task(task_id, TaskStatus.COMPLETED)

        session = collector.get_session_data()
        assert len(session.tasks) == 10

    def test_get_methods(self):
        """Test the various get methods."""
        collector = TelemetryCollector()

        # Initially empty
        assert len(collector.get_active_tasks()) == 0
        assert len(collector.get_active_agents()) == 0
        assert len(collector.get_active_tools()) == 0

        # Add some active items
        collector.start_task("task-1", "Test task")
        collector.start_agent_execution("agent-1", AgentType.MICRO, "TestAgent")
        collector.start_tool_execution("tool-1", "TestTool")

        # Check get methods return copies (modifications shouldn't affect internal state)
        active_tasks = collector.get_active_tasks()
        active_agents = collector.get_active_agents()
        active_tools = collector.get_active_tools()

        assert len(active_tasks) == 1
        assert len(active_agents) == 1
        assert len(active_tools) == 1

        # Modify returned dictionaries
        active_tasks.clear()
        active_agents.clear()
        active_tools.clear()

        # Internal state should be unchanged
        assert len(collector.get_active_tasks()) == 1
        assert len(collector.get_active_agents()) == 1
        assert len(collector.get_active_tools()) == 1


class TestTelemetryCollectorIntegration:
    """Integration tests for TelemetryCollector with real environment."""

    def test_real_environment_collection(self):
        """Test collection with real environment (no mocking)."""
        collector = TelemetryCollector()
        session = collector.get_session_data()
        env = session.environment

        # Should have real values
        assert env.os_type in ["Windows", "Linux", "Darwin"]
        assert len(env.python_version) > 0
        assert Path(env.working_directory).exists()
        assert Path(env.project_root).exists()

    def test_session_data_serialization(self):
        """Test that collected data can be serialized."""
        collector = TelemetryCollector()

        # Create some test data
        collector.start_task("test-task", "Serialization test")
        collector.record_llm_call("gpt-4", 100, 50, 2.0, task_id="test-task")
        collector.end_task("test-task", TaskStatus.COMPLETED)

        # Get session and test serialization
        session = collector.get_session_data()

        # Should be able to convert to dict and JSON
        session_dict = session.to_dict()
        assert isinstance(session_dict, dict)
        assert "session_id" in session_dict
        assert "tasks" in session_dict

        session_json = session.to_json()
        assert isinstance(session_json, str)
        assert len(session_json) > 0

        # Should be able to deserialize
        restored_session = TelemetrySession.from_json(session_json)
        assert restored_session.session_id == session.session_id
        assert len(restored_session.tasks) == len(session.tasks)


if __name__ == "__main__":
    pytest.main([__file__])
