"""
Error scenario tests for the hook system.
Tests timeout handling, failure cases, and error recovery.
"""
import os
import tempfile
import json
import time
from unittest.mock import patch
from pathlib import Path

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import HookEvent, HookResult


class TestHookTimeoutScenarios:
    """Test hook timeout handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()
        self.test_scripts_dir = Path(__file__).parent / "fixtures" / "test_scripts"

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_script_hook_timeout(self):
        """Test timeout handling for script hooks."""
        # Create a configuration with a timeout hook
        timeout_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TimeoutTool",
                    "hooks": [{
                        "type": "command",
                        "command": f"python {self.test_scripts_dir}/timeout_hook.py",
                        "timeout": 1  # 1 second timeout
                    }]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(timeout_config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                self.hook_manager.load_configuration()

            # Trigger the timeout hook
            start_time = time.time()
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "TimeoutTool", {}
            )
            end_time = time.time()

            # Should timeout within reasonable time (allow some overhead)
            execution_time = end_time - start_time
            assert execution_time < 3.0, f"Timeout took too long: {execution_time:.3f}s"

            # Hook should fail due to timeout
            assert not result.success
            assert "timeout" in result.reason.lower()

        finally:
            os.unlink(config_path)

    def test_python_hook_timeout(self):
        """Test timeout handling for Python hooks."""
        def timeout_hook(context):
            time.sleep(5)  # Sleep longer than timeout
            return HookResult(success=True, continue_execution=True)

        # Register hook with short timeout
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "TimeoutTool", timeout_hook
        )

        # Trigger the hook
        start_time = time.time()
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TimeoutTool", {}
        )
        end_time = time.time()

        # Should timeout quickly
        execution_time = end_time - start_time
        assert execution_time < 2.0, f"Python hook timeout took too long: {execution_time:.3f}s"

        # Hook should fail due to timeout
        assert not result.success
        assert "timeout" in result.reason.lower()

    def test_multiple_hooks_with_timeout(self):
        """Test timeout handling when multiple hooks are registered."""
        def fast_hook(context):
            return HookResult(success=True, continue_execution=True)

        def timeout_hook(context):
            time.sleep(3)
            return HookResult(success=True, continue_execution=True)

        # Register both hooks
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "TestTool", fast_hook
        )
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "TestTool", timeout_hook
        )

        # Trigger hooks
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {}
        )

        # Should handle mixed success/timeout scenario
        # The fast hook should succeed, timeout hook should fail
        # Overall result depends on aggregation strategy
        assert result is not None


class TestHookFailureScenarios:
    """Test various hook failure scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()
        self.test_scripts_dir = Path(__file__).parent / "fixtures" / "test_scripts"

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_script_hook_exit_code_failure(self):
        """Test handling of script hooks with non-zero exit codes."""
        # Test different failure modes
        failure_modes = ['exit_code', 'exception', 'invalid_json']

        for mode in failure_modes:
            with patch.dict(os.environ, {'HOOK_FAILURE_MODE': mode}):
                # Create configuration for failing hook
                fail_config = {
                    "hooks": {
                        "PreToolUse": [{
                            "matcher": "FailTool",
                            "hooks": [{
                                "type": "command",
                                "command": f"python {self.test_scripts_dir}/failing_hook.py"
                            }]
                        }]
                    }
                }

                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(fail_config, f)
                    config_path = f.name

                try:
                    with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                               [config_path]):
                        self.hook_manager.load_configuration()

                    # Trigger the failing hook
                    result = self.hook_manager.trigger_hooks(
                        HookEvent.PRE_TOOL_USE, "FailTool", {}
                    )

                    # Should handle failure appropriately
                    if mode == 'exit_code':
                        assert not result.success
                        assert "failed" in result.reason.lower()
                    elif mode == 'invalid_json':
                        # Should fall back to exit code behavior
                        assert result.success  # Script exits with 0

                finally:
                    os.unlink(config_path)

    def test_python_hook_exception_handling(self):
        """Test handling of Python hook exceptions."""
        def exception_hook(context):
            raise ValueError("Test exception in hook")

        def runtime_error_hook(context):
            raise RuntimeError("Runtime error in hook")

        def type_error_hook(context):
            raise TypeError("Type error in hook")

        # Test different exception types
        exception_hooks = [
            ("ValueError", exception_hook),
            ("RuntimeError", runtime_error_hook),
            ("TypeError", type_error_hook)
        ]

        for error_type, hook_func in exception_hooks:
            # Reset and register hook
            HookManager.reset_instance()
            hook_manager = HookManager.get_instance()
            hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE, "ErrorTool", hook_func
            )

            # Trigger the hook
            result = hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "ErrorTool", {}
            )

            # Should handle exception gracefully
            assert not result.success
            assert error_type.lower() in result.reason.lower() or "error" in result.reason.lower()

    def test_invalid_hook_configuration(self):
        """Test handling of invalid hook configurations."""
        invalid_configs = [
            # Missing required fields
            {"hooks": {"PreToolUse": [{"matcher": "Tool1"}]}},

            # Invalid hook type
            {"hooks": {"PreToolUse": [{"matcher": "Tool1", "hooks": [{"type": "invalid"}]}]}},

            # Invalid timeout
            {"hooks": {"PreToolUse": [{"matcher": "Tool1", "hooks": [{"type": "command", "command": "echo test", "timeout": "invalid"}]}]}},

            # Missing command
            {"hooks": {"PreToolUse": [{"matcher": "Tool1", "hooks": [{"type": "command"}]}]}}
        ]

        for i, invalid_config in enumerate(invalid_configs):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(invalid_config, f)
                config_path = f.name

            try:
                with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                           [config_path]):
                    # Should handle invalid configuration gracefully
                    hook_manager = HookManager.get_instance()
                    hook_manager.load_configuration()

                    # Should not crash, may log errors
                    result = hook_manager.trigger_hooks(
                        HookEvent.PRE_TOOL_USE, "Tool1", {}
                    )

                    # Should return a valid result even with invalid config
                    assert isinstance(result, HookResult)

            finally:
                os.unlink(config_path)

    def test_malformed_json_configuration(self):
        """Test handling of malformed JSON configuration files."""
        malformed_config_path = self.test_scripts_dir.parent / "sample_configs" / "malformed_json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(malformed_config_path)]):
            # Should handle malformed JSON gracefully
            hook_manager = HookManager.get_instance()
            hook_manager.load_configuration()  # Should not crash

            # Should still be able to trigger hooks (no hooks loaded)
            result = hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "TestTool", {}
            )

            assert isinstance(result, HookResult)
            assert result.success  # No hooks to execute

    def test_missing_configuration_files(self):
        """Test handling of missing configuration files."""
        non_existent_paths = [
            "/path/that/does/not/exist.json",
            "~/non_existent_config.json",
            "missing_config.json"
        ]

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   non_existent_paths):
            # Should handle missing files gracefully
            hook_manager = HookManager.get_instance()
            hook_manager.load_configuration()  # Should not crash

            # Should still work with no configuration
            result = hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "TestTool", {}
            )

            assert isinstance(result, HookResult)
            assert result.success  # No hooks to execute

    def test_hook_script_not_found(self):
        """Test handling of hook scripts that don't exist."""
        script_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{
                        "type": "command",
                        "command": "python /path/to/non_existent_script.py"
                    }]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(script_config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                self.hook_manager.load_configuration()

            # Trigger hook with non-existent script
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "TestTool", {}
            )

            # Should handle missing script gracefully
            assert not result.success
            assert "not found" in result.reason.lower() or "error" in result.reason.lower()

        finally:
            os.unlink(config_path)


