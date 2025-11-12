"""Tests for base execution environment classes."""

import pytest
from typing import List, Any

from ai_agents.tools.execution.base.execution_environment import ExecutionEnvironment
from ai_agents.tools.execution.base.sandbox_environment import SandboxEnvironment


class MockExecutionEnvironment(ExecutionEnvironment):
    """Mock implementation for testing."""

    def __init__(self):
        self._started = False

    def tools(self) -> List[Any]:
        return []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started


class MockSandboxEnvironment(SandboxEnvironment):
    """Mock sandbox implementation for testing."""

    def __init__(self, session_id: str = "test"):
        self._session_id = session_id
        self._started = False

    def tools(self) -> List[Any]:
        return []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def session_id(self) -> str:
        return self._session_id

    def get_security_info(self) -> dict:
        return {"policy": "test"}

    def get_resource_info(self) -> dict:
        return {"memory": "512m"}


class TestExecutionEnvironment:
    """Test ExecutionEnvironment abstract base class."""

    def test_is_abstract(self):
        """Test that ExecutionEnvironment is abstract."""
        with pytest.raises(TypeError):
            ExecutionEnvironment()

    def test_concrete_implementation(self):
        """Test concrete implementation works."""
        env = MockExecutionEnvironment()
        assert not env.is_started

        env.start()
        assert env.is_started

        env.stop()
        assert not env.is_started

    def test_context_manager(self):
        """Test context manager functionality."""
        env = MockExecutionEnvironment()
        assert not env.is_started

        with env:
            assert env.is_started

        assert not env.is_started

    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception."""
        env = MockExecutionEnvironment()

        try:
            with env:
                assert env.is_started
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not env.is_started


class TestSandboxEnvironment:
    """Test SandboxEnvironment abstract base class."""

    def test_is_abstract(self):
        """Test that SandboxEnvironment is abstract."""
        with pytest.raises(TypeError):
            SandboxEnvironment()

    def test_concrete_implementation(self):
        """Test concrete implementation works."""
        env = MockSandboxEnvironment("test_session")

        assert env.session_id == "test_session"
        assert not env.is_started

        env.start()
        assert env.is_started

        security_info = env.get_security_info()
        assert isinstance(security_info, dict)
        assert "policy" in security_info

        resource_info = env.get_resource_info()
        assert isinstance(resource_info, dict)
        assert "memory" in resource_info

        env.stop()
        assert not env.is_started

    def test_inherits_from_execution_environment(self):
        """Test that SandboxEnvironment inherits from ExecutionEnvironment."""
        env = MockSandboxEnvironment()
        assert isinstance(env, ExecutionEnvironment)
        assert isinstance(env, SandboxEnvironment)
