"""Unit tests for the HookErrorHandler class."""

import logging
from unittest.mock import patch
from concurrent.futures import TimeoutError

from ai_agents.core.hooks.error_handler import (
    HookErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    HookError
)
from ai_agents.core.hooks.types import (
    HookContext,
    HookResult,
    ScriptHook,
    PythonHook
)


class TestHookErrorHandler:
    """Test cases for HookErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = HookErrorHandler(debug_mode=True)
        self.context = HookContext(
            session_id="test-session",
            cwd="/test/dir",
            hook_event_name="PreToolUse",
            tool_name="test_tool",
            tool_input={"param": "value"}
        )

    def test_init_debug_mode(self):
        """Test initialization with debug mode."""
        handler = HookErrorHandler(debug_mode=True)
        assert handler.debug_mode is True
        assert handler.logger.level == logging.DEBUG

        handler = HookErrorHandler(debug_mode=False)
        assert handler.debug_mode is False

    def test_handle_script_timeout(self):
        """Test handling script timeout errors."""
        hook = ScriptHook(
            matcher="*",
            command="test-command",
            timeout=30
        )

        result = self.error_handler.handle_script_timeout(hook, self.context, 35.5)

        assert not result.success
        assert "timed out after 30s" in result.reason
        assert "test-command" in result.output

        # Check error was recorded
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["timeout"] == 1
        assert stats["total_errors"] == 1

    def test_handle_script_error_deny(self):
        """Test handling script error with exit code 2 (deny)."""
        hook = ScriptHook(
            matcher="*",
            command="test-command",
            timeout=30
        )

        result = self.error_handler.handle_script_error(
            hook, self.context, 2, "stdout output", "deny reason"
        )

        assert result.success
        assert result.decision == "deny"
        assert "deny reason" in result.reason

        # Check error was recorded with low severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["script_error"] == 1

    def test_handle_script_error_general(self):
        """Test handling general script errors."""
        hook = ScriptHook(
            matcher="*",
            command="test-command",
            timeout=30
        )

        result = self.error_handler.handle_script_error(
            hook, self.context, 1, "stdout", "error message"
        )

        assert not result.success
        assert "Script hook failed" in result.reason
        assert "error message" in result.reason

        # Check error was recorded
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["script_error"] == 1

    def test_handle_python_error_timeout(self):
        """Test handling Python hook timeout errors."""
        def test_func(context):
            return HookResult.success_result()

        hook = PythonHook(
            matcher="*",
            function=test_func,
            timeout=30
        )

        timeout_error = TimeoutError("Function timed out after 30s")
        result = self.error_handler.handle_python_error(hook, self.context, timeout_error)

        assert not result.success
        assert "Python hook failed" in result.reason
        assert "timed out" in result.reason.lower()

        # Check error was recorded
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["python_error"] == 1

    def test_handle_python_error_import_error(self):
        """Test handling Python import errors."""
        def test_func(context):
            return HookResult.success_result()

        hook = PythonHook(
            matcher="*",
            function=test_func,
            timeout=30
        )

        import_error = ImportError("No module named 'missing_module'")
        result = self.error_handler.handle_python_error(hook, self.context, import_error)

        assert not result.success
        assert "Python hook failed" in result.reason
        assert "missing_module" in result.reason

        # Check error was recorded with high severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["python_error"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["severity"] == "high"

    def test_handle_configuration_error_file_not_found(self):
        """Test handling configuration file not found errors."""
        error = FileNotFoundError("Config file not found")

        self.error_handler.handle_configuration_error(
            "/path/to/config.json", error, "loading configuration"
        )

        # Check error was recorded with low severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["configuration_error"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["severity"] == "low"

    def test_handle_configuration_error_json_error(self):
        """Test handling JSON configuration errors."""
        error = ValueError("Invalid JSON format")

        self.error_handler.handle_configuration_error(
            "/path/to/config.json", error, "parsing JSON"
        )

        # Check error was recorded with medium severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["configuration_error"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["severity"] == "medium"

    def test_handle_validation_error(self):
        """Test handling validation errors."""
        self.error_handler.handle_validation_error(
            "hook configuration",
            "Invalid matcher pattern",
            ["Use valid regex pattern", "Check documentation"]
        )

        # Check error was recorded
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["validation_error"] == 1
        assert len(stats["recent_errors"]) == 1
        # The recovery suggestion should be in the recent error details
        recent_error = stats["recent_errors"][0]
        assert "Invalid matcher pattern" in recent_error["details"]

    def test_handle_permission_error(self):
        """Test handling permission errors."""
        error = PermissionError("Permission denied")

        self.error_handler.handle_permission_error(
            "executing script", "/path/to/script", error
        )

        # Check error was recorded with high severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["permission_error"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["severity"] == "high"

    def test_handle_system_error(self):
        """Test handling system errors."""
        error = RuntimeError("System failure")
        context = {"operation": "test", "component": "hook_system"}

        self.error_handler.handle_system_error(
            "hook execution", error, context
        )

        # Check error was recorded with critical severity
        stats = self.error_handler.get_error_statistics()
        assert stats["error_counts"]["system_error"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["severity"] == "critical"

    def test_error_statistics_management(self):
        """Test error statistics tracking and management."""
        # Generate multiple errors
        hook = ScriptHook(matcher="*", command="test", timeout=30)

        self.error_handler.handle_script_timeout(hook, self.context, 35.0)
        self.error_handler.handle_script_error(hook, self.context, 1, "", "error")
        self.error_handler.handle_validation_error("test", "validation failed")

        stats = self.error_handler.get_error_statistics()
        assert stats["total_errors"] == 3
        assert stats["error_counts"]["timeout"] == 1
        assert stats["error_counts"]["script_error"] == 1
        assert stats["error_counts"]["validation_error"] == 1
        assert len(stats["recent_errors"]) == 3

        # Clear statistics
        self.error_handler.clear_error_statistics()
        stats = self.error_handler.get_error_statistics()
        assert stats["total_errors"] == 0
        assert len(stats["recent_errors"]) == 0

    def test_debug_mode_toggle(self):
        """Test debug mode toggling."""
        # Start with debug mode off
        handler = HookErrorHandler(debug_mode=False)
        assert not handler.debug_mode

        # Enable debug mode
        handler.set_debug_mode(True)
        assert handler.debug_mode
        assert handler.logger.level == logging.DEBUG

        # Disable debug mode
        handler.set_debug_mode(False)
        assert not handler.debug_mode
        assert handler.logger.level == logging.INFO

    def test_recovery_suggestions(self):
        """Test recovery suggestion generation."""
        # Test script error suggestions
        hook = ScriptHook(matcher="*", command="test", timeout=30)

        # Test exit code 126 (permission)
        _ = self.error_handler.handle_script_error(
            hook, self.context, 126, "", "permission denied"
        )
        stats = self.error_handler.get_error_statistics()
        # Check that error was recorded and has details
        assert len(stats["recent_errors"]) == 1
        assert "permission denied" in stats["recent_errors"][0]["details"]

        # Test Python import error suggestion
        def test_func(context):
            return HookResult.success_result()

        python_hook = PythonHook(matcher="*", function=test_func, timeout=30)
        import_error = ImportError("No module named 'test'")

        self.error_handler.handle_python_error(python_hook, self.context, import_error)
        stats = self.error_handler.get_error_statistics()
        assert len(stats["recent_errors"]) == 2  # Previous + this one

    @patch.object(HookErrorHandler, '_log_error')
    def test_logging_levels(self, mock_log_error):
        """Test that errors are logged with appropriate levels."""
        # Test critical error logging
        error = RuntimeError("Critical system error")
        self.error_handler.handle_system_error("test", error)

        # Verify log_error was called
        mock_log_error.assert_called()

        # Test warning level logging
        hook = ScriptHook(matcher="*", command="test", timeout=30)
        self.error_handler.handle_script_error(hook, self.context, 1, "", "warning")

        # Verify log_error was called again
        assert mock_log_error.call_count == 2

    def test_recent_errors_limit(self):
        """Test that recent errors list is limited to max size."""
        # Generate more errors than the limit
        hook = ScriptHook(matcher="*", command="test", timeout=30)

        # Generate 105 errors (more than the 100 limit)
        for i in range(105):
            self.error_handler.handle_script_error(
                hook, self.context, 1, "", f"error {i}"
            )

        stats = self.error_handler.get_error_statistics()
        assert stats["total_errors"] == 105
        assert len(self.error_handler._recent_errors) == 100  # Limited to max
        assert stats["recent_errors_count"] == 100

        # Verify only the last 10 are returned in stats
        assert len(stats["recent_errors"]) == 10


class TestHookError:
    """Test cases for HookError dataclass."""

    def test_hook_error_creation(self):
        """Test HookError creation with all fields."""
        error = HookError(
            category=ErrorCategory.SCRIPT_ERROR,
            severity=ErrorSeverity.HIGH,
            message="Test error message",
            details="Detailed error information",
            hook_info={"type": "script", "command": "test"},
            context_info={"tool": "test_tool"},
            recovery_suggestion="Fix the script",
            traceback_info="Traceback info"
        )

        assert error.category == ErrorCategory.SCRIPT_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.message == "Test error message"
        assert error.details == "Detailed error information"
        assert error.hook_info["type"] == "script"
        assert error.context_info["tool"] == "test_tool"
        assert error.recovery_suggestion == "Fix the script"
        assert error.traceback_info == "Traceback info"

    def test_hook_error_minimal(self):
        """Test HookError creation with minimal fields."""
        error = HookError(
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout occurred"
        )

        assert error.category == ErrorCategory.TIMEOUT
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.message == "Timeout occurred"
        assert error.details is None
        assert error.hook_info is None
        assert error.context_info is None
        assert error.recovery_suggestion is None
        assert error.traceback_info is None


class TestErrorEnums:
    """Test cases for error enums."""

    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.SCRIPT_ERROR.value == "script_error"
        assert ErrorCategory.PYTHON_ERROR.value == "python_error"
        assert ErrorCategory.CONFIGURATION_ERROR.value == "configuration_error"
        assert ErrorCategory.PERMISSION_ERROR.value == "permission_error"
        assert ErrorCategory.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCategory.SYSTEM_ERROR.value == "system_error"
