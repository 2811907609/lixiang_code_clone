"""Integration tests for HookManager with all hook system components."""

import json
import os
import tempfile
from unittest.mock import patch


from ai_agents.core.hooks import HookManager, HookEvent, HookContext, HookResult


class TestHookManagerIntegration:
    """Integration tests for HookManager."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after each test."""
        try:
            self.hook_manager.shutdown()
        except Exception:
            pass
        HookManager.reset_instance()

    def test_end_to_end_python_hook_workflow(self):
        """Test complete workflow with Python hooks."""
        # Track hook execution
        execution_log = []

        def pre_hook(context: HookContext) -> HookResult:
            execution_log.append(f"pre_hook: {context.tool_name}")
            assert context.hook_event_name == "PreToolUse"
            assert context.tool_input == {"param": "test_value"}
            return HookResult.success_result(output="Pre-hook executed")

        def post_hook(context: HookContext) -> HookResult:
            execution_log.append(f"post_hook: {context.tool_name}")
            assert context.hook_event_name == "PostToolUse"
            assert context.tool_response == {"result": "tool_executed"}
            return HookResult.success_result(output="Post-hook executed")

        # Register hooks
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            pre_hook
        )

        self.hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE,
            "TestTool",
            post_hook
        )

        # Trigger pre-tool hooks
        pre_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "TestTool",
            {"param": "test_value"}
        )

        assert pre_result.success is True
        assert pre_result.decision == "allow"
        assert "Pre-hook executed" in pre_result.output

        # Trigger post-tool hooks
        post_result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE,
            "TestTool",
            {"param": "test_value"},
            {"result": "tool_executed"}
        )

        assert post_result.success is True
        assert post_result.decision == "allow"
        assert "Post-hook executed" in post_result.output

        # Verify execution order
        assert execution_log == ["pre_hook: TestTool", "post_hook: TestTool"]

    def test_end_to_end_script_hook_workflow(self):
        """Test complete workflow with script hooks from configuration."""
        # Create a temporary config file
        config_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "TestTool",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'Script hook executed'",
                                "timeout": 30
                            }
                        ]
                    }
                ]
            },
            "hook_settings": {
                "default_timeout": 60
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name

        try:
            # Mock the config paths to use our temporary file
            with patch.object(self.hook_manager.config_loader, 'CONFIG_PATHS', [temp_config_path]):
                # Load configuration
                self.hook_manager.load_configuration()

                # Trigger hooks
                result = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    "TestTool",
                    {"param": "test_value"}
                )

                assert result.success is True
                assert result.decision == "allow"
                assert "Script hook executed" in result.output
        finally:
            os.unlink(temp_config_path)

    def test_mixed_hook_types_execution(self):
        """Test execution of both Python and script hooks together."""
        # Create a temporary config file for script hook
        config_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "TestTool",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'Script hook output'",
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
            # Register Python hook
            def python_hook(context: HookContext) -> HookResult:
                return HookResult.success_result(output="Python hook output")

            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE,
                "TestTool",
                python_hook
            )

            # Load script hooks from configuration
            with patch.object(self.hook_manager.config_loader, 'CONFIG_PATHS', [temp_config_path]):
                self.hook_manager.load_configuration()

                # Trigger hooks - should execute both Python and script hooks
                result = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    "TestTool",
                    {"param": "test_value"}
                )

                assert result.success is True
                assert result.decision == "allow"
                assert "Python hook output" in result.output
                assert "Script hook output" in result.output
        finally:
            os.unlink(temp_config_path)

    def test_hook_blocking_workflow(self):
        """Test workflow when hooks block execution."""
        def blocking_hook(context: HookContext) -> HookResult:
            return HookResult.deny_result("Tool execution blocked for security reasons")

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "DangerousTool",
            blocking_hook
        )

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "DangerousTool",
            {"dangerous_param": "malicious_value"}
        )

        assert result.success is True
        assert result.should_block() is True
        assert result.decision == "deny"
        assert "Tool execution blocked for security reasons" in result.reason

        # Test blocked response
        blocked_response = result.get_blocked_response()
        assert blocked_response["blocked"] is True
        assert "Tool execution blocked for security reasons" in blocked_response["reason"]
        assert blocked_response["decision"] == "deny"

    def test_pattern_matching_integration(self):
        """Test pattern matching with various tool names."""
        execution_log = []

        def wildcard_hook(context: HookContext) -> HookResult:
            execution_log.append(f"wildcard: {context.tool_name}")
            return HookResult.success_result()

        def file_hook(context: HookContext) -> HookResult:
            execution_log.append(f"file: {context.tool_name}")
            return HookResult.success_result()

        def edit_write_hook(context: HookContext) -> HookResult:
            execution_log.append(f"edit_write: {context.tool_name}")
            return HookResult.success_result()

        # Register hooks with different patterns
        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "*",  # Matches all tools
            wildcard_hook
        )

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "File.*",  # Matches tools starting with "File"
            file_hook
        )

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "Edit|Write",  # Matches "Edit" or "Write" tools
            edit_write_hook
        )

        # Test different tool names
        test_cases = [
            ("FileReader", ["wildcard: FileReader", "file: FileReader"]),
            ("FileWriter", ["wildcard: FileWriter", "file: FileWriter"]),
            ("Edit", ["wildcard: Edit", "edit_write: Edit"]),
            ("Write", ["wildcard: Write", "edit_write: Write"]),
            ("SomeTool", ["wildcard: SomeTool"]),
        ]

        for tool_name, expected_logs in test_cases:
            execution_log.clear()

            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE,
                tool_name,
                {"param": "value"}
            )

            assert result.success is True
            assert set(execution_log) == set(expected_logs), f"Tool {tool_name}: expected {expected_logs}, got {execution_log}"

    def test_configuration_reload_workflow(self):
        """Test configuration reloading workflow."""
        # Create initial config
        config_data_1 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Tool1",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'Config 1'",
                                "timeout": 30
                            }
                        ]
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data_1, f)
            temp_config_path = f.name

        try:
            # Load initial configuration
            with patch.object(self.hook_manager.config_loader, 'CONFIG_PATHS', [temp_config_path]):
                self.hook_manager.load_configuration()

                # Test initial config
                result1 = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    "Tool1",
                    {"param": "value"}
                )
                assert "Config 1" in result1.output

                # Update config file
                config_data_2 = {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Tool2",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "echo 'Config 2'",
                                        "timeout": 30
                                    }
                                ]
                            }
                        ]
                    }
                }

                with open(temp_config_path, 'w') as f:
                    json.dump(config_data_2, f)

                # Reload configuration
                self.hook_manager.reload_configuration()

                # Test that old hook is gone and new hook works
                result_old = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    "Tool1",
                    {"param": "value"}
                )
                assert result_old.decision == "allow"  # No hooks should match

                result_new = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    "Tool2",
                    {"param": "value"}
                )
                assert "Config 2" in result_new.output
        finally:
            os.unlink(temp_config_path)

    def test_hook_statistics_integration(self):
        """Test hook statistics functionality."""
        # Register some hooks
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "Tool1",
            test_hook
        )

        self.hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE,
            "Tool2",
            test_hook
        )

        # Create script hook via configuration
        config_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Tool3",
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
            with patch.object(self.hook_manager.config_loader, 'CONFIG_PATHS', [temp_config_path]):
                self.hook_manager.load_configuration()

                # Get statistics
                stats = self.hook_manager.get_hook_statistics()

                assert stats["configuration_loaded"] is True
                assert stats["hook_counts"]["python_hooks"] == 2
                assert stats["hook_counts"]["script_hooks"] == 1
                assert stats["hook_counts"]["total"] == 3

                # Check event-specific counts
                pre_tool_counts = stats["hook_counts_by_event"]["PreToolUse"]
                assert pre_tool_counts["python_hooks"] == 1
                assert pre_tool_counts["script_hooks"] == 1
                assert pre_tool_counts["total"] == 2

                post_tool_counts = stats["hook_counts_by_event"]["PostToolUse"]
                assert post_tool_counts["python_hooks"] == 1
                assert post_tool_counts["script_hooks"] == 0
                assert post_tool_counts["total"] == 1
        finally:
            os.unlink(temp_config_path)

    def test_error_handling_integration(self):
        """Test error handling across all components."""
        # Register a hook that raises an exception
        def failing_hook(context: HookContext) -> HookResult:
            raise Exception("Hook failed")

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "FailingTool",
            failing_hook
        )

        # Trigger hooks - should handle the error gracefully
        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "FailingTool",
            {"param": "value"}
        )

        # The hook system should handle the error gracefully and continue execution
        # The error information should be in the output
        assert result.output is None or "Hook failed" in result.output

        # System should still be functional after error
        def working_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(output="Working hook")

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "WorkingTool",
            working_hook
        )

        result2 = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            "WorkingTool",
            {"param": "value"}
        )

        assert result2.success is True
        assert "Working hook" in result2.output
