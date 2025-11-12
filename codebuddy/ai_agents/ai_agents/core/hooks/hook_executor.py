"""Hook executor for running hooks and processing results."""

import json
import subprocess
import time
from typing import List, Dict, Any
import logging
import signal
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from .types import HookContext, HookResult, ScriptHook, PythonHook
from .error_handler import HookErrorHandler


logger = logging.getLogger(__name__)


class HookExecutor:
    """Executes hooks and processes their results."""

    def __init__(self, max_concurrent_hooks: int = 5, debug_mode: bool = False):
        """Initialize the hook executor.

        Args:
            max_concurrent_hooks: Maximum number of hooks to execute concurrently
            debug_mode: Enable verbose debug logging
        """
        self.max_concurrent_hooks = max_concurrent_hooks
        self.debug_mode = debug_mode
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_hooks)
        self._error_handler = HookErrorHandler(debug_mode=debug_mode)

    def execute_script_hook(self, hook: ScriptHook, context: HookContext) -> HookResult:
        """Execute a script hook with timeout handling.

        Args:
            hook: The script hook to execute
            context: The hook context to pass to the script

        Returns:
            HookResult containing the execution result
        """
        logger.debug(f"Executing script hook: {hook.command} for tool {context.tool_name}")

        try:
            # Prepare the working directory
            working_dir = hook.working_directory or context.cwd
            if not os.path.exists(working_dir):
                logger.warning(f"Working directory {working_dir} does not exist, using current directory")
                working_dir = context.cwd

            # Prepare the command
            command_parts = hook.command.split()
            if not command_parts:
                return HookResult.error_result("Empty command in script hook")

            # Serialize context to JSON for stdin
            context_json = context.to_json()

            # Execute the script with timeout
            start_time = time.time()
            try:
                process = subprocess.Popen(
                    command_parts,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=working_dir,
                    text=True,
                    preexec_fn=os.setsid if os.name != 'nt' else None  # For process group handling on Unix
                )

                # Use communicate with timeout
                try:
                    stdout, stderr = process.communicate(
                        input=context_json,
                        timeout=hook.timeout
                    )
                    exit_code = process.returncode

                except subprocess.TimeoutExpired:
                    # Kill the process group to ensure all child processes are terminated
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        time.sleep(1)  # Give it a moment to terminate gracefully
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # Process already terminated
                    else:
                        process.terminate()
                        time.sleep(1)
                        process.kill()

                    process.wait()  # Clean up the process
                    execution_time = time.time() - start_time
                    return self._error_handler.handle_script_timeout(hook, context, execution_time)

            except FileNotFoundError as e:
                self._error_handler.handle_system_error(
                    f"executing script {hook.command}",
                    e,
                    {"hook_type": "script", "command": command_parts[0]}
                )
                return HookResult.error_result(
                    f"Script command not found: {command_parts[0]}",
                    output=f"Command: {hook.command}"
                )
            except PermissionError as e:
                self._error_handler.handle_permission_error(
                    f"executing script {hook.command}",
                    command_parts[0],
                    e
                )
                return HookResult.error_result(
                    f"Permission denied executing script: {command_parts[0]}",
                    output=f"Command: {hook.command}"
                )
            except Exception as e:
                self._error_handler.handle_system_error(
                    f"executing script {hook.command}",
                    e,
                    {"hook_type": "script", "command": hook.command}
                )
                return HookResult.error_result(
                    f"Unexpected error executing script: {str(e)}",
                    output=f"Command: {hook.command}\nError: {str(e)}"
                )

            execution_time = time.time() - start_time
            logger.debug(f"Script hook completed in {execution_time:.2f}s with exit code {exit_code}")

            # Process the result based on exit code and output
            return self._process_script_result(hook, context, exit_code, stdout, stderr)

        except Exception as e:
            self._error_handler.handle_system_error(
                f"executing script hook {hook.command}",
                e,
                {"hook_type": "script", "command": hook.command, "tool_name": context.tool_name}
            )
            return HookResult.error_result(
                f"Failed to execute script hook: {str(e)}",
                output=f"Command: {hook.command}\nError: {str(e)}"
            )

    def _process_script_result(self, hook: ScriptHook, context: HookContext, exit_code: int, stdout: str, stderr: str) -> HookResult:
        """Process the result of a script hook execution.

        Supports both JSON output and simple exit code behavior:
        1. First attempts to parse stdout as JSON
        2. Falls back to exit code behavior if JSON parsing fails
        3. Exit code 0 = allow, 2 = deny, others = error but continue

        Args:
            hook: The script hook that was executed
            context: The hook context
            exit_code: The exit code from the script
            stdout: Standard output from the script
            stderr: Standard error from the script

        Returns:
            HookResult based on the script output
        """
        # Clean up output strings
        stdout_clean = stdout.strip() if stdout else ""
        stderr_clean = stderr.strip() if stderr else ""

        # Try to parse JSON output first if stdout contains data
        if stdout_clean:
            try:
                # Attempt to parse the entire stdout as JSON
                json_output = json.loads(stdout_clean)
                if isinstance(json_output, dict):
                    logger.debug(f"Successfully parsed JSON output from script hook: {hook.command}")
                    return self._parse_json_hook_result(json_output, stdout_clean)
                else:
                    logger.warning(f"Script hook returned non-object JSON: {type(json_output)}")
                    # Fall through to exit code behavior
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON from script hook output (falling back to exit code): {str(e)}")
                # Fall through to exit code behavior
            except Exception as e:
                logger.warning(f"Unexpected error parsing JSON from script hook: {str(e)}")
                # Fall through to exit code behavior

        # Handle based on exit code (fallback behavior)
        logger.debug(f"Using exit code behavior for script hook: exit_code={exit_code}")

        if exit_code == 0:
            # Success - allow execution
            return HookResult.success_result(output=stdout_clean if stdout_clean else None)
        elif exit_code == 2:
            # Deny operation - use stderr for reason, fallback to stdout
            reason = stderr_clean or stdout_clean or "Script hook blocked operation"
            return HookResult.deny_result(reason, output=stdout_clean if stdout_clean else None)
        else:
            # Error but continue execution - use error handler
            return self._error_handler.handle_script_error(hook, context, exit_code, stdout, stderr)

    def _parse_json_hook_result(self, json_output: Dict[str, Any], raw_output: str) -> HookResult:
        """Parse JSON output from a script hook.

        Supports the following JSON fields:
        - decision: "allow", "deny", "ask", "block" (default: "allow")
        - reason: Human-readable reason for the decision
        - additionalContext: Additional context to inject into agent
        - continue: Boolean indicating if execution should continue (default: True)
        - stopReason: Alternative field for reason (legacy support)
        - suppressOutput: Boolean to suppress tool output (default: False)

        Args:
            json_output: Parsed JSON output from the script
            raw_output: Raw output string for fallback

        Returns:
            HookResult based on the JSON output
        """
        try:
            # Extract and validate decision field
            decision = json_output.get("decision", "allow")
            if decision not in ["allow", "deny", "ask", "block"]:
                logger.warning(f"Invalid decision value '{decision}', defaulting to 'allow'")
                decision = "allow"

            # Extract reason field with fallback to stopReason for legacy support
            reason = json_output.get("reason")
            stop_reason = json_output.get("stopReason")
            if not reason and stop_reason:
                reason = stop_reason

            # Extract additional context
            additional_context = json_output.get("additionalContext")
            if additional_context is not None and not isinstance(additional_context, str):
                # Convert non-string additional context to string
                additional_context = str(additional_context)

            # Extract continue execution flag
            continue_execution = json_output.get("continue", True)
            if not isinstance(continue_execution, bool):
                logger.warning(f"Invalid continue value '{continue_execution}', defaulting to True")
                continue_execution = True

            # Extract suppress output flag
            suppress_output = json_output.get("suppressOutput", False)
            if not isinstance(suppress_output, bool):
                logger.warning(f"Invalid suppressOutput value '{suppress_output}', defaulting to False")
                suppress_output = False

            # Validate reason field for decisions that require it
            if decision in ["deny", "ask", "block"] and not reason:
                logger.warning(f"Decision '{decision}' should include a reason, using default")
                reason = f"Hook returned {decision} decision without reason"

            # Log successful JSON parsing for debugging
            logger.debug(f"Parsed JSON hook result: decision={decision}, reason={reason}, "
                        f"continue={continue_execution}, suppress={suppress_output}")

            return HookResult(
                success=True,
                decision=decision,
                reason=reason,
                additional_context=additional_context,
                suppress_output=suppress_output,
                continue_execution=continue_execution,
                output=raw_output
            )

        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Error parsing JSON hook result fields: {str(e)}")
            return HookResult.success_result(output=raw_output)
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON hook result: {str(e)}")
            return HookResult.success_result(output=raw_output)

    def execute_python_hook(self, hook: PythonHook, context: HookContext) -> HookResult:
        """Execute a Python function hook with timeout handling.

        Args:
            hook: The Python hook to execute
            context: The hook context to pass to the function

        Returns:
            HookResult containing the execution result
        """
        logger.debug(f"Executing Python hook: {hook.function.__name__} for tool {context.tool_name}")

        try:
            # Create a separate ThreadPoolExecutor for this hook to avoid blocking the main pool
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(hook.function, context)

                start_time = time.time()
                try:
                    result = future.result(timeout=hook.timeout)
                    execution_time = time.time() - start_time
                    logger.debug(f"Python hook completed in {execution_time:.2f}s")

                    # Validate the result
                    if not isinstance(result, HookResult):
                        logger.warning(f"Python hook {hook.function.__name__} returned invalid result type: {type(result)}")
                        return HookResult.success_result(output=str(result))

                    return result

                except TimeoutError:
                    execution_time = time.time() - start_time
                    future.cancel()  # Attempt to cancel the future
                    # Create a timeout exception for the error handler
                    timeout_exception = TimeoutError(f"Function timed out after {hook.timeout}s")
                    return self._error_handler.handle_python_error(hook, context, timeout_exception)

        except Exception as e:
            return self._error_handler.handle_python_error(hook, context, e)

    def aggregate_results(self, results: List[HookResult]) -> HookResult:
        """Combine multiple hook results into a single result.

        Uses the centralized aggregation logic from HookResult.aggregate_results()
        but adds logging for failed hooks.

        Args:
            results: List of hook results to aggregate

        Returns:
            Aggregated HookResult
        """
        if not results:
            return HookResult.success_result()

        # Log failed hooks for debugging
        failed_results = [r for r in results if not r.success]
        if failed_results:
            logger.warning(f"Some hooks failed: {len(failed_results)} out of {len(results)}")
            for failed_result in failed_results:
                logger.debug(f"Failed hook reason: {failed_result.reason}")

        # Use the centralized aggregation logic
        return HookResult.aggregate_results(results)

    def execute_hooks_parallel(self, hooks: List[tuple], context: HookContext) -> HookResult:
        """Execute multiple hooks in parallel and aggregate results.

        Args:
            hooks: List of tuples (hook_type, hook) where hook_type is 'script' or 'python'
            context: The hook context to pass to all hooks

        Returns:
            Aggregated HookResult from all hook executions
        """
        if not hooks:
            return HookResult.success_result()

        logger.debug(f"Executing {len(hooks)} hooks in parallel for tool {context.tool_name}")

        # Execute hooks directly instead of using the thread pool to avoid timeout issues
        results = []
        for hook_type, hook in hooks:
            try:
                if hook_type == 'script':
                    result = self.execute_script_hook(hook, context)
                elif hook_type == 'python':
                    result = self.execute_python_hook(hook, context)
                else:
                    logger.warning(f"Unknown hook type: {hook_type}")
                    continue
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing {hook_type} hook: {str(e)}")
                results.append(HookResult.error_result(f"Hook execution error: {str(e)}"))

        return self.aggregate_results(results)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics from the error handler.

        Returns:
            Dictionary containing error statistics
        """
        return self._error_handler.get_error_statistics()

    def clear_error_statistics(self) -> None:
        """Clear error statistics."""
        self._error_handler.clear_error_statistics()

    def set_debug_mode(self, debug_mode: bool) -> None:
        """Enable or disable debug mode.

        Args:
            debug_mode: Whether to enable debug mode
        """
        self.debug_mode = debug_mode
        self._error_handler.set_debug_mode(debug_mode)
        if debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled for hook executor")
        else:
            logger.setLevel(logging.INFO)

    def shutdown(self):
        """Shutdown the hook executor and clean up resources."""
        logger.debug("Shutting down hook executor")
        self._thread_pool.shutdown(wait=True)
