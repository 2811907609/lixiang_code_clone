"""Comprehensive error handling and logging for the hook system."""

import logging
import traceback
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

from .types import HookResult, ScriptHook, PythonHook, HookContext


class ErrorSeverity(Enum):
    """Severity levels for hook errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of hook errors."""
    TIMEOUT = "timeout"
    SCRIPT_ERROR = "script_error"
    PYTHON_ERROR = "python_error"
    CONFIGURATION_ERROR = "configuration_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"


@dataclass
class HookError:
    """Detailed error information for hook failures."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    hook_info: Optional[Dict[str, Any]] = None
    context_info: Optional[Dict[str, Any]] = None
    recovery_suggestion: Optional[str] = None
    traceback_info: Optional[str] = None


class HookErrorHandler:
    """Centralized error processing and recovery for the hook system."""

    def __init__(self, debug_mode: bool = False):
        """Initialize the error handler.

        Args:
            debug_mode: Enable verbose debug logging
        """
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)

        # Configure logging level based on debug mode
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)

        # Error statistics
        self._error_counts: Dict[ErrorCategory, int] = {
            category: 0 for category in ErrorCategory
        }
        self._recent_errors: List[HookError] = []
        self._max_recent_errors = 100

    def handle_script_timeout(self, hook: ScriptHook, context: HookContext,
                            execution_time: float) -> HookResult:
        """Handle script hook timeout errors.

        Args:
            hook: The script hook that timed out
            context: The hook context
            execution_time: Actual execution time before timeout

        Returns:
            HookResult with appropriate error handling
        """
        error = HookError(
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message=f"Script hook timed out after {hook.timeout}s",
            details=f"Command: {hook.command}\nExecution time: {execution_time:.2f}s",
            hook_info={
                "type": "script",
                "command": hook.command,
                "timeout": hook.timeout,
                "matcher": hook.matcher,
                "working_directory": hook.working_directory
            },
            context_info={
                "tool_name": context.tool_name,
                "event": context.hook_event_name,
                "session_id": context.session_id
            },
            recovery_suggestion="Consider increasing the timeout value or optimizing the script"
        )

        self._record_error(error)
        self._log_error(error)

        return HookResult.error_result(
            reason=error.message,
            output=f"Timeout after {hook.timeout}s executing: {hook.command}"
        )

    def handle_script_error(self, hook: ScriptHook, context: HookContext,
                          exit_code: int, stdout: str, stderr: str) -> HookResult:
        """Handle script hook execution errors.

        Args:
            hook: The script hook that failed
            context: The hook context
            exit_code: Exit code from the script
            stdout: Standard output from the script
            stderr: Standard error from the script

        Returns:
            HookResult with appropriate error handling
        """
        # Determine severity based on exit code
        if exit_code == 2:
            # Exit code 2 is expected (deny operation)
            severity = ErrorSeverity.LOW
            category = ErrorCategory.SCRIPT_ERROR
        elif exit_code in [1, 3, 4, 5]:
            # Common error codes
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SCRIPT_ERROR
        else:
            # Unusual exit codes
            severity = ErrorSeverity.HIGH
            category = ErrorCategory.SCRIPT_ERROR

        error_message = stderr.strip() if stderr.strip() else f"Script exited with code {exit_code}"

        error = HookError(
            category=category,
            severity=severity,
            message=f"Script hook failed: {error_message}",
            details=f"Command: {hook.command}\nExit code: {exit_code}\nStdout: {stdout}\nStderr: {stderr}",
            hook_info={
                "type": "script",
                "command": hook.command,
                "timeout": hook.timeout,
                "matcher": hook.matcher,
                "working_directory": hook.working_directory
            },
            context_info={
                "tool_name": context.tool_name,
                "event": context.hook_event_name,
                "session_id": context.session_id
            },
            recovery_suggestion=self._get_script_error_recovery_suggestion(exit_code, stderr)
        )

        self._record_error(error)
        self._log_error(error)

        # Handle based on exit code
        if exit_code == 2:
            # Deny operation
            reason = stderr.strip() or stdout.strip() or "Script hook blocked operation"
            return HookResult.deny_result(reason, output=stdout.strip() if stdout.strip() else None)
        else:
            # Error but continue execution
            return HookResult.error_result(
                reason=error.message,
                output=stdout.strip() if stdout.strip() else stderr.strip()
            )

    def handle_python_error(self, hook: PythonHook, context: HookContext,
                          exception: Exception) -> HookResult:
        """Handle Python hook execution errors.

        Args:
            hook: The Python hook that failed
            context: The hook context
            exception: The exception that occurred

        Returns:
            HookResult with appropriate error handling
        """
        # Determine severity based on exception type
        severity = self._get_python_error_severity(exception)

        error = HookError(
            category=ErrorCategory.PYTHON_ERROR,
            severity=severity,
            message=f"Python hook failed: {str(exception)}",
            details=f"Function: {hook.function.__name__}\nException type: {type(exception).__name__}",
            hook_info={
                "type": "python",
                "function_name": hook.function.__name__,
                "function_module": getattr(hook.function, '__module__', 'unknown'),
                "timeout": hook.timeout,
                "matcher": hook.matcher
            },
            context_info={
                "tool_name": context.tool_name,
                "event": context.hook_event_name,
                "session_id": context.session_id
            },
            recovery_suggestion=self._get_python_error_recovery_suggestion(exception),
            traceback_info=traceback.format_exc() if self.debug_mode else None
        )

        self._record_error(error)
        self._log_error(error)

        return HookResult.error_result(
            reason=f"Python hook failed: {str(exception)}",
            output=f"Function: {hook.function.__name__}\nError: {str(exception)}"
        )

    def handle_configuration_error(self, config_path: str, error: Exception,
                                 context: Optional[str] = None) -> None:
        """Handle configuration loading failures.

        Args:
            config_path: Path to the configuration file that failed
            error: The exception that occurred
            context: Additional context about the error
        """
        # Determine severity based on error type
        if isinstance(error, (FileNotFoundError, PermissionError)):
            severity = ErrorSeverity.LOW
        elif isinstance(error, (ValueError, TypeError)):
            severity = ErrorSeverity.MEDIUM
        else:
            severity = ErrorSeverity.HIGH

        hook_error = HookError(
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=severity,
            message=f"Configuration error in {config_path}: {str(error)}",
            details=f"Error type: {type(error).__name__}\nContext: {context or 'None'}",
            hook_info={
                "config_path": config_path,
                "error_type": type(error).__name__
            },
            recovery_suggestion=self._get_configuration_error_recovery_suggestion(error, config_path),
            traceback_info=traceback.format_exc() if self.debug_mode else None
        )

        self._record_error(hook_error)
        self._log_error(hook_error)

    def handle_validation_error(self, validation_context: str, error_details: str,
                              suggestions: Optional[List[str]] = None) -> None:
        """Handle validation errors in hook configurations or inputs.

        Args:
            validation_context: Context where validation failed
            error_details: Detailed error information
            suggestions: Optional list of recovery suggestions
        """
        error = HookError(
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"Validation error in {validation_context}",
            details=error_details,
            recovery_suggestion="; ".join(suggestions) if suggestions else None
        )

        self._record_error(error)
        self._log_error(error)

    def handle_permission_error(self, operation: str, path: str, error: Exception) -> None:
        """Handle permission-related errors.

        Args:
            operation: The operation that failed
            path: The path that caused the permission error
            error: The permission error exception
        """
        error_obj = HookError(
            category=ErrorCategory.PERMISSION_ERROR,
            severity=ErrorSeverity.HIGH,
            message=f"Permission denied for {operation}: {path}",
            details=f"Error: {str(error)}",
            recovery_suggestion="Check file permissions and user access rights"
        )

        self._record_error(error_obj)
        self._log_error(error_obj)

    def handle_system_error(self, operation: str, error: Exception,
                          context: Optional[Dict[str, Any]] = None) -> None:
        """Handle system-level errors.

        Args:
            operation: The operation that failed
            error: The system error exception
            context: Additional context information
        """
        error_obj = HookError(
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            message=f"System error during {operation}: {str(error)}",
            details=f"Error type: {type(error).__name__}",
            context_info=context,
            recovery_suggestion="Check system resources and configuration",
            traceback_info=traceback.format_exc() if self.debug_mode else None
        )

        self._record_error(error_obj)
        self._log_error(error_obj)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and recent errors.

        Returns:
            Dictionary containing error statistics
        """
        return {
            "error_counts": {category.value: count for category, count in self._error_counts.items()},
            "total_errors": sum(self._error_counts.values()),
            "recent_errors_count": len(self._recent_errors),
            "recent_errors": [
                {
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "message": error.message,
                    "details": error.details
                }
                for error in self._recent_errors[-10:]  # Last 10 errors
            ]
        }

    def clear_error_statistics(self) -> None:
        """Clear error statistics and recent errors."""
        self._error_counts = {category: 0 for category in ErrorCategory}
        self._recent_errors.clear()
        self.logger.info("Error statistics cleared")

    def set_debug_mode(self, debug_mode: bool) -> None:
        """Enable or disable debug mode.

        Args:
            debug_mode: Whether to enable debug mode
        """
        self.debug_mode = debug_mode
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode enabled for hook error handler")
        else:
            self.logger.setLevel(logging.INFO)
            self.logger.info("Debug mode disabled for hook error handler")

    def _record_error(self, error: HookError) -> None:
        """Record an error in statistics and recent errors list."""
        self._error_counts[error.category] += 1
        self._recent_errors.append(error)

        # Keep only the most recent errors
        if len(self._recent_errors) > self._max_recent_errors:
            self._recent_errors = self._recent_errors[-self._max_recent_errors:]

    def _log_error(self, error: HookError) -> None:
        """Log an error with appropriate level based on severity."""
        log_message = f"[{error.category.value.upper()}] {error.message}"

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        # Log details in debug mode
        if self.debug_mode and error.details:
            self.logger.debug(f"Error details: {error.details}")

        # Log recovery suggestion
        if error.recovery_suggestion:
            self.logger.info(f"Recovery suggestion: {error.recovery_suggestion}")

        # Log traceback in debug mode
        if self.debug_mode and error.traceback_info:
            self.logger.debug(f"Traceback:\n{error.traceback_info}")

        # Log context information in debug mode
        if self.debug_mode:
            if error.hook_info:
                self.logger.debug(f"Hook info: {error.hook_info}")
            if error.context_info:
                self.logger.debug(f"Context info: {error.context_info}")

    def _get_script_error_recovery_suggestion(self, exit_code: int, stderr: str) -> str:
        """Get recovery suggestion for script errors."""
        if exit_code == 2:
            return "This is expected behavior for deny operations"
        elif exit_code == 1:
            return "Check script logic and input validation"
        elif exit_code == 126:
            return "Check script permissions and make it executable"
        elif exit_code == 127:
            return "Check if the command exists and is in PATH"
        elif "permission" in stderr.lower():
            return "Check file and directory permissions"
        elif "not found" in stderr.lower():
            return "Verify the command or file path exists"
        else:
            return "Review script output and fix any issues"

    def _get_python_error_recovery_suggestion(self, exception: Exception) -> str:
        """Get recovery suggestion for Python errors."""
        if isinstance(exception, ImportError):
            return "Check if required modules are installed and available"
        elif isinstance(exception, AttributeError):
            return "Verify object attributes and method names"
        elif isinstance(exception, TypeError):
            return "Check function arguments and types"
        elif isinstance(exception, ValueError):
            return "Validate input values and ranges"
        elif isinstance(exception, KeyError):
            return "Check dictionary keys and data structure"
        elif isinstance(exception, FileNotFoundError):
            return "Verify file paths and existence"
        elif isinstance(exception, PermissionError):
            return "Check file and directory permissions"
        else:
            return "Review the Python function implementation and fix any issues"

    def _get_python_error_severity(self, exception: Exception) -> ErrorSeverity:
        """Determine severity level for Python errors."""
        if isinstance(exception, (SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        elif isinstance(exception, (ImportError, ModuleNotFoundError)):
            return ErrorSeverity.HIGH
        elif isinstance(exception, (TypeError, AttributeError, ValueError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.MEDIUM

    def _get_configuration_error_recovery_suggestion(self, error: Exception, config_path: str) -> str:
        """Get recovery suggestion for configuration errors."""
        if isinstance(error, FileNotFoundError):
            return f"Create the configuration file at {config_path} or check the path"
        elif isinstance(error, PermissionError):
            return f"Check read permissions for {config_path}"
        elif "JSON" in str(error) or isinstance(error, ValueError):
            return "Fix JSON syntax errors in the configuration file"
        else:
            return "Review and fix the configuration file format"
