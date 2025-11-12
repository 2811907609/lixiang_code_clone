"""Host execution environment for running commands directly on the host system."""

import subprocess
import time
from ai_agents.tools.execution.host.host_executor import HostExecutor

class AprHostExecutor(HostExecutor):
    """
    Host execution environment that runs commands directly on the host system.

    This provides a unified interface for executing commands on the host,
    with safety validations and consistent output formatting.
    """

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
                text=True,
                env=self.env,
                shell=True
            )

            # Process output
            stdout = result.stdout or ""
            stderr = result.stderr or ""

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


            std_full=stdout+stderr
            if std_full and 'build.sh' in command:
                # 使用延迟导入避免循环依赖
                from ai_agents.supervisor_agents.detected_static_repair.coverity_compile_log_extractor_test import extract_coverity_compile_info
                info_txt, bool_compile_ok = extract_coverity_compile_info(compile_info_txtpath=std_full)
                if info_txt:
                    result_lines.extend([
                        "",
                        "=== OUTPUT FROM extract_coverity_compile_info ===",
                        info_txt.rstrip()
                    ])
            else:
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
