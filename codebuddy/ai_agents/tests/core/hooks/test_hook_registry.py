"""Tests for the HookRegistry class."""

import pytest

from ai_agents.core.hooks.hook_registry import HookRegistry
from ai_agents.core.hooks.types import HookEvent, ScriptHook, PythonHook, HookContext, HookResult


class TestHookRegistry:
    """Test cases for HookRegistry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = HookRegistry()

        # Create sample hooks
        self.script_hook1 = ScriptHook(
            matcher="FileWriter",
            command="echo 'file writer hook'",
            timeout=30
        )

        self.script_hook2 = ScriptHook(
            matcher="*",
            command="echo 'universal hook'",
            timeout=60
        )

        def sample_python_function(context: HookContext) -> HookResult:
            return HookResult.success_result(f"Python hook for {context.tool_name}")

        self.python_hook1 = PythonHook(
            matcher="CodeEditor",
            function=sample_python_function,
            timeout=45
        )

        def another_python_function(context: HookContext) -> HookResult:
            return HookResult.success_result("Another python hook")

        self.python_hook2 = PythonHook(
            matcher="File.*",
            function=another_python_function,
            timeout=30
        )

    def test_initialization(self):
        """Test that HookRegistry initializes correctly."""
        registry = HookRegistry()

        # Check that all hook events have empty lists
        for event in HookEvent:
            assert event in registry.script_hooks
            assert event in registry.python_hooks
            assert registry.script_hooks[event] == []
            assert registry.python_hooks[event] == []

        # Check that hook matcher is initialized
        assert registry._hook_matcher is not None

    def test_register_script_hook(self):
        """Test registering script hooks."""
        # Register a script hook
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)

        # Verify it was registered
        hooks = self.registry.script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(hooks) == 1
        assert hooks[0] == self.script_hook1

        # Register another hook for the same event
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)

        # Verify both are registered
        hooks = self.registry.script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(hooks) == 2
        assert self.script_hook1 in hooks
        assert self.script_hook2 in hooks

    def test_register_script_hook_invalid_event(self):
        """Test registering script hook with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.register_script_hook("invalid_event", self.script_hook1)

    def test_register_script_hook_invalid_hook(self):
        """Test registering invalid script hook."""
        with pytest.raises(ValueError, match="Invalid script hook"):
            self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, "not_a_hook")

    def test_register_python_hook(self):
        """Test registering Python hooks."""
        # Register a Python hook
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook1)

        # Verify it was registered
        hooks = self.registry.python_hooks[HookEvent.POST_TOOL_USE]
        assert len(hooks) == 1
        assert hooks[0] == self.python_hook1

        # Register another hook for the same event
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Verify both are registered
        hooks = self.registry.python_hooks[HookEvent.POST_TOOL_USE]
        assert len(hooks) == 2
        assert self.python_hook1 in hooks
        assert self.python_hook2 in hooks

    def test_register_python_hook_invalid_event(self):
        """Test registering Python hook with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.register_python_hook("invalid_event", self.python_hook1)

    def test_register_python_hook_invalid_hook(self):
        """Test registering invalid Python hook."""
        with pytest.raises(ValueError, match="Invalid Python hook"):
            self.registry.register_python_hook(HookEvent.POST_TOOL_USE, "not_a_hook")

    def test_get_matching_hooks_exact_match(self):
        """Test getting hooks with exact tool name match."""
        # Register hooks
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)

        # Test exact match for script hook
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "FileWriter")
        assert len(matches) == 1
        assert matches[0] == self.script_hook1

        # Test exact match for Python hook
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "CodeEditor")
        assert len(matches) == 1
        assert matches[0] == self.python_hook1

    def test_get_matching_hooks_wildcard(self):
        """Test getting hooks with wildcard matcher."""
        # Register wildcard hook
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)

        # Test that wildcard matches any tool name
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "AnyTool")
        assert len(matches) == 1
        assert matches[0] == self.script_hook2

        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "FileWriter")
        assert len(matches) == 1
        assert matches[0] == self.script_hook2

    def test_get_matching_hooks_regex_pattern(self):
        """Test getting hooks with regex pattern matcher."""
        # Register regex pattern hook
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Test regex pattern matching
        matches = self.registry.get_matching_hooks(HookEvent.POST_TOOL_USE, "FileWriter")
        assert len(matches) == 1
        assert matches[0] == self.python_hook2

        matches = self.registry.get_matching_hooks(HookEvent.POST_TOOL_USE, "FileReader")
        assert len(matches) == 1
        assert matches[0] == self.python_hook2

        # Test non-matching tool name
        matches = self.registry.get_matching_hooks(HookEvent.POST_TOOL_USE, "CodeEditor")
        assert len(matches) == 0

    def test_get_matching_hooks_multiple_matches(self):
        """Test getting multiple matching hooks."""
        # Register multiple hooks that could match
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)  # wildcard
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook2)  # File.*

        # Test tool name that matches both
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "FileWriter")
        assert len(matches) == 2
        assert self.script_hook2 in matches
        assert self.python_hook2 in matches

    def test_get_matching_hooks_no_matches(self):
        """Test getting hooks when no matches exist."""
        # Register hooks that won't match
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)

        # Test tool name that doesn't match
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, "NonMatchingTool")
        assert len(matches) == 0

    def test_get_matching_hooks_invalid_event(self):
        """Test getting hooks with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.get_matching_hooks("invalid_event", "SomeTool")

    def test_get_matching_hooks_none_tool_name(self):
        """Test getting hooks with None tool name."""
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)  # wildcard

        # Should handle None tool name gracefully
        matches = self.registry.get_matching_hooks(HookEvent.PRE_TOOL_USE, None)
        assert len(matches) == 1  # wildcard should match empty string

    def test_list_script_hooks(self):
        """Test listing script hooks."""
        # Register hooks for different events
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.POST_TOOL_USE, self.script_hook2)

        # Test listing all script hooks
        all_hooks = self.registry.list_script_hooks()
        assert HookEvent.PRE_TOOL_USE in all_hooks
        assert HookEvent.POST_TOOL_USE in all_hooks
        assert len(all_hooks[HookEvent.PRE_TOOL_USE]) == 1
        assert len(all_hooks[HookEvent.POST_TOOL_USE]) == 1
        assert all_hooks[HookEvent.PRE_TOOL_USE][0] == self.script_hook1
        assert all_hooks[HookEvent.POST_TOOL_USE][0] == self.script_hook2

        # Test listing hooks for specific event
        pre_hooks = self.registry.list_script_hooks(HookEvent.PRE_TOOL_USE)
        assert len(pre_hooks) == 1
        assert HookEvent.PRE_TOOL_USE in pre_hooks
        assert len(pre_hooks[HookEvent.PRE_TOOL_USE]) == 1
        assert pre_hooks[HookEvent.PRE_TOOL_USE][0] == self.script_hook1

    def test_list_script_hooks_invalid_event(self):
        """Test listing script hooks with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.list_script_hooks("invalid_event")

    def test_list_python_hooks(self):
        """Test listing Python hooks."""
        # Register hooks for different events
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Test listing all Python hooks
        all_hooks = self.registry.list_python_hooks()
        assert HookEvent.PRE_TOOL_USE in all_hooks
        assert HookEvent.POST_TOOL_USE in all_hooks
        assert len(all_hooks[HookEvent.PRE_TOOL_USE]) == 1
        assert len(all_hooks[HookEvent.POST_TOOL_USE]) == 1
        assert all_hooks[HookEvent.PRE_TOOL_USE][0] == self.python_hook1
        assert all_hooks[HookEvent.POST_TOOL_USE][0] == self.python_hook2

        # Test listing hooks for specific event
        pre_hooks = self.registry.list_python_hooks(HookEvent.PRE_TOOL_USE)
        assert len(pre_hooks) == 1
        assert HookEvent.PRE_TOOL_USE in pre_hooks
        assert len(pre_hooks[HookEvent.PRE_TOOL_USE]) == 1
        assert pre_hooks[HookEvent.PRE_TOOL_USE][0] == self.python_hook1

    def test_list_python_hooks_invalid_event(self):
        """Test listing Python hooks with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.list_python_hooks("invalid_event")

    def test_remove_script_hook(self):
        """Test removing script hooks."""
        # Register hooks
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)

        # Verify both are registered
        hooks = self.registry.script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(hooks) == 2

        # Remove one hook
        result = self.registry.remove_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        assert result is True

        # Verify it was removed
        hooks = self.registry.script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(hooks) == 1
        assert hooks[0] == self.script_hook2

        # Try to remove the same hook again
        result = self.registry.remove_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        assert result is False

    def test_remove_script_hook_invalid_event(self):
        """Test removing script hook with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.remove_script_hook("invalid_event", self.script_hook1)

    def test_remove_python_hook(self):
        """Test removing Python hooks."""
        # Register hooks
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook1)
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Verify both are registered
        hooks = self.registry.python_hooks[HookEvent.POST_TOOL_USE]
        assert len(hooks) == 2

        # Remove one hook
        result = self.registry.remove_python_hook(HookEvent.POST_TOOL_USE, self.python_hook1)
        assert result is True

        # Verify it was removed
        hooks = self.registry.python_hooks[HookEvent.POST_TOOL_USE]
        assert len(hooks) == 1
        assert hooks[0] == self.python_hook2

        # Try to remove the same hook again
        result = self.registry.remove_python_hook(HookEvent.POST_TOOL_USE, self.python_hook1)
        assert result is False

    def test_remove_python_hook_invalid_event(self):
        """Test removing Python hook with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.remove_python_hook("invalid_event", self.python_hook1)

    def test_clear_hooks_specific_event(self):
        """Test clearing hooks for a specific event."""
        # Register hooks for multiple events
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.POST_TOOL_USE, self.script_hook2)
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Clear hooks for one event
        self.registry.clear_hooks(HookEvent.PRE_TOOL_USE)

        # Verify PRE_TOOL_USE hooks are cleared
        assert len(self.registry.script_hooks[HookEvent.PRE_TOOL_USE]) == 0
        assert len(self.registry.python_hooks[HookEvent.PRE_TOOL_USE]) == 0

        # Verify POST_TOOL_USE hooks are still there
        assert len(self.registry.script_hooks[HookEvent.POST_TOOL_USE]) == 1
        assert len(self.registry.python_hooks[HookEvent.POST_TOOL_USE]) == 1

    def test_clear_hooks_all_events(self):
        """Test clearing all hooks."""
        # Register hooks for multiple events
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.POST_TOOL_USE, self.script_hook2)
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)
        self.registry.register_python_hook(HookEvent.POST_TOOL_USE, self.python_hook2)

        # Clear all hooks
        self.registry.clear_hooks()

        # Verify all hooks are cleared
        for event in HookEvent:
            assert len(self.registry.script_hooks[event]) == 0
            assert len(self.registry.python_hooks[event]) == 0

    def test_clear_hooks_invalid_event(self):
        """Test clearing hooks with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.clear_hooks("invalid_event")

    def test_get_hook_count_specific_event(self):
        """Test getting hook count for specific event."""
        # Register hooks
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook2)
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)

        # Get count for specific event
        count = self.registry.get_hook_count(HookEvent.PRE_TOOL_USE)
        assert count["script_hooks"] == 2
        assert count["python_hooks"] == 1
        assert count["total"] == 3

    def test_get_hook_count_all_events(self):
        """Test getting hook count for all events."""
        # Register hooks for different events
        self.registry.register_script_hook(HookEvent.PRE_TOOL_USE, self.script_hook1)
        self.registry.register_script_hook(HookEvent.POST_TOOL_USE, self.script_hook2)
        self.registry.register_python_hook(HookEvent.PRE_TOOL_USE, self.python_hook1)
        self.registry.register_python_hook(HookEvent.POST_TOOL_ERROR, self.python_hook2)

        # Get total count
        count = self.registry.get_hook_count()
        assert count["script_hooks"] == 2
        assert count["python_hooks"] == 2
        assert count["total"] == 4

    def test_get_hook_count_invalid_event(self):
        """Test getting hook count with invalid event."""
        with pytest.raises(ValueError, match="Invalid hook event"):
            self.registry.get_hook_count("invalid_event")

    def test_get_hook_count_empty_registry(self):
        """Test getting hook count when registry is empty."""
        count = self.registry.get_hook_count()
        assert count["script_hooks"] == 0
        assert count["python_hooks"] == 0
        assert count["total"] == 0

        # Test specific event count when empty
        count = self.registry.get_hook_count(HookEvent.PRE_TOOL_USE)
        assert count["script_hooks"] == 0
        assert count["python_hooks"] == 0
        assert count["total"] == 0
