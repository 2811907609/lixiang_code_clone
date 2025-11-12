"""Host execution environment for running commands directly on the host system."""

import logging
import subprocess
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from commonlibs.encoding.detect_content_encoding import safe_decode_byte_data
from ..base.execution_environment import ExecutionEnvironment
from ..security.command_validator import CommandValidator


class HostExecutor(ExecutionEnvironment):
    """
    Host execution environment that runs commands directly on the host system.

    This provides a unified interface for executing commands on the host,
    with safety validations and consistent output formatting.
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout_seconds: float = 240.0,
        environment_vars: Optional[Dict[str, str]] = None,
        max_output_size_kb: float = 1024.0,
        validate_commands: bool = True,
        allow_dangerous_commands: bool = False
    ):
        """
        Initialize host executor.

        Args:
            working_directory: Default working directory for commands
            timeout_seconds: Default timeout for command execution
            environment_vars: Additional environment variables
            max_output_size_kb: Maximum output size to capture
            validate_commands: Whether to validate commands for safety
            allow_dangerous_commands: Whether to allow potentially dangerous commands
        """
        self.logger = logging.getLogger(__name__)
        self.timeout_seconds = timeout_seconds
        self.max_output_size_kb = max_output_size_kb
        self.validate_commands = validate_commands
        self.allow_dangerous_commands = allow_dangerous_commands

        # Set working directory
        if working_directory:
            work_dir = Path(working_directory)
            if not work_dir.exists():
                raise ValueError(f"Working directory '{working_directory}' does not exist")
            if not work_dir.is_dir():
                raise ValueError(f"Working directory '{working_directory}' is not a directory")
            if not os.access(work_dir, os.R_OK | os.X_OK):
                raise PermissionError(f"Insufficient permissions to access working directory '{working_directory}'")
            self.working_directory = str(work_dir.resolve())
        else:
            self.working_directory = os.getcwd()

        # Set environment variables
        self.env = os.environ.copy()
        if environment_vars:
            self.env.update(environment_vars)

        # Initialize command validator
        self.command_validator = CommandValidator(allow_dangerous_commands=self.allow_dangerous_commands)

        self._is_started = True  # Host is always "started"

        self.logger.info(f"Host executor initialized (cwd: {self.working_directory})")

    @property
    def is_started(self) -> bool:
        """Host executor is always ready."""
        return self._is_started

    def start(self) -> None:
        """Start the host executor (no-op for host)."""
        self._is_started = True

    def stop(self) -> None:
        """Stop the host executor (no-op for host)."""
        self._is_started = True  # Host can't really be "stopped"

    def tools(self) -> List[Any]:
        """
        Get list tools for AI agents.

        Returns:
            List containing the execute_command tool
        """
        def execute_command(command: str) -> str:
            """
            Execute a shell command on the host system, ensuring proper handling and security measures.
            Before executing the command, please follow these steps:
            1. Directory Verification:
                - If the command will create new directories or files, first use the ls to verify the parent directory exists and is the correct location
                - For example, before running "mkdir foo/bar", first use ls to check that "foo" exists and is the intended parent directory
            2. Command Execution:
                - Always quote file paths that contain spaces with double quotes (e.g., cd "path with spaces/file.txt")
                - Examples of proper quoting:
                    - cd "/Users/name/My Documents" (correct)
                    - cd /Users/name/My Documents (incorrect - will fail)
                    - python \"/path/with spaces/script.py\" (correct)
                    - python /path/with spaces/script.py (incorrect - will fail)
                - After ensuring proper quoting, execute the command.
                - Capture the output of the command.

            Usage notes:
                - The command argument is required.
                - If the output exceeds 30000 characters, output will be truncated before being returned to you.
                - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. ALWAYS USE ripgrep at `rg` first, which all users have pre-installed.
                - Ripgrep (rg) Examples:
                    - Search keyword: rg "keyword" (search text in all files)
                    - Search by file type: rg "function" --type py (Python files only)
                    - List matching files: rg --files -g 'test_*.py' (find files by pattern)
                    - Case-insensitive: rg -i "error" (ignore case)
                    - With line numbers: rg -n "import" (show line numbers)
                    - Files containing pattern: rg -l "pandas" (filenames only)
                    - Count matches: rg -c "function" --type py (count occurrences per file)
                - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
                - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.
                    <good-example>
                    pytest /foo/bar/tests
                    </good-example>
                    <bad-example>
                    cd /foo/bar && pytest tests
                    </bad-example>

            Args:
                command: The shell command to execute

            Returns:
                Command output and execution status
            """
            if not self.is_started:
                return "Error: Host executor is not started"

            try:
                return self._execute_command_internal(command)
            except Exception as e:
                return f"Execution error: {e}"

        return [execute_command]

    def _execute_command_internal(self, command: str) -> str:
        """Internal method to execute commands with full error handling."""
        start_time = time.time()

        # Validate inputs
        if not command or not command.strip():
            raise ValueError("command is required and cannot be empty")

        command = command.strip()

        # Validate command safety if requested
        if self.validate_commands:
            validation_result = self.command_validator.validate_command(command)
            if not validation_result.is_safe:
                error_msg = f"Command blocked for security reasons: {'; '.join(validation_result.violations)}"
                if validation_result.warnings:
                    error_msg += f" (Warnings: {'; '.join(validation_result.warnings)})"
                raise ValueError(error_msg)
            elif validation_result.warnings:
                for warning in validation_result.warnings:
                    self.logger.warning(f"Command security warning: {warning}")

        # Log the operation
        self.logger.info(f"Executing host command: {command} (cwd: {self.working_directory}, timeout: {self.timeout_seconds}s)")

        try:
            # Execute the command using shell to support complex commands
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=False,  # 使用字节模式避免编码问题
                env=self.env,
                shell=True
            )
            stdout = safe_decode_byte_data(result.stdout) if result.stdout else ""
            stderr = safe_decode_byte_data(result.stderr) if result.stderr else ""

            # Truncate output if too large
            max_output_bytes = int(self.max_output_size_kb * 1024)

            if len(stdout.encode('utf-8')) > max_output_bytes:
                stdout = stdout[:max_output_bytes // 2] + f"\n\n... [OUTPUT TRUNCATED - exceeded {self.max_output_size_kb}KB limit] ...\n\n"

            if stderr and len(stderr.encode('utf-8')) > max_output_bytes:
                stderr = stderr[:max_output_bytes // 2] + f"\n\n... [STDERR TRUNCATED - exceeded {self.max_output_size_kb}KB limit] ...\n\n"

            # Calculate execution time
            execution_time = time.time() - start_time

            # Format result
            result_lines = [
                f"Command: {command}",
                f"Working Directory: {self.working_directory}",
                f"Exit Code: {result.returncode}",
                f"Execution Status: {'SUCCESS' if result.returncode == 0 else 'FAILED'}",
                f"Execution Time: {execution_time:.2f}s"
            ]

            if stdout:
                result_lines.extend([
                    "",
                    "=== OUTPUT ===",
                    stdout.rstrip()
                ])

            if stderr:
                result_lines.extend([
                    "",
                    "=== ERRORS ===",
                    stderr.rstrip()
                ])

            if not stdout and not stderr:
                result_lines.append("(No output)")

            # Log the completion
            self.logger.info(f"Host command completed with exit code {result.returncode} in {execution_time:.2f}s")

            return "\n".join(result_lines)

        except subprocess.TimeoutExpired as e:
            error_msg = f"Command '{command}' timed out after {self.timeout_seconds} seconds"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg) from e

        except PermissionError as e:
            error_msg = f"Permission denied when executing command '{command}': {e}"
            self.logger.error(error_msg)
            raise PermissionError(error_msg) from e

        except OSError as e:
            error_msg = f"Failed to execute command '{command}': {e}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error executing command '{command}': {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
