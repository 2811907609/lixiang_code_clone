"""Public API for programmatic hook registration."""

import logging
from typing import Callable, Dict, List, Optional, Set, Tuple
from .hook_manager import HookManager
from .types import HookEvent, HookContext, HookResult


logger = logging.getLogger(__name__)


# Global registry to track registered hooks and prevent duplicates
_registered_hooks: Dict[str, Set[Tuple[HookEvent, str, str]]] = {}


def _generate_hook_id(event: HookEvent, matcher: str, func: Callable) -> str:
    """Generate a unique identifier for a hook registration."""
    func_name = getattr(func, '__name__', str(func))
    module_name = getattr(func, '__module__', 'unknown')
    return f"{module_name}.{func_name}:{event.value}:{matcher}"


def _is_hook_registered(hook_id: str, event: HookEvent, matcher: str, func_name: str) -> bool:
    """Check if a hook is already registered to prevent duplicates."""
    if hook_id not in _registered_hooks:
        _registered_hooks[hook_id] = set()

    hook_signature = (event, matcher, func_name)
    return hook_signature in _registered_hooks[hook_id]


def _mark_hook_registered(hook_id: str, event: HookEvent, matcher: str, func_name: str) -> None:
    """Mark a hook as registered."""
    if hook_id not in _registered_hooks:
        _registered_hooks[hook_id] = set()

    hook_signature = (event, matcher, func_name)
    _registered_hooks[hook_id].add(hook_signature)


def _unmark_hook_registered(hook_id: str, event: HookEvent, matcher: str, func_name: str) -> None:
    """Unmark a hook as registered."""
    if hook_id in _registered_hooks:
        hook_signature = (event, matcher, func_name)
        _registered_hooks[hook_id].discard(hook_signature)

        # Clean up empty entries
        if not _registered_hooks[hook_id]:
            del _registered_hooks[hook_id]


def register_hook(event: HookEvent, matcher: str, hook_func: Callable[[HookContext], HookResult],
                 timeout: int = 60, allow_duplicates: bool = False) -> None:
    """
    Register a Python function hook programmatically.

    Args:
        event: The hook event to register for
        matcher: Pattern to match tool names (supports regex and wildcards)
        hook_func: Python function that takes HookContext and returns HookResult
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Raises:
        ValueError: If parameters are invalid or hook is already registered

    Example:
        def my_validation_hook(context: HookContext) -> HookResult:
            if context.tool_name == "dangerous_tool":
                return HookResult.deny_result("Tool not allowed")
            return HookResult.success_result()

        register_hook(HookEvent.PRE_TOOL_USE, "dangerous_*", my_validation_hook)
    """
    # Validate parameters
    if not isinstance(event, HookEvent):
        raise ValueError(f"Invalid hook event: {event}")
    if not matcher or not isinstance(matcher, str):
        raise ValueError("Matcher must be a non-empty string")
    if not callable(hook_func):
        raise ValueError("Hook function must be callable")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    # Get function name for logging and tracking
    func_name = getattr(hook_func, '__name__', str(hook_func))

    # Check for duplicates if not allowed
    if not allow_duplicates:
        hook_id = _generate_hook_id(event, matcher, hook_func)

        if _is_hook_registered(hook_id, event, matcher, func_name):
            raise ValueError(f"Hook already registered: {func_name} for event {event.value} with matcher '{matcher}'")

    # Register the hook
    hook_manager = HookManager.get_instance()
    hook_manager.register_python_hook(event, matcher, hook_func, timeout)

    # Mark as registered
    if not allow_duplicates:
        hook_id = _generate_hook_id(event, matcher, hook_func)
        _mark_hook_registered(hook_id, event, matcher, func_name)

    logger.info(f"Registered hook: {func_name} for event {event.value} with matcher '{matcher}'")


def register_pre_tool_hook(matcher: str, hook_func: Callable[[HookContext], HookResult],
                          timeout: int = 60, allow_duplicates: bool = False) -> None:
    """
    Convenience function to register a pre-tool execution hook.

    Args:
        matcher: Pattern to match tool names
        hook_func: Python function that takes HookContext and returns HookResult
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        def validate_file_operations(context: HookContext) -> HookResult:
            if "delete" in context.tool_input.get("operation", ""):
                return HookResult.ask_result("Confirm file deletion?")
            return HookResult.success_result()

        register_pre_tool_hook("File*", validate_file_operations)
    """
    register_hook(HookEvent.PRE_TOOL_USE, matcher, hook_func, timeout, allow_duplicates)


