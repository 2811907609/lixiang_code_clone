"""Integration tests for execution environments."""

import pytest
import tempfile

from ai_agents.tools.execution import create_execution_environment


class TestExecutionEnvironmentIntegration:
    """Integration tests for execution environments."""

    def test_host_executor_basic_workflow(self):
        """Test basic workflow with host executor."""
        with create_execution_environment("host") as env:
            tools = env.tools()
            execute_command = tools[0]

            # Test basic command
            result = execute_command("echo 'Hello World'")
            assert "Hello World" in result
            assert "SUCCESS" in result

            # Test command with output
            result = execute_command("python -c 'print(2 + 2)'")
            assert "4" in result
            assert "SUCCESS" in result

    def test_host_executor_file_operations(self):
        """Test file operations with host executor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = create_execution_environment(
                "host",
                working_directory=temp_dir
            )

            tools = env.tools()
            execute_command = tools[0]

            # Create a file using shell
            result = execute_command("bash -c \"echo 'test content' > test.txt\"")
            assert "SUCCESS" in result

            # Read the file
            result = execute_command("cat test.txt")
            assert "test content" in result
            assert "SUCCESS" in result

            # List files
            result = execute_command("ls -la")
            assert "test.txt" in result
            assert "SUCCESS" in result

    def test_host_executor_environment_variables(self):
        """Test environment variables with host executor."""
        env = create_execution_environment(
            "host",
            environment_vars={"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
        )

        tools = env.tools()
        execute_command = tools[0]

        # Test environment variable
        result = execute_command("bash -c 'echo $TEST_VAR'")
        assert "test_value" in result
        assert "SUCCESS" in result

        # Test another environment variable
        result = execute_command("bash -c 'echo $ANOTHER_VAR'")
        assert "another_value" in result
        assert "SUCCESS" in result

    def test_host_executor_error_handling(self):
        """Test error handling with host executor."""
        env = create_execution_environment("host")
        tools = env.tools()
        execute_command = tools[0]

        # Test command that fails
        result = execute_command("false")
        assert "FAILED" in result
        assert "Exit Code: 1" in result

        # Test nonexistent command
        result = execute_command("nonexistent_command_xyz")
        assert "Execution error:" in result

    def test_host_executor_security_validation(self):
        """Test security validation with host executor."""
        env = create_execution_environment(
            "host",
            validate_commands=True,
            allow_dangerous_commands=False
        )

        tools = env.tools()
        execute_command = tools[0]

        # Test dangerous command is blocked
        result = execute_command("rm -rf /")
        assert "Blocked command 'rm': attempting to delete root filesystem" in result

        # Test safe command works
        result = execute_command("echo 'safe command'")
        assert "SUCCESS" in result

    @pytest.mark.docker
    def test_docker_sandbox_basic_workflow_mock(self):
        """Test basic workflow with Docker sandbox (mocked, no actual Docker)."""
        # Note: This test doesn't actually start Docker to avoid dependencies
        env = create_execution_environment(
            "docker",
            session_id="integration_test",
            auto_start=False,
            auto_pull_image=False
        )

        # Test that the environment is created correctly
        assert env.session_id == "integration_test"
        assert not env.is_started

        # Test tools method
        tools = env.tools()
        assert len(tools) == 1
        execute_command = tools[0]
        assert callable(execute_command)

        # Test that command execution fails when not started
        result = execute_command("echo 'test'")
        assert "Sandbox is not started" in result

    @pytest.mark.docker
    def test_docker_sandbox_configuration(self):
        """Test Docker sandbox configuration."""
        from ai_agents.tools.execution.docker.docker_config import PREDEFINED_CONFIGS

        env = create_execution_environment(
            "docker",
            session_id="config_test",
            predefined_config="python",
            memory_limit="1g",
            cpu_limit="2.0",
            allow_network=True,
            environment_vars={"DEBUG": "1"},
            auto_start=False
        )

        expected_python_config = PREDEFINED_CONFIGS["python"]

        # Test configuration
        assert env.config.image == expected_python_config.image
        assert env.config.memory_limit == "1g"
        assert env.config.cpu_limit == "2.0"
        assert env.config.network_mode == "bridge"
        assert "DEBUG" in env.config.environment
        assert env.config.environment["DEBUG"] == "1"

        # Test security and resource info
        security_info = env.get_security_info()
        assert isinstance(security_info, dict)
        assert "network_mode" in security_info

        resource_info = env.get_resource_info()
        assert isinstance(resource_info, dict)
        assert "memory_limit" in resource_info
        assert resource_info["memory_limit"] == "1g"

    def test_host_environment_interface(self):
        """Test host environment interface and functionality."""
        # Create host environment
        host_env = create_execution_environment("host")
        host_tools = host_env.tools()
        host_execute = host_tools[0]

        # Test interface
        assert len(host_tools) == 1
        assert callable(host_execute)

        # Host should work
        result = host_execute("echo 'host test'")
        assert "host test" in result
        assert "SUCCESS" in result

    @pytest.mark.docker
    def test_docker_environment_interface(self):
        """Test Docker environment interface and functionality."""
        # Create Docker environment (without starting)
        docker_env = create_execution_environment(
            "docker",
            session_id="switch_test",
            auto_start=False
        )
        docker_tools = docker_env.tools()
        docker_execute = docker_tools[0]

        # Test interface
        assert len(docker_tools) == 1
        assert callable(docker_execute)

        # Docker should indicate it's not started
        result = docker_execute("echo 'docker test'")
        assert "not started" in result

    def test_host_interface_consistency(self):
        """Test that host environment has consistent interface."""
        env = create_execution_environment("host")

        # Test required methods exist
        assert hasattr(env, 'tools')
        assert hasattr(env, 'start')
        assert hasattr(env, 'stop')
        assert hasattr(env, 'is_started')

        # Test tools method returns list with one callable
        tools = env.tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert callable(tools[0])

        # Test context manager support
        assert hasattr(env, '__enter__')
        assert hasattr(env, '__exit__')

    @pytest.mark.docker
    def test_docker_interface_consistency(self):
        """Test that docker environment has consistent interface."""
        env = create_execution_environment(
            "docker",
            session_id="consistency_test",
            auto_start=False
        )

        # Test required methods exist
        assert hasattr(env, 'tools')
        assert hasattr(env, 'start')
        assert hasattr(env, 'stop')
        assert hasattr(env, 'is_started')

        # Test tools method returns list with one callable
        tools = env.tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert callable(tools[0])

        # Test context manager support
        assert hasattr(env, '__enter__')
        assert hasattr(env, '__exit__')

    def test_general_error_propagation(self):
        """Test that general errors are properly propagated."""
        # Test invalid environment type
        with pytest.raises(ValueError, match="Unknown environment type"):
            create_execution_environment("invalid_type")

    def test_host_error_propagation(self):
        """Test that host-specific errors are properly propagated."""
        # Test invalid host parameters
        with pytest.raises(ValueError):
            create_execution_environment(
                "host",
                working_directory="/nonexistent/directory"
            )

    @pytest.mark.docker
    def test_docker_error_propagation(self):
        """Test that Docker-specific errors are properly propagated."""
        # Test invalid Docker parameters (invalid memory limit)
        with pytest.raises(ValueError):
            create_execution_environment(
                "docker",
                session_id="test",
                memory_limit="invalid_memory",  # Invalid memory format
                auto_start=False
            )
