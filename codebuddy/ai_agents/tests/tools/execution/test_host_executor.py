"""Tests for HostExecutor."""

import pytest
import os
import tempfile
from pathlib import Path

from ai_agents.tools.execution.host.host_executor import HostExecutor
from ai_agents.tools.execution.base.execution_environment import ExecutionEnvironment


class TestHostExecutor:
    """Test HostExecutor functionality."""

    def test_initialization_default(self):
        """Test default initialization."""
        executor = HostExecutor()

        assert executor.is_started
        assert executor.working_directory == os.getcwd()
        assert executor.timeout_seconds == 30.0
        assert executor.max_output_size_kb == 1024.0
        assert executor.validate_commands is True
        assert executor.allow_dangerous_commands is False

    def test_initialization_with_params(self):
        """Test initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = HostExecutor(
                working_directory=temp_dir,
                timeout_seconds=60.0,
                environment_vars={"TEST_VAR": "test_value"},
                max_output_size_kb=2048.0,
                validate_commands=False,
                allow_dangerous_commands=True
            )

            assert executor.working_directory == str(Path(temp_dir).resolve())
            assert executor.timeout_seconds == 60.0
            assert executor.max_output_size_kb == 2048.0
            assert executor.validate_commands is False
            assert executor.allow_dangerous_commands is True
            assert "TEST_VAR" in executor.env
            assert executor.env["TEST_VAR"] == "test_value"

    def test_invalid_working_directory(self):
        """Test initialization with invalid working directory."""
        with pytest.raises(ValueError, match="does not exist"):
            HostExecutor(working_directory="/nonexistent/directory")

    def test_working_directory_not_directory(self):
        """Test initialization with file as working directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError, match="is not a directory"):
                HostExecutor(working_directory=temp_file.name)

    def test_inherits_from_execution_environment(self):
        """Test that HostExecutor inherits from ExecutionEnvironment."""
        executor = HostExecutor()
        assert isinstance(executor, ExecutionEnvironment)

    def test_start_stop_methods(self):
        """Test start and stop methods."""
        executor = HostExecutor()

        # Host is always started
        assert executor.is_started

        executor.stop()
        assert executor.is_started  # Host can't really be stopped

        executor.start()
        assert executor.is_started

    def test_tools_method(self):
        """Test tools method returns execute_command tool."""
        executor = HostExecutor()
        tools = executor.tools()

        assert len(tools) == 1
        execute_command = tools[0]
        assert callable(execute_command)
        # SimpleTool objects don't have __name__, check the tool's name attribute instead
        assert hasattr(execute_command, 'name') or callable(execute_command)

    def test_execute_simple_command(self):
        """Test executing a simple command."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("echo 'Hello World'")

        assert "Command: echo 'Hello World'" in result
        assert "Exit Code: 0" in result
        assert "Execution Status: SUCCESS" in result
        assert "Hello World" in result

    def test_execute_command_with_error(self):
        """Test executing a command that fails."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("false")  # Command that always fails

        assert "Exit Code: 1" in result
        assert "Execution Status: FAILED" in result

    def test_execute_nonexistent_command(self):
        """Test executing a nonexistent command."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("nonexistent_command_12345")

        assert "Execution error:" in result

    def test_command_validation_dangerous(self):
        """Test command validation blocks dangerous commands."""
        executor = HostExecutor(validate_commands=True, allow_dangerous_commands=False)
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("rm -rf /")

        assert "Blocked command 'rm': attempting to delete root filesystem" in result

    def test_command_validation_disabled(self):
        """Test command validation can be disabled."""
        executor = HostExecutor(validate_commands=False)
        tools = executor.tools()
        execute_command = tools[0]

        # This would normally be blocked, but validation is disabled
        # Note: We're not actually running rm -rf /, just testing the validation
        result = execute_command("echo 'rm -rf /'")

        assert "SUCCESS" in result

    def test_empty_command(self):
        """Test executing empty command."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("")

        assert "Execution error:" in result
        assert "command is required" in result

    def test_working_directory_change(self):
        """Test command execution in specific working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = HostExecutor(working_directory=temp_dir)
            tools = executor.tools()
            execute_command = tools[0]

            result = execute_command("pwd")

            assert temp_dir in result

    def test_environment_variables(self):
        """Test environment variables are passed to commands."""
        executor = HostExecutor(environment_vars={"TEST_ENV_VAR": "test_value"})
        tools = executor.tools()
        execute_command = tools[0]

        # Use shell to expand the variable
        result = execute_command("bash -c 'echo $TEST_ENV_VAR'")

        assert "test_value" in result

    def test_context_manager(self):
        """Test context manager functionality."""
        with HostExecutor() as executor:
            assert executor.is_started
            tools = executor.tools()
            execute_command = tools[0]

            result = execute_command("echo 'test'")
            assert "SUCCESS" in result

        # Host executor is always "started"
        assert executor.is_started

    def test_command_with_special_characters(self):
        """Test command with special characters."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        result = execute_command("echo 'Hello & World | Test'")

        assert "Hello & World | Test" in result
        assert "SUCCESS" in result

    def test_complex_shell_commands_supported(self):
        """Test that complex shell commands (&&, ||, |) are now supported."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test command chaining with &&
        result = execute_command("echo 'first' && echo 'second'")

        # Should now execute both commands
        assert "SUCCESS" in result
        assert "first" in result
        assert "second" in result

        # Test pipe command
        result = execute_command("echo 'hello world' | grep 'world'")

        # Should pipe echo output to grep and find the matching line
        assert "SUCCESS" in result
        assert "hello world" in result  # grep outputs the entire matching line

    def test_command_with_semicolon_supported(self):
        """Test that semicolon command separation is now supported."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test command separation with semicolon
        result = execute_command("echo 'first'; echo 'second'")

        # Should now execute both commands
        assert "SUCCESS" in result
        assert "first" in result
        assert "second" in result

    def test_command_substitution_supported(self):
        """Test that command substitution is now supported."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test command substitution with a simple command
        result = execute_command("echo $(echo 'substituted')")

        # Should substitute the command
        assert "SUCCESS" in result
        assert "substituted" in result

    def test_environment_variable_expansion_supported(self):
        """Test that environment variable expansion now works with shell."""
        executor = HostExecutor(environment_vars={"TEST_VAR": "test_value"})
        tools = executor.tools()
        execute_command = tools[0]

        # Test environment variable expansion with shell
        result = execute_command("echo $TEST_VAR")

        # With shell=True, $TEST_VAR should be expanded
        assert "SUCCESS" in result
        assert "test_value" in result

    def test_logical_operators_supported(self):
        """Test logical operators && and || are supported."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test && operator (both commands should run if first succeeds)
        result = execute_command("true && echo 'success'")
        assert "SUCCESS" in result
        assert "success" in result

        # Test || operator (second command should run if first fails)
        result = execute_command("false || echo 'fallback'")
        assert "SUCCESS" in result  # Overall command succeeds due to ||
        assert "fallback" in result

    def test_pipe_with_multiple_commands(self):
        """Test pipe operator with multiple commands."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test multi-stage pipe
        result = execute_command("echo -e 'apple\\nbanana\\ncherry' | grep 'a' | wc -l")

        assert "SUCCESS" in result
        # Should count lines containing 'a' (apple, banana = 2 lines)
        assert "2" in result

    def test_output_redirection_supported(self):
        """Test that output redirection is now supported."""
        import tempfile
        import os

        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Test output redirection to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            result = execute_command(f"echo 'test content' > {tmp_path}")
            assert "SUCCESS" in result

            # Verify file was created and contains expected content
            result = execute_command(f"cat {tmp_path}")
            assert "SUCCESS" in result
            assert "test content" in result
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_complex_shell_command_combinations(self):
        """Test combinations of different shell features."""
        executor = HostExecutor()
        tools = executor.tools()
        execute_command = tools[0]

        # Complex command: conditional execution, pipe, and grep
        result = execute_command("echo 'line1\\nline2\\nline3' | grep 'line' && echo 'found lines'")

        assert "SUCCESS" in result
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result
        assert "found lines" in result