def register_post_tool_hook(matcher: str, hook_func: Callable[[HookContext], HookResult],
                           timeout: int = 60, allow_duplicates: bool = False) -> None:
    """
    Convenience function to register a post-tool execution hook.

    Args:
        matcher: Pattern to match tool names
        hook_func: Python function that takes HookContext and returns HookResult
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        def log_tool_usage(context: HookContext) -> HookResult:
            print(f"Tool {context.tool_name} executed successfully")
            return HookResult.success_result()

        register_post_tool_hook("*", log_tool_usage)
    """
    register_hook(HookEvent.POST_TOOL_USE, matcher, hook_func, timeout, allow_duplicates)


def register_error_hook(matcher: str, hook_func: Callable[[HookContext], HookResult],
                       timeout: int = 60, allow_duplicates: bool = False) -> None:
    """
    Convenience function to register a post-tool error hook.

    Args:
        matcher: Pattern to match tool names
        hook_func: Python function that takes HookContext and returns HookResult
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        def handle_tool_errors(context: HookContext) -> HookResult:
            error_info = context.tool_response.get("error", "Unknown error")
            print(f"Tool {context.tool_name} failed: {error_info}")
            return HookResult.success_result()

        register_error_hook("*", handle_tool_errors)
    """
    register_hook(HookEvent.POST_TOOL_ERROR, matcher, hook_func, timeout, allow_duplicates)


def unregister_hook(event: HookEvent, matcher: str, hook_func: Callable[[HookContext], HookResult]) -> bool:
    """
    Unregister a previously registered Python hook.

    Args:
        event: The hook event to unregister from
        matcher: Pattern that was used to register the hook
        hook_func: The function that was registered

    Returns:
        True if the hook was found and removed, False otherwise

    Example:
        # Unregister a previously registered hook
        unregister_hook(HookEvent.PRE_TOOL_USE, "File*", my_validation_hook)
    """
    hook_manager = HookManager.get_instance()
    hook_registry = hook_manager.hook_registry

    # Find the matching Python hook
    python_hooks = hook_registry.list_python_hooks(event)[event]

    for hook in python_hooks:
        if hook.matcher == matcher and hook.function == hook_func:
            success = hook_registry.remove_python_hook(event, hook)

            if success:
                # Unmark as registered
                hook_id = _generate_hook_id(event, matcher, hook_func)
                func_name = getattr(hook_func, '__name__', str(hook_func))
                _unmark_hook_registered(hook_id, event, matcher, func_name)

                logger.info(f"Unregistered hook: {func_name} for event {event.value} with matcher '{matcher}'")

            return success

    return False


