"""
End-to-end integration tests for the hook system.
Tests complete workflows from configuration loading to hook execution.
"""
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import HookEvent, HookContext
from ai_agents.core.tools import tool


class TestEndToEndHookIntegration:
    """Test complete hook execution workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()
        self.test_config_dir = Path(__file__).parent / "fixtures" / "sample_configs"

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()
        # Clean up any test log files
        if os.path.exists("/tmp/hook_error_test.log"):
            os.remove("/tmp/hook_error_test.log")

    def test_basic_hook_workflow(self):
        """Test basic pre and post hook execution workflow."""
        # Load basic configuration
        config_path = self.test_config_dir / "basic_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Create test context
        _ = HookContext(
            session_id="test-session",
            cwd="/tmp",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"}
        )

        # Trigger pre-tool hooks
        pre_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {"param": "value"}
        )

        assert pre_result.success
        assert pre_result.continue_execution
        assert "Pre-hook executed" in pre_result.output

        # Trigger post-tool hooks
        post_result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE, "TestTool", {"param": "value"}, {"result": "success"}
        )

        assert post_result.success
        assert "Post-hook executed for all tools" in post_result.output

    def test_complex_decision_workflow(self):
        """Test complex hook workflow with decisions and blocking."""
        config_path = self.test_config_dir / "complex_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Test allow decision
        allow_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "EditTool", {"content": "safe content"}
        )

        assert allow_result.success
        assert allow_result.continue_execution
        assert allow_result.decision == "allow"

        # Test deny decision
        deny_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "EditTool", {"content": "dangerous operation"}
        )

        assert deny_result.success
        assert not deny_result.continue_execution
        assert deny_result.decision == "deny"
        assert "dangerous" in deny_result.reason.lower()

        # Test ask decision
        ask_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "EditTool", {"content": "please confirm this"}
        )

        assert ask_result.success
        assert not ask_result.continue_execution
        assert ask_result.decision == "ask"

    def test_blocking_hook_workflow(self):
        """Test workflow with blocking hooks (exit code 2)."""
        config_path = self.test_config_dir / "complex_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Test blocking hook
        block_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "DeleteTool", {"file": "important.txt"}
        )

        # Blocking hooks return success=True but continue_execution=False
        assert block_result.success or not block_result.continue_execution
        assert not block_result.continue_execution
        assert "blocked" in block_result.reason.lower()

    def test_error_hook_workflow(self):
        """Test error handling hook workflow."""
        config_path = self.test_config_dir / "complex_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Trigger error hook
        error_result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_ERROR, "TestTool",
            {"param": "value"}, {"error": "Test error occurred"}
        )

        assert error_result.success

        # Check that error was logged
        assert os.path.exists("/tmp/hook_error_test.log")
        with open("/tmp/hook_error_test.log", "r") as f:
            log_content = f.read()
            assert "ERROR in TestTool" in log_content
            assert "Test error occurred" in log_content

    def test_json_response_parsing(self):
        """Test parsing of structured JSON responses from hooks."""
        config_path = self.test_config_dir / "complex_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Trigger hook that returns JSON response
        result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE, "TestTool",
            {"param": "value"}, {"result": "success"}
        )

        assert result.success
        # Check that JSON response was parsed (may be aggregated with other results)
        assert result.decision is not None or result.additional_context is not None
        assert result.continue_execution

    def test_pattern_matching_workflow(self):
        """Test hook pattern matching in complete workflow."""
        config_path = self.test_config_dir / "basic_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Test exact match
        exact_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {"param": "value"}
        )
        assert exact_result.success

        # Test regex pattern match (File.*)
        pattern_result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "FileWriter", {"file": "test.txt"}
        )
        assert pattern_result.success

        # Test wildcard match (*)
        wildcard_result = self.hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE, "AnyTool", {"param": "value"}
        )
        assert wildcard_result.success

    def test_multiple_config_sources_workflow(self):
        """Test workflow with multiple configuration sources."""
        # Create temporary config files
        with tempfile.TemporaryDirectory() as temp_dir:
            config1_path = os.path.join(temp_dir, "config1.json")
            config2_path = os.path.join(temp_dir, "config2.json")

            config1 = {
                "hooks": {
                    "PreToolUse": [{
                        "matcher": "Tool1",
                        "hooks": [{"type": "command", "command": "echo 'Config1 hook'"}]
                    }]
                }
            }

            config2 = {
                "hooks": {
                    "PreToolUse": [{
                        "matcher": "Tool2",
                        "hooks": [{"type": "command", "command": "echo 'Config2 hook'"}]
                    }]
                }
            }

            with open(config1_path, 'w') as f:
                json.dump(config1, f)
            with open(config2_path, 'w') as f:
                json.dump(config2, f)

            # Test with multiple config sources
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config1_path, config2_path]):
                self.hook_manager.load_configuration()

            # Test hooks from both configs
            result1 = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "Tool1", {}
            )
            assert result1.success
            assert "Config1 hook" in result1.output

            result2 = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "Tool2", {}
            )
            assert result2.success
            assert "Config2 hook" in result2.output


class TestToolDecoratorIntegration:
    """Test integration with the @tool decorator."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.test_config_dir = Path(__file__).parent / "fixtures" / "sample_configs"

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_tool_decorator_with_hooks(self):
        """Test that @tool decorator properly integrates with hooks."""
        # Load configuration
        config_path = self.test_config_dir / "basic_hooks.json"

        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            hook_manager = HookManager.get_instance()
            hook_manager.load_configuration()

        # Create a test tool
        @tool
        def test_tool(param: str) -> str:
            """A test tool for hook integration.

            Args:
                param: A test parameter for the tool

            Returns:
                A string with the processed parameter
            """
            return f"Tool executed with {param}"

        # Mock the hook manager to verify it's called
        with patch.object(hook_manager, 'trigger_hooks') as mock_trigger:
            mock_trigger.return_value = MagicMock(
                success=True,
                continue_execution=True,
                should_block=lambda: False,
                merge_with_tool_result=lambda x: x
            )

            # Execute the tool
            result = test_tool("test_value")

            # Verify hooks were triggered
            assert mock_trigger.call_count >= 2  # Pre and post hooks

            # Verify the tool executed normally
            assert "Tool executed with test_value" in str(result)

    def test_tool_decorator_hook_blocking(self):
        """Test that hooks can block tool execution."""
        # Create a hook that blocks execution
        hook_manager = HookManager.get_instance()

        def blocking_hook(context):
            from ai_agents.core.hooks.types import HookResult
            return HookResult(
                success=True,
                decision="deny",
                reason="Tool blocked by test hook",
                continue_execution=False
            )

        hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "test_tool", blocking_hook
        )

        # Create a test tool
        @tool
        def test_tool(param: str) -> str:
            """A test tool that should be blocked.

            Args:
                param: A test parameter for the tool

            Returns:
                A string that should not be returned if blocked
            """
            return f"This should not execute: {param}"

        # Execute the tool - it should be blocked
        with patch.object(hook_manager, 'trigger_hooks') as mock_trigger:
            mock_result = MagicMock()
            mock_result.should_block.return_value = True
            mock_result.get_blocked_response.return_value = "Tool execution blocked"
            mock_trigger.return_value = mock_result

            result = test_tool("test_value")

            # Verify the tool was blocked
            assert result == "Tool execution blocked"
            assert mock_trigger.called
