"""
Tests for telemetry data structures and types.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_agents.telemetry.types import (
    TaskStatus,
    AgentType,
    TokenUsage,
    EnvironmentInfo,
    LLMCall,
    AgentExecution,
    TaskExecution,
    TelemetrySession,
    serialize_telemetry_data,
    deserialize_telemetry_data,
)


class TestTokenUsage:
    """Test TokenUsage data structure."""

    def test_token_usage_creation(self):
        """Test basic TokenUsage creation."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_addition(self):
        """Test adding TokenUsage instances."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=75)

        usage1.add_usage(usage2)

        assert usage1.prompt_tokens == 300
        assert usage1.completion_tokens == 125
        assert usage1.total_tokens == 425

    def test_token_usage_serialization(self):
        """Test TokenUsage serialization/deserialization."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            cost_estimate=0.05
        )

        # Test to_dict
        data = usage.to_dict()
        assert data["prompt_tokens"] == 100
        assert data["completion_tokens"] == 50
        assert data["total_tokens"] == 150
        assert data["cost_estimate"] == 0.05

        # Test from_dict
        restored = TokenUsage.from_dict(data)
        assert restored.prompt_tokens == usage.prompt_tokens
        assert restored.completion_tokens == usage.completion_tokens
        assert restored.total_tokens == usage.total_tokens
        assert restored.cost_estimate == usage.cost_estimate


class TestEnvironmentInfo:
    """Test EnvironmentInfo data structure."""

    def test_environment_info_creation(self):
        """Test EnvironmentInfo creation."""
        env = EnvironmentInfo(
            os_type="Linux",
            os_version="Ubuntu 20.04",
            python_version="3.9.0",
            working_directory="/home/user/project",
            project_root="/home/user/project",
            user_name="testuser"
        )

        assert env.os_type == "Linux"
        assert env.user_name == "testuser"

    def test_environment_info_serialization(self):
        """Test EnvironmentInfo serialization."""
        env = EnvironmentInfo(
            os_type="Linux",
            os_version="Ubuntu 20.04",
            python_version="3.9.0",
            working_directory="/home/user/project",
            project_root="/home/user/project"
        )

        data = env.to_dict()
        restored = EnvironmentInfo.from_dict(data)

        assert restored.os_type == env.os_type
        assert restored.os_version == env.os_version
        assert restored.python_version == env.python_version


class TestLLMCall:
    """Test LLMCall data structure."""

    def test_llm_call_creation(self):
        """Test LLMCall creation."""
        now = datetime.now()
        call = LLMCall(
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            duration=2.5,
            timestamp=now
        )

        assert call.model == "gpt-4"
        assert call.duration == 2.5
        assert call.timestamp == now

    def test_llm_call_serialization(self):
        """Test LLMCall serialization."""
        now = datetime.now()
        call = LLMCall(
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            duration=2.5,
            timestamp=now
        )

        data = call.to_dict()
        restored = LLMCall.from_dict(data)

        assert restored.model == call.model
        assert restored.prompt_tokens == call.prompt_tokens
        assert restored.duration == call.duration
        # Note: datetime comparison might have microsecond differences
        assert abs((restored.timestamp - call.timestamp).total_seconds()) < 1


class TestTaskExecution:
    """Test TaskExecution data structure."""

    def test_task_execution_creation(self):
        """Test TaskExecution creation."""
        now = datetime.now()
        task = TaskExecution(
            task_id="task-123",
            description="Test task",
            start_time=now,
            status=TaskStatus.IN_PROGRESS
        )

        assert task.task_id == "task-123"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.start_time == now

    def test_task_execution_with_agents(self):
        """Test TaskExecution with agents."""
        now = datetime.now()

        agent = AgentExecution(
            agent_type=AgentType.SUPERVISOR,
            agent_name="test-agent",
            start_time=now,
            status=TaskStatus.COMPLETED
        )

        task = TaskExecution(
            task_id="task-123",
            description="Test task",
            start_time=now,
            agents=[agent]
        )

        assert len(task.agents) == 1
        assert task.agents[0].agent_name == "test-agent"

    def test_task_execution_serialization(self):
        """Test TaskExecution serialization."""
        now = datetime.now()
        task = TaskExecution(
            task_id="task-123",
            description="Test task",
            start_time=now,
            status=TaskStatus.COMPLETED,
            sop_category="test-sop"
        )

        data = task.to_dict()
        restored = TaskExecution.from_dict(data)

        assert restored.task_id == task.task_id
        assert restored.description == task.description
        assert restored.status == task.status
        assert restored.sop_category == task.sop_category


