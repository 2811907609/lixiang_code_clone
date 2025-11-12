"""Integration tests for tool decorator with hook system."""

import pytest
from ai_agents.core.tools import tool
from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import HookEvent, HookContext, HookResult


class TestToolDecoratorHookIntegration:
    """Test integration between tool decorator and hook system."""

    def setup_method(self):
        """Set up test environment."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        HookManager.reset_instance()

    def test_tool_decorator_without_hooks(self):
        """Test that tool decorator works normally when hooks are not available."""

        @tool
        def simple_tool(message: str) -> str:
            """A simple test tool.

            Args:
                message: The message to return
            """
            return f"Hello, {message}!"

        # Test normal execution
        result = simple_tool.forward(message="World")
        assert result == "Hello, World!"

    def test_tool_decorator_with_pre_hook_allow(self):
        """Test tool decorator with pre-execution hook that allows execution."""

        @tool
        def simple_tool(message: str) -> str:
            """A simple test tool.

            Args:
                message: The message to return
            """
            return f"Hello, {message}!"

        # Create a mock hook function that allows execution
        def allow_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(output="Pre-hook executed")

        # Register the hook
        hook_manager = HookManager.get_instance()
        hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "simple_tool",
            allow_hook
        )

        # Test execution
        result = simple_tool.forward(message="World")

        # Should return merged result with hook feedback
        assert isinstance(result, dict)
        assert result["result"] == "Hello, World!"
        assert "hook_feedback" in result
        assert result["hook_feedback"]["decision"] == "allow"

    def test_tool_decorator_with_pre_hook_deny(self):
        """Test tool decorator with pre-execution hook that denies execution."""

        @tool
        def simple_tool(message: str) -> str:
            """A simple test tool.

            Args:
                message: The message to return
            """
            return f"Hello, {message}!"

        # Create a mock hook function that denies execution
        def deny_hook(context: HookContext) -> HookResult:
            return HookResult.deny_result(
                reason="Tool execution denied by hook",
                output="Pre-hook denied execution"
            )

        # Register the hook
        hook_manager = HookManager.get_instance()
        hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE,
            "simple_tool",
            deny_hook
        )

        # Test execution
        result = simple_tool.forward(message="World")

        # Should return blocked response
        assert isinstance(result, dict)
        assert result["blocked"] is True
        assert "Tool execution denied by hook" in result["reason"]
        assert result["decision"] == "deny"

    def test_tool_decorator_with_post_hook(self):
        """Test tool decorator with post-execution hook."""

        @tool
        def simple_tool(message: str) -> str:
            """A simple test tool.

            Args:
                message: The message to return
            """
            return f"Hello, {message}!"

        # Create a mock hook function for post-execution
        def post_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(output="Post-hook executed")

        # Register the hook
        hook_manager = HookManager.get_instance()
        hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE,
            "simple_tool",
            post_hook
        )

        # Test execution
        result = simple_tool.forward(message="World")

        # Should return merged result with hook feedback
        assert isinstance(result, dict)
        assert result["result"] == "Hello, World!"
        assert "hook_feedback" in result
        assert result["hook_feedback"]["decision"] == "allow"

    def test_tool_decorator_with_error_hook(self):
        """Test tool decorator with error hook when tool raises exception."""

        @tool
        def failing_tool(message: str) -> str:
            """A tool that always fails.

            Args:
                message: The message (unused)
            """
            raise ValueError("Tool failed intentionally")

        # Create a mock hook function for error handling
        error_hook_called = False

        def error_hook(context: HookContext) -> HookResult:
            nonlocal error_hook_called
            error_hook_called = True
            assert context.tool_response is not None
            assert "error" in context.tool_response
            assert "Tool failed intentionally" in context.tool_response["error"]
            return HookResult.success_result(output="Error hook executed")

        # Register the hook
        hook_manager = HookManager.get_instance()
        hook_manager.register_python_hook(
            HookEvent.POST_TOOL_ERROR,
            "failing_tool",
            error_hook
        )

        # Test execution - should still raise the original exception
        with pytest.raises(ValueError, match="Tool failed intentionally"):
            failing_tool.forward(message="World")

        # Verify error hook was called
        assert error_hook_called

    def test_tool_decorator_backward_compatibility(self):
        """Test that enhanced tool decorator maintains backward compatibility."""

        # Test with existing tool patterns
        @tool
        def legacy_tool(x: int, y: int) -> int:
            """A legacy tool for testing backward compatibility.

            Args:
                x: First number
                y: Second number
            """
            return x + y

        # Test normal execution without hooks
        result = legacy_tool.forward(x=5, y=3)
        assert result == 8

        # Test that tool properties are preserved
        assert legacy_tool.name == "legacy_tool"
        assert "legacy tool" in legacy_tool.description.lower()
        assert "x" in legacy_tool.inputs
        assert "y" in legacy_tool.inputs
        assert legacy_tool.output_type == "integer"
