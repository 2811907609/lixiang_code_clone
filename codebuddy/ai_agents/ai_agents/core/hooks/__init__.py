"""Hook system for AI agents framework."""

from .types import (
    HookEvent,
    HookContext,
    HookResult,
    ScriptHook,
    PythonHook,
)
from .hook_matcher import HookMatcher
from .hook_manager import HookManager
from .api import (
    register_hook,
    register_pre_tool_hook,
    register_post_tool_hook,
    register_error_hook,
    unregister_hook,
    list_registered_hooks,
    clear_registered_hooks,
    hook,
    pre_tool_hook,
    post_tool_hook,
    error_hook,
    get_hook_statistics,
)

__all__ = [
    # Core types
    "HookEvent",
    "HookContext",
    "HookResult",
    "ScriptHook",
    "PythonHook",
    # Core components
    "HookMatcher",
    "HookManager",
    # Public API functions
    "register_hook",
    "register_pre_tool_hook",
    "register_post_tool_hook",
    "register_error_hook",
    "unregister_hook",
    "list_registered_hooks",
    "clear_registered_hooks",
    "get_hook_statistics",
    # Decorators
    "hook",
    "pre_tool_hook",
    "post_tool_hook",
    "error_hook",
]
