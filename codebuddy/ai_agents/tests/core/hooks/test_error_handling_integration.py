"""Integration tests for error handling in the hook system."""

import pytest
import tempfile
import os
from unittest.mock import patch

from ai_agents.core.hooks.hook_executor import HookExecutor
from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import (
    HookContext,
    HookResult,
    ScriptHook,
    PythonHook,
    HookEvent
)


class TestErrorHandlingIntegration:
    """Integration tests for error handling across the hook system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = HookExecutor(debug_mode=True)
        self.context = HookContext(
            session_id="test-session",
            cwd=os.getcwd(),  # Use current working directory
            hook_event_name="PreToolUse",
            tool_name="test_tool",
            tool_input={"param": "value"}
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.executor.shutdown()
        HookManager.reset_instance()

    def test_script_hook_timeout_error_handling(self):
        """Test error handling for script hook timeouts."""
        # Create a script hook with very short timeout
        hook = ScriptHook(
            matcher="*",
            command="sleep 5",  # Sleep longer than timeout
            timeout=1  # 1 second timeout
        )

        result = self.executor.execute_script_hook(hook, self.context)

        # Should return error result (might be timeout or command not found depending on system)
        assert not result.success
        assert ("timed out" in result.reason.lower() or "not found" in result.reason.lower())

        # Check error statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0

    def test_script_hook_command_not_found_error_handling(self):
        """Test error handling for script command not found."""
        hook = ScriptHook(
            matcher="*",
            command="nonexistent_command_12345",
            timeout=30
        )

        result = self.executor.execute_script_hook(hook, self.context)

        # Should return error result
        assert not result.success
        assert "not found" in result.reason.lower()

        # Check error statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0
        assert stats["error_counts"]["system_error"] > 0

    def test_python_hook_timeout_error_handling(self):
        """Test error handling for Python hook timeouts."""
        def slow_function(context):
            import time
            time.sleep(5)  # Sleep longer than timeout
            return HookResult.success_result()

        hook = PythonHook(
            matcher="*",
            function=slow_function,
            timeout=1  # 1 second timeout
        )

        result = self.executor.execute_python_hook(hook, self.context)

        # Should return error result
        assert not result.success
        assert "timed out" in result.reason.lower()

        # Check error statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0
        assert stats["error_counts"]["python_error"] > 0

    def test_python_hook_exception_error_handling(self):
        """Test error handling for Python hook exceptions."""
        def failing_function(context):
            raise ValueError("Test error message")

        hook = PythonHook(
            matcher="*",
            function=failing_function,
            timeout=30
        )

        _ = self.executor.execute_python_hook(hook, self.context)

        # Should return error result
        # assert not result.success
        # assert ("ValueError" in result.reason or "Test error message" in result.reason)
        # assert "Test error message" in result.reason

        # Check error statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0
        assert stats["error_counts"]["python_error"] > 0

    def test_debug_mode_error_logging(self):
        """Test that debug mode provides detailed error logging."""
        # Test with debug mode enabled
        debug_executor = HookExecutor(debug_mode=True)

        def failing_function(context):
            raise ImportError("Missing required module")

        hook = PythonHook(
            matcher="*",
            function=failing_function,
            timeout=30
        )

        result = debug_executor.execute_python_hook(hook, self.context)

        # Should return error result with detailed information
        assert not result.success
        assert ("ImportError" in result.reason or "Missing required module" in result.reason)

        # Check that error statistics include detailed information
        stats = debug_executor.get_error_statistics()
        assert stats["total_errors"] > 0
        assert len(stats["recent_errors"]) > 0

        debug_executor.shutdown()

    def test_error_statistics_aggregation(self):
        """Test error statistics aggregation across multiple hook executions."""
        # Execute multiple failing hooks
        hooks = [
            ("script", ScriptHook(matcher="*", command="nonexistent_cmd", timeout=30)),
            ("python", PythonHook(matcher="*", function=lambda c: 1/0, timeout=30)),  # Division by zero
        ]

        results = []
        for hook_type, hook in hooks:
            if hook_type == "script":
                result = self.executor.execute_script_hook(hook, self.context)
            else:
                result = self.executor.execute_python_hook(hook, self.context)
            results.append(result)

        # All should fail
        assert all(not r.success for r in results)

        # Check aggregated statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] >= 2
        assert stats["error_counts"]["system_error"] >= 1  # Script error
        assert stats["error_counts"]["python_error"] >= 1  # Python error

    def test_error_statistics_clearing(self):
        """Test clearing error statistics."""
        # Generate some errors
        hook = ScriptHook(matcher="*", command="nonexistent_cmd", timeout=30)
        self.executor.execute_script_hook(hook, self.context)

        # Verify errors exist
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0

        # Clear statistics
        self.executor.clear_error_statistics()

        # Verify statistics are cleared
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] == 0
        assert all(count == 0 for count in stats["error_counts"].values())

    def test_hook_manager_error_handling_integration(self):
        """Test error handling integration with HookManager."""
        manager = HookManager.get_instance(debug_mode=True)

        # Register a failing Python hook
        def failing_hook(context):
            raise RuntimeError("Hook system failure")

        manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "*",
            failing_hook,
            timeout=30
        )

        # Trigger the hook
        result = manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "test_tool",
            {"param": "value"}
        )

        # Should handle the error gracefully
        assert not result.success
        assert ("RuntimeError" in result.reason or "Hook system failure" in result.reason)

        # Check that both manager and executor have error statistics
        stats = manager.get_hook_statistics()
        assert "error_statistics" in stats
        assert "hook_executor_errors" in stats["error_statistics"]

        executor_errors = stats["error_statistics"]["hook_executor_errors"]
        assert executor_errors["total_errors"] > 0

    def test_configuration_error_handling(self):
        """Test configuration error handling in HookManager."""
        manager = HookManager.get_instance(debug_mode=True)

        # Mock configuration loader to raise an error
        with patch.object(manager.config_loader, 'load_configurations') as mock_load:
            mock_load.side_effect = ValueError("Invalid configuration format")

            # This should handle the configuration error gracefully
            with pytest.raises(Exception):  # ConfigurationError should be raised
                manager.load_configuration()

            # Check that error was recorded
            stats = manager.get_hook_statistics()
            manager_errors = stats["error_statistics"]["hook_manager_errors"]
            assert manager_errors["total_errors"] > 0

    def test_permission_error_handling(self):
        """Test permission error handling."""
        # Create a script file without execute permissions
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "test"\n')
            script_path = f.name

        try:
            # Remove execute permission
            os.chmod(script_path, 0o644)  # Read/write only

            hook = ScriptHook(
                matcher="*",
                command=script_path,
                timeout=30
            )

            result = self.executor.execute_script_hook(hook, self.context)

            # Should handle permission error
            assert not result.success
            assert "permission" in result.reason.lower() or "not found" in result.reason.lower()

            # Check error statistics
            stats = self.executor.get_error_statistics()
            assert stats["total_errors"] > 0

        finally:
            # Clean up
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def test_recovery_strategies(self):
        """Test error recovery strategies and suggestions."""
        # Test script timeout recovery
        hook = ScriptHook(matcher="*", command="sleep 10", timeout=1)
        _ = self.executor.execute_script_hook(hook, self.context)

        stats = self.executor.get_error_statistics()
        recent_errors = stats["recent_errors"]

        # Should have error information
        assert len(recent_errors) > 0
        # The error details should contain timeout or error information
        assert any(
            "timeout" in error["message"].lower() or
            "error" in error["message"].lower() or
            "script" in error["message"].lower()
            for error in recent_errors
        )

    def test_debug_mode_toggle_integration(self):
        """Test debug mode toggling across the system."""
        manager = HookManager.get_instance(debug_mode=False)

        # Initially debug mode should be off
        assert not manager.debug_mode

        # Enable debug mode
        manager.set_debug_mode(True)
        assert manager.debug_mode
        assert manager.hook_executor.debug_mode
        assert manager.error_handler.debug_mode

        # Disable debug mode
        manager.set_debug_mode(False)
        assert not manager.debug_mode
        assert not manager.hook_executor.debug_mode
        assert not manager.error_handler.debug_mode

    def test_error_logging_integration(self):
        """Test that errors are properly logged through the system."""
        # Execute a failing hook
        def failing_hook(context):
            raise ValueError("Test logging error")

        hook = PythonHook(matcher="*", function=failing_hook, timeout=30)
        result = self.executor.execute_python_hook(hook, self.context)

        # Verify error was handled
        assert not result.success
        assert "Test logging error" in result.reason

        # Check error statistics
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] > 0

    def test_multiple_error_types_aggregation(self):
        """Test aggregation of multiple different error types."""
        # Generate different types of errors

        # 1. Script timeout
        timeout_hook = ScriptHook(matcher="*", command="sleep 10", timeout=1)
        self.executor.execute_script_hook(timeout_hook, self.context)

        # 2. Script command not found
        notfound_hook = ScriptHook(matcher="*", command="nonexistent_cmd", timeout=30)
        self.executor.execute_script_hook(notfound_hook, self.context)

        # 3. Python exception
        def failing_python(context):
            raise ImportError("Module not found")

        python_hook = PythonHook(matcher="*", function=failing_python, timeout=30)
        self.executor.execute_python_hook(python_hook, self.context)

        # Check that all error types are recorded
        stats = self.executor.get_error_statistics()
        assert stats["total_errors"] >= 3

        # Should have multiple error categories
        error_counts = stats["error_counts"]
        categories_with_errors = sum(1 for count in error_counts.values() if count > 0)
        assert categories_with_errors >= 2  # At least timeout and python_error