class TestTelemetrySession:
    """Test TelemetrySession data structure."""

    def test_session_creation(self):
        """Test TelemetrySession creation."""
        now = datetime.now()
        env = EnvironmentInfo(
            os_type="Linux",
            os_version="Ubuntu 20.04",
            python_version="3.9.0",
            working_directory="/test",
            project_root="/test"
        )

        session = TelemetrySession(
            session_id="session-123",
            start_time=now,
            environment=env
        )

        assert session.session_id == "session-123"
        assert session.environment.os_type == "Linux"

    def test_session_add_task(self):
        """Test adding tasks to session."""
        now = datetime.now()
        session = TelemetrySession(
            session_id="session-123",
            start_time=now
        )

        task = TaskExecution(
            task_id="task-123",
            description="Test task",
            start_time=now
        )

        session.add_task(task)

        assert len(session.tasks) == 1
        assert session.tasks[0].task_id == "task-123"

    def test_session_serialization(self):
        """Test TelemetrySession serialization."""
        now = datetime.now()
        env = EnvironmentInfo(
            os_type="Linux",
            os_version="Ubuntu 20.04",
            python_version="3.9.0",
            working_directory="/test",
            project_root="/test"
        )

        session = TelemetrySession(
            session_id="session-123",
            start_time=now,
            environment=env
        )

        # Test JSON serialization
        json_str = session.to_json()
        assert isinstance(json_str, str)
        assert "session-123" in json_str

        # Test deserialization
        restored = TelemetrySession.from_json(json_str)
        assert restored.session_id == session.session_id
        assert restored.environment.os_type == session.environment.os_type

    def test_session_file_operations(self):
        """Test saving/loading session to/from file."""
        now = datetime.now()
        session = TelemetrySession(
            session_id="session-123",
            start_time=now
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_session.json"

            # Save to file
            session.save_to_file(file_path)
            assert file_path.exists()

            # Load from file
            restored = TelemetrySession.load_from_file(file_path)
            assert restored.session_id == session.session_id


class TestEnums:
    """Test enum types."""

    def test_task_status_enum(self):
        """Test TaskStatus enum."""
        assert TaskStatus.NOT_STARTED.value == "not_started"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.PARTIAL.value == "partial"

    def test_agent_type_enum(self):
        """Test AgentType enum."""
        assert AgentType.SUPERVISOR.value == "supervisor"
        assert AgentType.MICRO.value == "micro"
        assert AgentType.TOOL_CALLING.value == "tool_calling"
        assert AgentType.CODE.value == "code"
        assert AgentType.MANAGED.value == "managed"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_serialize_telemetry_data(self):
        """Test serialize_telemetry_data function."""
        now = datetime.now()
        session = TelemetrySession(
            session_id="session-123",
            start_time=now
        )

        json_str = serialize_telemetry_data(session)
        assert isinstance(json_str, str)
        assert "session-123" in json_str

    def test_deserialize_telemetry_data(self):
        """Test deserialize_telemetry_data function."""
        now = datetime.now()
        session = TelemetrySession(
            session_id="session-123",
            start_time=now
        )

        json_str = session.to_json()
        restored = deserialize_telemetry_data(json_str, "session")

        assert isinstance(restored, TelemetrySession)
        assert restored.session_id == "session-123"

    def test_deserialize_invalid_type(self):
        """Test deserialize_telemetry_data with invalid type."""
        with pytest.raises(ValueError, match="Unknown data type"):
            deserialize_telemetry_data("{}", "invalid_type")
