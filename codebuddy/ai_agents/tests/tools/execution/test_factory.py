"""Tests for execution environment factory function."""

import pytest
import tempfile

from ai_agents.tools.execution import create_execution_environment
from ai_agents.tools.execution.host.host_executor import HostExecutor
from ai_agents.tools.execution.docker.docker_sandbox import DockerSandbox
from ai_agents.tools.execution.base.execution_environment import ExecutionEnvironment


class TestCreateExecutionEnvironment:
    """Test the factory function for creating execution environments."""

    def test_create_host_executor(self):
        """Test creating host executor."""
        env = create_execution_environment("host")

        assert isinstance(env, HostExecutor)
        assert isinstance(env, ExecutionEnvironment)
        assert env.is_started

    def test_create_host_executor_with_params(self):
        """Test creating host executor with parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = create_execution_environment(
                "host",
                working_directory=temp_dir,
                timeout_seconds=60.0,
                allow_dangerous_commands=True
            )

            assert isinstance(env, HostExecutor)
            # Use Path.resolve() to handle symlinks consistently
            from pathlib import Path
            assert env.working_directory == str(Path(temp_dir).resolve())
            assert env.timeout_seconds == 60.0
            assert env.allow_dangerous_commands is True

    @pytest.mark.docker
    def test_create_docker_sandbox(self):
        """Test creating Docker sandbox."""
        env = create_execution_environment(
            "docker",
            session_id="test_session",
            auto_start=False  # Don't actually start Docker
        )

        assert isinstance(env, DockerSandbox)
        assert isinstance(env, ExecutionEnvironment)
        assert env.session_id == "test_session"

    @pytest.mark.docker
    def test_create_docker_sandbox_with_params(self):
        """Test creating Docker sandbox with parameters."""
        from ai_agents.tools.execution.docker.docker_config import PREDEFINED_CONFIGS

        env = create_execution_environment(
            "docker",
            session_id="test_session",
            predefined_config="python",
            allow_network=True,
            memory_limit="1g",
            auto_start=False  # Don't actually start Docker
        )

        expected_python_config = PREDEFINED_CONFIGS["python"]

        assert isinstance(env, DockerSandbox)
        assert env.session_id == "test_session"
        assert env.config.image == expected_python_config.image
        assert env.config.memory_limit == "1g"
        assert env.config.network_mode == "bridge"

    def test_create_unknown_environment_type(self):
        """Test creating unknown environment type."""
        with pytest.raises(ValueError, match="Unknown environment type"):
            create_execution_environment("unknown_type")

    def test_create_environment_type_case_sensitive(self):
        """Test that environment type is case sensitive."""
        with pytest.raises(ValueError, match="Unknown environment type"):
            create_execution_environment("HOST")  # Should be "host"

        with pytest.raises(ValueError, match="Unknown environment type"):
            create_execution_environment("Docker")  # Should be "docker"

    def test_available_environment_types_in_error(self):
        """Test that error message includes available types."""
        with pytest.raises(ValueError) as exc_info:
            create_execution_environment("invalid")

        error_message = str(exc_info.value)
        assert "host" in error_message
        assert "docker" in error_message

    def test_unified_interface_host(self):
        """Test that host executor has unified interface."""
        env = create_execution_environment("host")

        # Test unified interface
        assert hasattr(env, 'tools')
        assert hasattr(env, 'start')
        assert hasattr(env, 'stop')
        assert hasattr(env, 'is_started')

        tools = env.tools()
        assert len(tools) == 1
        assert callable(tools[0])

    @pytest.mark.docker
    def test_unified_interface_docker(self):
        """Test that Docker sandbox has unified interface."""
        env = create_execution_environment(
            "docker",
            session_id="test",
            auto_start=False
        )

        # Test unified interface
        assert hasattr(env, 'tools')
        assert hasattr(env, 'start')
        assert hasattr(env, 'stop')
        assert hasattr(env, 'is_started')

        tools = env.tools()
        assert len(tools) == 1
        assert callable(tools[0])

    def test_host_context_manager_interface(self):
        """Test that host environment supports context manager."""
        # Host executor
        with create_execution_environment("host") as env:
            assert env.is_started
            tools = env.tools()
            assert len(tools) == 1

    @pytest.mark.docker
    def test_docker_context_manager_interface(self):
        """Test that docker environment supports context manager."""
        # Docker sandbox (without actually starting)
        env = create_execution_environment(
            "docker",
            session_id="test",
            auto_start=False
        )
        # Just test that it has the context manager methods
        assert hasattr(env, '__enter__')
        assert hasattr(env, '__exit__')

    def test_host_specific_features(self):
        """Test that host environment specific features are accessible."""
        # Host executor specific features
        host_env = create_execution_environment("host")
        assert hasattr(host_env, 'working_directory')
        assert hasattr(host_env, 'timeout_seconds')

    @pytest.mark.docker
    def test_docker_specific_features(self):
        """Test that docker environment specific features are accessible."""
        # Docker sandbox specific features
        docker_env = create_execution_environment(
            "docker",
            session_id="test",
            auto_start=False
        )
        assert hasattr(docker_env, 'session_id')
        assert hasattr(docker_env, 'config')
        assert hasattr(docker_env, 'get_security_info')
        assert hasattr(docker_env, 'get_resource_info')

    def test_host_parameter_forwarding(self):
        """Test that host parameters are correctly forwarded to constructors."""
        # Test host executor parameter forwarding
        with tempfile.TemporaryDirectory() as temp_dir:
            host_env = create_execution_environment(
                "host",
                working_directory=temp_dir,
                timeout_seconds=45.0,
                max_output_size_kb=2048.0
            )

            from pathlib import Path
            assert host_env.working_directory == str(Path(temp_dir).resolve())
            assert host_env.timeout_seconds == 45.0
            assert host_env.max_output_size_kb == 2048.0

    @pytest.mark.docker
    def test_docker_parameter_forwarding(self):
        """Test that docker parameters are correctly forwarded to constructors."""
        # Test Docker sandbox parameter forwarding
        docker_env = create_execution_environment(
            "docker",
            session_id="param_test",
            docker_image="alpine:latest",
            memory_limit="256m",
            cpu_limit="0.5",
            auto_start=False
        )

        assert docker_env.session_id == "param_test"
        assert docker_env.config.image == "alpine:latest"
        assert docker_env.config.memory_limit == "256m"
        assert docker_env.config.cpu_limit == "0.5"