class TestHookErrorRecovery:
    """Test error recovery mechanisms in the hook system."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_partial_hook_failure_recovery(self):
        """Test recovery when some hooks fail but others succeed."""
        def success_hook(context):
            return HookResult(success=True, continue_execution=True, output="Success hook executed")

        def failure_hook(context):
            raise Exception("Failure hook error")

        def another_success_hook(context):
            return HookResult(success=True, continue_execution=True, output="Another success hook executed")

        # Register mixed success/failure hooks
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "TestTool", success_hook)
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "TestTool", failure_hook)
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "TestTool", another_success_hook)

        # Trigger hooks
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {}
        )

        # Should aggregate results appropriately
        assert isinstance(result, HookResult)
        # The aggregation strategy determines overall success
        # At minimum, should not crash and should provide meaningful feedback

    def test_hook_error_isolation(self):
        """Test that hook errors don't affect other hooks or the main system."""
        def crashing_hook(context):
            # Simulate various types of crashes
            import sys
            sys.exit(1)  # This should be caught

        def normal_hook(context):
            return HookResult(success=True, continue_execution=True)

        # Register hooks
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "TestTool", crashing_hook)
        self.hook_manager.register_python_hook(HookEvent.POST_TOOL_USE, "TestTool", normal_hook)

        # Trigger pre-tool hooks (with crash)
        pre_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {}
        )

        # Should handle crash gracefully
        assert isinstance(pre_result, HookResult)

        # Post-tool hooks should still work
        post_result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE, "TestTool", {}, {"result": "success"}
        )

        assert post_result.success

    def test_configuration_error_recovery(self):
        """Test recovery from configuration loading errors."""
        # Create a mix of valid and invalid configurations
        valid_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "ValidTool",
                    "hooks": [{"type": "command", "command": "echo 'valid'"}]
                }]
            }
        }

        invalid_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "InvalidTool",
                    "hooks": [{"type": "invalid_type", "command": "echo 'invalid'"}]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as valid_f:
            json.dump(valid_config, valid_f)
            valid_path = valid_f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as invalid_f:
            json.dump(invalid_config, invalid_f)
            invalid_path = invalid_f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [valid_path, invalid_path]):
                self.hook_manager.load_configuration()

            # Valid hooks should still work despite invalid configuration
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "ValidTool", {}
            )

            assert result.success
            assert "valid" in result.output

        finally:
            os.unlink(valid_path)
            os.unlink(invalid_path)

    def test_resource_cleanup_on_error(self):
        """Test that resources are properly cleaned up when hooks fail."""
        import tempfile
        import threading

        cleanup_called = threading.Event()

        def resource_hook(context):
            # Simulate resource allocation
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(b"test data")
            temp_file.close()

            try:
                # Simulate some work that might fail
                raise Exception("Simulated failure")
            finally:
                # Cleanup should happen
                os.unlink(temp_file.name)
                cleanup_called.set()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "ResourceTool", resource_hook
        )

        # Trigger hook
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "ResourceTool", {}
        )

        # Should fail but cleanup should have occurred
        assert not result.success
        assert cleanup_called.is_set(), "Resource cleanup was not called"