def list_registered_hooks(event: Optional[HookEvent] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    List all registered Python hooks.

    Args:
        event: Optional specific event to list hooks for

    Returns:
        Dictionary mapping event names to lists of hook information

    Example:
        hooks = list_registered_hooks()
        for event_name, hook_list in hooks.items():
            print(f"Event {event_name}: {len(hook_list)} hooks")
    """
    hook_manager = HookManager.get_instance()
    hook_registry = hook_manager.hook_registry

    python_hooks = hook_registry.list_python_hooks(event)

    result = {}
    for hook_event, hooks in python_hooks.items():
        hook_info_list = []
        for hook in hooks:
            func_name = getattr(hook.function, '__name__', str(hook.function))
            module_name = getattr(hook.function, '__module__', 'unknown')

            hook_info_list.append({
                "matcher": hook.matcher,
                "function_name": func_name,
                "module": module_name,
                "timeout": hook.timeout,
            })

        result[hook_event.value] = hook_info_list

    return result


def clear_registered_hooks(event: Optional[HookEvent] = None) -> int:
    """
    Clear registered Python hooks.

    Args:
        event: Optional specific event to clear hooks for. If None, clears all hooks.

    Returns:
        Number of hooks that were cleared

    Example:
        # Clear all pre-tool hooks
        cleared = clear_registered_hooks(HookEvent.PRE_TOOL_USE)
        print(f"Cleared {cleared} pre-tool hooks")
    """
    hook_manager = HookManager.get_instance()
    hook_registry = hook_manager.hook_registry

    # Count hooks before clearing
    if event is not None:
        hooks_before = hook_registry.list_python_hooks(event)[event]
        count = len(hooks_before)
        hook_registry.clear_hooks(event)
    else:
        all_hooks = hook_registry.list_python_hooks()
        count = sum(len(hooks) for hooks in all_hooks.values())
        hook_registry.clear_hooks()

    # Clear our registration tracking
    if event is not None:
        # Clear registrations for specific event
        for hook_id in list(_registered_hooks.keys()):
            _registered_hooks[hook_id] = {
                sig for sig in _registered_hooks[hook_id]
                if sig[0] != event
            }
            if not _registered_hooks[hook_id]:
                del _registered_hooks[hook_id]
    else:
        # Clear all registrations
        _registered_hooks.clear()

    logger.info(f"Cleared {count} Python hooks" + (f" for event {event.value}" if event else ""))
    return count


def hook(event: HookEvent, matcher: str, timeout: int = 60, allow_duplicates: bool = False):
    """
    Decorator for registering Python function hooks.

    Args:
        event: The hook event to register for
        matcher: Pattern to match tool names
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Returns:
        Decorator function

    Example:
        @hook(HookEvent.PRE_TOOL_USE, "File*")
        def validate_file_operations(context: HookContext) -> HookResult:
            if "delete" in context.tool_input.get("operation", ""):
                return HookResult.ask_result("Confirm file deletion?")
            return HookResult.success_result()
    """
    def decorator(func: Callable[[HookContext], HookResult]) -> Callable[[HookContext], HookResult]:
        register_hook(event, matcher, func, timeout, allow_duplicates)
        return func

    return decorator


def pre_tool_hook(matcher: str, timeout: int = 60, allow_duplicates: bool = False):
    """
    Decorator for registering pre-tool execution hooks.

    Args:
        matcher: Pattern to match tool names
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        @pre_tool_hook("File*")
        def validate_file_operations(context: HookContext) -> HookResult:
            if "delete" in context.tool_input.get("operation", ""):
                return HookResult.ask_result("Confirm file deletion?")
            return HookResult.success_result()
    """
    return hook(HookEvent.PRE_TOOL_USE, matcher, timeout, allow_duplicates)


def post_tool_hook(matcher: str, timeout: int = 60, allow_duplicates: bool = False):
    """
    Decorator for registering post-tool execution hooks.

    Args:
        matcher: Pattern to match tool names
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        @post_tool_hook("*")
        def log_tool_usage(context: HookContext) -> HookResult:
            print(f"Tool {context.tool_name} executed successfully")
            return HookResult.success_result()
    """
    return hook(HookEvent.POST_TOOL_USE, matcher, timeout, allow_duplicates)


def error_hook(matcher: str, timeout: int = 60, allow_duplicates: bool = False):
    """
    Decorator for registering post-tool error hooks.

    Args:
        matcher: Pattern to match tool names
        timeout: Timeout in seconds for hook execution (default: 60)
        allow_duplicates: Whether to allow duplicate registrations (default: False)

    Example:
        @error_hook("*")
        def handle_tool_errors(context: HookContext) -> HookResult:
            error_info = context.tool_response.get("error", "Unknown error")
            print(f"Tool {context.tool_name} failed: {error_info}")
            return HookResult.success_result()
    """
    return hook(HookEvent.POST_TOOL_ERROR, matcher, timeout, allow_duplicates)


def get_hook_statistics() -> Dict[str, any]:
    """
    Get statistics about registered hooks and the hook system.

    Returns:
        Dictionary containing hook statistics and system information

    Example:
        stats = get_hook_statistics()
        print(f"Total hooks: {stats['hook_counts']['total']}")
        print(f"Python hooks: {stats['hook_counts']['python_hooks']}")
    """
    hook_manager = HookManager.get_instance()
    stats = hook_manager.get_hook_statistics()

    # Add API-specific statistics
    stats["api_statistics"] = {
        "tracked_registrations": len(_registered_hooks),
        "total_tracked_hooks": sum(len(hooks) for hooks in _registered_hooks.values()),
    }

    return stats
