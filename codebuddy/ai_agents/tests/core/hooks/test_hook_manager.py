"""Tests for the HookManager class."""

import json
import os
import tempfile
import threading
from unittest.mock import patch

import pytest

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import HookEvent, HookContext, HookResult
from ai_agents.core.hooks.config_loader import ConfigurationError


class TestHookManager:
    """Test cases for HookManager."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset singleton before each test
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after each test."""
        try:
            self.hook_manager.shutdown()
        except Exception:
            pass
        HookManager.reset_instance()

    def test_singleton_pattern(self):
        """Test that HookManager follows singleton pattern."""
        manager1 = HookManager.get_instance()
        manager2 = HookManager.get_instance()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        instances = []

        def create_instance():
            instances.append(HookManager.get_instance())

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    def test_direct_instantiation_raises_error(self):
        """Test that direct instantiation raises an error."""
        with pytest.raises(RuntimeError, match="HookManager is a singleton"):
            HookManager()

    def test_initialization_components(self):
        """Test that all components are properly initialized."""
        assert self.hook_manager.config_loader is not None
        assert self.hook_manager.hook_registry is not None
        assert self.hook_manager.hook_executor is not None
        assert self.hook_manager.hook_matcher is not None
        assert hasattr(self.hook_manager, '_session_id')
        assert not self.hook_manager._configuration_loaded

    def test_trigger_hooks_no_matching_hooks(self):
        """Test triggering hooks when no hooks match."""
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

        assert result.success is True
        assert result.decision == "allow"
        assert result.continue_execution is True

    def test_trigger_hooks_with_configuration_loading(self):
        """Test that configuration is loaded automatically when triggering hooks."""
        with patch.object(self.hook_manager, 'load_configuration') as mock_load:
            # Mock the load_configuration to set the flag
            def mock_load_config():
                self.hook_manager._configuration_loaded = True
            mock_load.side_effect = mock_load_config

            self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                {"param": "value"}
            )

            mock_load.assert_called_once()
            assert self.hook_manager._configuration_loaded is True

    def test_trigger_hooks_configuration_already_loaded(self):
        """Test that configuration is not loaded again if already loaded."""
        self.hook_manager._configuration_loaded = True

        with patch.object(self.hook_manager, 'load_configuration') as mock_load:
            self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                {"param": "value"}
            )

            mock_load.assert_not_called()

    def test_trigger_hooks_with_matching_hooks(self):
        """Test triggering hooks with matching hooks."""
        # Register a Python hook
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(output="Hook executed")

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook
        )

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

        assert result.success is True
        assert result.decision == "allow"
        assert "Hook executed" in result.output

    def test_trigger_hooks_error_handling(self):
        """Test error handling in trigger_hooks."""
        with patch.object(self.hook_manager.hook_registry, 'get_matching_hooks', side_effect=Exception("Test error")):
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                {"param": "value"}
            )

            assert result.success is False
            assert "Hook system error" in result.reason
            assert "Test error" in result.output

    def test_register_python_hook_success(self):
        """Test successful Python hook registration."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook,
            timeout=30
        )

        # Verify hook was registered
        hooks = self.hook_manager.hook_registry.list_python_hooks(HookEvent.PRE_TOOL_USE)
        assert len(hooks[HookEvent.PRE_TOOL_USE]) == 1

        registered_hook = hooks[HookEvent.PRE_TOOL_USE][0]
        assert registered_hook.matcher == "TestTool"
        assert registered_hook.function == test_hook
        assert registered_hook.timeout == 30

    def test_register_python_hook_invalid_event(self):
        """Test Python hook registration with invalid event."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Invalid hook event"):
            self.hook_manager.register_python_hook(
                "invalid_event",
                "TestTool",
                test_hook
            )

    def test_register_python_hook_invalid_matcher(self):
        """Test Python hook registration with invalid matcher."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Matcher must be a non-empty string"):
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE,
                "",
                test_hook
            )

    def test_register_python_hook_invalid_function(self):
        """Test Python hook registration with invalid function."""
        with pytest.raises(ValueError, match="Hook function must be callable"):
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                "not_a_function"
            )

    def test_register_python_hook_invalid_timeout(self):
        """Test Python hook registration with invalid timeout."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Timeout must be positive"):
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                test_hook,
                timeout=0
            )

    def test_load_configuration_success(self):
        """Test successful configuration loading."""
        # Create a temporary config file
        config_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "TestTool",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo test",
                                "timeout": 30
                            }
                        ]
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name

        try:
            # Mock the config paths to use our temporary file
            with patch.object(self.hook_manager.config_loader, 'CONFIG_PATHS', [temp_config_path]):
                self.hook_manager.load_configuration()

                assert self.hook_manager._configuration_loaded is True

                # Verify script hook was registered
                hooks = self.hook_manager.hook_registry.list_script_hooks(HookEvent.PRE_TOOL_USE)
                assert len(hooks[HookEvent.PRE_TOOL_USE]) == 1

                registered_hook = hooks[HookEvent.PRE_TOOL_USE][0]
                assert registered_hook.matcher == "TestTool"
                assert registered_hook.command == "echo test"
                assert registered_hook.timeout == 30
        finally:
            os.unlink(temp_config_path)

    def test_load_configuration_error_handling(self):
        """Test configuration loading error handling."""
        with patch.object(self.hook_manager.config_loader, 'load_configurations', side_effect=ConfigurationError("Test error")):
            with pytest.raises(ConfigurationError, match="Test error"):
                self.hook_manager.load_configuration()

            # Should still mark as loaded to avoid repeated attempts
            assert self.hook_manager._configuration_loaded is True

    def test_load_configuration_unexpected_error(self):
        """Test configuration loading with unexpected error."""
        with patch.object(self.hook_manager.config_loader, 'load_configurations', side_effect=Exception("Unexpected error")):
            with pytest.raises(ConfigurationError, match="Failed to load hook configuration"):
                self.hook_manager.load_configuration()

            assert self.hook_manager._configuration_loaded is True

    def test_reload_configuration(self):
        """Test configuration reloading."""
        # First, register some hooks
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook
        )

        # Mock script hook registration
        with patch.object(self.hook_manager.config_loader, 'load_configurations', return_value={"hooks": {}}):
            with patch.object(self.hook_manager.config_loader, 'parse_script_hooks_from_config', return_value={}):
                self.hook_manager._configuration_loaded = True

                # Add a mock script hook to test clearing
                from ai_agents.core.hooks.types import ScriptHook
                script_hook = ScriptHook(matcher="TestScript", command="echo test")
                self.hook_manager.hook_registry.register_script_hook(HookEvent.PRE_TOOL_USE, script_hook)

                # Verify script hook exists
                script_hooks_before = self.hook_manager.hook_registry.list_script_hooks(HookEvent.PRE_TOOL_USE)
                assert len(script_hooks_before[HookEvent.PRE_TOOL_USE]) == 1

                # Reload configuration
                self.hook_manager.reload_configuration()

                # Script hooks should be cleared, Python hooks should remain
                script_hooks_after = self.hook_manager.hook_registry.list_script_hooks(HookEvent.PRE_TOOL_USE)
                python_hooks_after = self.hook_manager.hook_registry.list_python_hooks(HookEvent.PRE_TOOL_USE)

                assert len(script_hooks_after[HookEvent.PRE_TOOL_USE]) == 0
                assert len(python_hooks_after[HookEvent.PRE_TOOL_USE]) == 1

    def test_reload_configuration_error_handling(self):
        """Test reload configuration error handling."""
        with patch.object(self.hook_manager, 'load_configuration', side_effect=Exception("Reload error")):
            with pytest.raises(Exception, match="Reload error"):
                self.hook_manager.reload_configuration()

    def test_get_hook_statistics(self):
        """Test getting hook statistics."""
        # Register some hooks
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook
        )

        stats = self.hook_manager.get_hook_statistics()

        assert "session_id" in stats
        assert "configuration_loaded" in stats
        assert "hook_counts" in stats
        assert "hook_counts_by_event" in stats
        assert "pattern_cache_size" in stats

        assert stats["configuration_loaded"] is False
        assert stats["hook_counts"]["python_hooks"] == 1
        assert stats["hook_counts"]["total"] == 1

    def test_get_hook_statistics_error_handling(self):
        """Test hook statistics error handling."""
        with patch.object(self.hook_manager.hook_registry, 'get_hook_count', side_effect=Exception("Stats error")):
            stats = self.hook_manager.get_hook_statistics()

            assert "error" in stats
            assert "Stats error" in stats["error"]
            assert "session_id" in stats
            assert "configuration_loaded" in stats

    def test_clear_all_hooks(self):
        """Test clearing all hooks."""
        # Register some hooks
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook
        )

        # Verify hooks exist
        stats_before = self.hook_manager.get_hook_statistics()
        assert stats_before["hook_counts"]["total"] > 0

        # Clear all hooks
        self.hook_manager.clear_all_hooks()

        # Verify hooks are cleared
        stats_after = self.hook_manager.get_hook_statistics()
        assert stats_after["hook_counts"]["total"] == 0
        assert stats_after["pattern_cache_size"] == 0

    def test_clear_all_hooks_error_handling(self):
        """Test clear all hooks error handling."""
        with patch.object(self.hook_manager.hook_registry, 'clear_hooks', side_effect=Exception("Clear error")):
            with pytest.raises(Exception, match="Clear error"):
                self.hook_manager.clear_all_hooks()

    def test_shutdown(self):
        """Test hook manager shutdown."""
        with patch.object(self.hook_manager.hook_executor, 'shutdown') as mock_executor_shutdown:
            with patch.object(self.hook_manager, 'clear_all_hooks') as mock_clear_hooks:
                self.hook_manager.shutdown()

                mock_executor_shutdown.assert_called_once()
                mock_clear_hooks.assert_called_once()

    def test_shutdown_error_handling(self):
        """Test shutdown error handling."""
        with patch.object(self.hook_manager.hook_executor, 'shutdown', side_effect=Exception("Shutdown error")):
            # Should not raise exception, just log error
            self.hook_manager.shutdown()

    def test_hook_context_creation(self):
        """Test that hook context is created correctly."""
        def test_hook(context: HookContext) -> HookResult:
            # Verify context fields
            assert context.session_id == self.hook_manager._session_id
            assert context.cwd == os.getcwd()
            assert context.hook_event_name == "PreToolUse"
            assert context.tool_name == "TestTool"
            assert context.tool_input == {"param": "value"}
            assert context.tool_response is None
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            test_hook
        )

        self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

    def test_hook_context_with_response(self):
        """Test hook context creation with tool response."""
        def test_hook(context: HookContext) -> HookResult:
            assert context.tool_response == {"result": "success"}
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE,
            "TestTool",
            test_hook
        )

        self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE,
            "TestTool",
            {"param": "value"},
            {"result": "success"}
        )

    def test_multiple_hooks_execution(self):
        """Test execution of multiple matching hooks."""
        results = []

        def hook1(context: HookContext) -> HookResult:
            results.append("hook1")
            return HookResult.success_result(output="Hook 1 executed")

        def hook2(context: HookContext) -> HookResult:
            results.append("hook2")
            return HookResult.success_result(output="Hook 2 executed")

        # Register multiple hooks with same matcher
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            hook1
        )
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            hook2
        )

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

        assert len(results) == 2
        assert "hook1" in results
        assert "hook2" in results
        assert result.success is True
        assert "Hook 1 executed" in result.output
        assert "Hook 2 executed" in result.output

    def test_hook_blocking_behavior(self):
        """Test that blocking hooks prevent execution."""
        def blocking_hook(context: HookContext) -> HookResult:
            return HookResult.deny_result("Operation blocked by hook")

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            blocking_hook
        )

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

        assert result.should_block() is True
        assert result.decision == "deny"
        assert "Operation blocked by hook" in result.reason

    def test_reset_instance(self):
        """Test resetting the singleton instance."""
        manager1 = HookManager.get_instance()
        session_id1 = manager1._session_id

        HookManager.reset_instance()

        manager2 = HookManager.get_instance()
        session_id2 = manager2._session_id

        assert manager1 is not manager2
        assert session_id1 != session_id2

    def test_concurrent_hook_execution(self):
        """Test that multiple hooks are executed and results are aggregated."""
        execution_order = []

        def hook1(context: HookContext) -> HookResult:
            execution_order.append("hook1")
            return HookResult.success_result(output="Hook 1 result")

        def hook2(context: HookContext) -> HookResult:
            execution_order.append("hook2")
            return HookResult.success_result(output="Hook 2 result")

        def hook3(context: HookContext) -> HookResult:
            execution_order.append("hook3")
            return HookResult.success_result(output="Hook 3 result")

        # Register multiple hooks
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            hook1
        )
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            hook2
        )
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            hook3
        )

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "value"}
        )

        assert result.success is True
        assert len(execution_order) == 3
        assert "hook1" in execution_order
        assert "hook2" in execution_order
        assert "hook3" in execution_order
        # Verify all hook outputs are aggregated
        assert "Hook 1 result" in result.output
        assert "Hook 2 result" in result.output
        assert "Hook 3 result" in result.output
