"""Unit tests for the programmatic hook registration API."""

from ai_agents.core.hooks import (
    HookEvent, HookContext, HookResult,
    register_hook, register_pre_tool_hook, register_post_tool_hook, register_error_hook,
    unregister_hook, list_registered_hooks, clear_registered_hooks,
    HookManager
)
from ai_agents.core.hooks.api import _registered_hooks


class TestProgrammaticRegistration:
    """Test programmatic hook registration functions."""

    def setup_method(self):
        """Set up test environment."""
        HookManager.reset_instance()
        _registered_hooks.clear()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()
        _registered_hooks.clear()

    def test_register_hook_basic(self):
        """Test basic hook registration."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        register_hook(HookEvent.PRE_TOOL_USE, "test_*", test_hook)

        hooks = list_registered_hooks(HookEvent.PRE_TOOL_USE)
        assert len(hooks[HookEvent.PRE_TOOL_USE.value]) == 1
        assert hooks[HookEvent.PRE_TOOL_USE.value][0]["matcher"] == "test_*"
        assert hooks[HookEvent.PRE_TOOL_USE.value][0]["function_name"] == "test_hook"

    def test_convenience_functions(self):
        """Test convenience registration functions."""
        def pre_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        def post_hook(context: HookContext) -> HookResult:
            return HookResult.success_result()

        def error_hook_func(context: HookContext) -> HookResult:
            return HookResult.success_result()

        register_pre_tool_hook("pre_*", pre_hook)
        register_post_tool_hook("post_*", post_hook)
        register_error_hook("error_*", error_hook_func)

        all_hooks = list_registered_hooks()

        assert len(all_hooks[HookEvent.PRE_TOOL_USE.value]) == 1
        assert all_hooks[HookEvent.PRE_TOOL_USE.value][0]["matcher"] == "pre_*"

        assert len(all_hooks[HookEvent.POST_TOOL_USE.value]) == 1
        assert all_hooks[HookEvent.POST_TOOL_USE.value][0]["matcher"] == "post_*"

        assert len(all_hooks[HookEvent.POST_TOOL_ERROR.value]) == 1
        assert all_hooks[HookEvent.POST_TOOL_ERROR.value][0]["matcher"] == "error_*"


def test_basic_functionality():
    """Simple test function to verify basic functionality."""
    def test_hook(context: HookContext) -> HookResult:
        return HookResult.success_result()

    # Clear any existing hooks
    clear_registered_hooks()

    # Test registration
    register_hook(HookEvent.PRE_TOOL_USE, "test_*", test_hook)

    # Verify registration
    hooks = list_registered_hooks(HookEvent.PRE_TOOL_USE)
    assert len(hooks[HookEvent.PRE_TOOL_USE.value]) == 1

    # Test unregistration
    success = unregister_hook(HookEvent.PRE_TOOL_USE, "test_*", test_hook)
    assert success is True

    # Verify unregistration
    hooks = list_registered_hooks(HookEvent.PRE_TOOL_USE)
    assert len(hooks[HookEvent.PRE_TOOL_USE.value]) == 0

    print("✓ Basic functionality test passed")


if __name__ == "__main__":
    test_basic_functionality()