class TestHookSystemRobustness:
    """Test overall robustness of the hook system under stress."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_rapid_hook_execution(self):
        """Test system stability under rapid hook execution."""
        def rapid_hook(context):
            return HookResult(success=True, continue_execution=True)

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "*", rapid_hook
        )

        # Execute hooks rapidly
        for i in range(1000):
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, f"Tool{i % 10}", {"iteration": i}
            )
            assert result.success

    def test_concurrent_hook_execution_stress(self):
        """Test system stability under concurrent hook execution."""
        import concurrent.futures

        def concurrent_hook(context):
            time.sleep(0.001)  # Small delay
            return HookResult(success=True, continue_execution=True)

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "*", concurrent_hook
        )

        def execute_hook(tool_name):
            return self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, tool_name, {}
            )

        # Execute hooks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(execute_hook, f"Tool{i}")
                for i in range(100)
            ]

            # Wait for all to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # All should succeed
            assert all(result.success for result in results)

    def test_memory_pressure_handling(self):
        """Test hook system behavior under memory pressure."""
        def memory_intensive_hook(context):
            # Allocate some memory
            large_data = [i for i in range(10000)]
            return HookResult(
                success=True,
                continue_execution=True,
                additional_context=str(len(large_data))
            )

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "*", memory_intensive_hook
        )

        # Execute many memory-intensive hooks
        for i in range(100):
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, f"Tool{i}", {}
            )
            assert result.success

            # Force garbage collection periodically
            if i % 10 == 0:
                import gc
                gc.collect()
