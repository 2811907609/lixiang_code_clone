"""Hook registry for managing hook storage and retrieval."""

from typing import Dict, List, Union
from .types import HookEvent, ScriptHook, PythonHook
from .hook_matcher import HookMatcher


class HookRegistry:
    """Manages registration and storage of hooks."""

    def __init__(self):
        """Initialize the hook registry with separate storage for different hook types."""
        self.script_hooks: Dict[HookEvent, List[ScriptHook]] = {
            event: [] for event in HookEvent
        }
        self.python_hooks: Dict[HookEvent, List[PythonHook]] = {
            event: [] for event in HookEvent
        }
        self._hook_matcher = HookMatcher()

    def register_script_hook(self, event: HookEvent, hook: ScriptHook) -> None:
        """
        Register a script hook for the specified event.

        Args:
            event: The hook event to register for
            hook: The script hook configuration

        Raises:
            ValueError: If event is not a valid HookEvent or hook is invalid
        """
        if not isinstance(event, HookEvent):
            raise ValueError(f"Invalid hook event: {event}")
        if not isinstance(hook, ScriptHook):
            raise ValueError(f"Invalid script hook: {hook}")

        self.script_hooks[event].append(hook)

    def register_python_hook(self, event: HookEvent, hook: PythonHook) -> None:
        """
        Register a Python function hook for the specified event.

        Args:
            event: The hook event to register for
            hook: The Python hook configuration

        Raises:
            ValueError: If event is not a valid HookEvent or hook is invalid
        """
        if not isinstance(event, HookEvent):
            raise ValueError(f"Invalid hook event: {event}")
        if not isinstance(hook, PythonHook):
            raise ValueError(f"Invalid Python hook: {hook}")

        self.python_hooks[event].append(hook)

    def get_matching_hooks(self, event: HookEvent, tool_name: str) -> List[Union[ScriptHook, PythonHook]]:
        """
        Get all hooks that match the specified event and tool name.

        Args:
            event: The hook event to match
            tool_name: The name of the tool to match against hook patterns

        Returns:
            List of matching hooks (both script and Python hooks)

        Raises:
            ValueError: If event is not a valid HookEvent
        """
        if not isinstance(event, HookEvent):
            raise ValueError(f"Invalid hook event: {event}")
        if tool_name is None:
            tool_name = ""

        matching_hooks = []

        # Check script hooks
        for script_hook in self.script_hooks[event]:
            if self._hook_matcher.matches(script_hook.matcher, tool_name):
                matching_hooks.append(script_hook)

        # Check Python hooks
        for python_hook in self.python_hooks[event]:
            if self._hook_matcher.matches(python_hook.matcher, tool_name):
                matching_hooks.append(python_hook)

        return matching_hooks

    def list_script_hooks(self, event: HookEvent = None) -> Dict[HookEvent, List[ScriptHook]]:
        """
        List all registered script hooks.

        Args:
            event: Optional specific event to list hooks for

        Returns:
            Dictionary mapping events to lists of script hooks
        """
        if event is not None:
            if not isinstance(event, HookEvent):
                raise ValueError(f"Invalid hook event: {event}")
            return {event: self.script_hooks[event].copy()}

        return {event: hooks.copy() for event, hooks in self.script_hooks.items()}

    def list_python_hooks(self, event: HookEvent = None) -> Dict[HookEvent, List[PythonHook]]:
        """
        List all registered Python hooks.

        Args:
            event: Optional specific event to list hooks for

        Returns:
            Dictionary mapping events to lists of Python hooks
        """
        if event is not None:
            if not isinstance(event, HookEvent):
                raise ValueError(f"Invalid hook event: {event}")
            return {event: self.python_hooks[event].copy()}

        return {event: hooks.copy() for event, hooks in self.python_hooks.items()}

    def remove_script_hook(self, event: HookEvent, hook: ScriptHook) -> bool:
        """
        Remove a specific script hook.

        Args:
            event: The hook event to remove from
            hook: The script hook to remove

        Returns:
            True if the hook was found and removed, False otherwise

        Raises:
            ValueError: If event is not a valid HookEvent
        """
        if not isinstance(event, HookEvent):
            raise ValueError(f"Invalid hook event: {event}")

        try:
            self.script_hooks[event].remove(hook)
            return True
        except ValueError:
            return False

    def remove_python_hook(self, event: HookEvent, hook: PythonHook) -> bool:
        """
        Remove a specific Python hook.

        Args:
            event: The hook event to remove from
            hook: The Python hook to remove

        Returns:
            True if the hook was found and removed, False otherwise

        Raises:
            ValueError: If event is not a valid HookEvent
        """
        if not isinstance(event, HookEvent):
            raise ValueError(f"Invalid hook event: {event}")

        try:
            self.python_hooks[event].remove(hook)
            return True
        except ValueError:
            return False

    def clear_hooks(self, event: HookEvent = None) -> None:
        """
        Clear all hooks for a specific event or all events.

        Args:
            event: Optional specific event to clear hooks for. If None, clears all hooks.

        Raises:
            ValueError: If event is not a valid HookEvent
        """
        if event is not None:
            if not isinstance(event, HookEvent):
                raise ValueError(f"Invalid hook event: {event}")
            self.script_hooks[event].clear()
            self.python_hooks[event].clear()
        else:
            for event in HookEvent:
                self.script_hooks[event].clear()
                self.python_hooks[event].clear()

    def get_hook_count(self, event: HookEvent = None) -> Dict[str, int]:
        """
        Get count of registered hooks.

        Args:
            event: Optional specific event to count hooks for

        Returns:
            Dictionary with hook counts
        """
        if event is not None:
            if not isinstance(event, HookEvent):
                raise ValueError(f"Invalid hook event: {event}")
            return {
                "script_hooks": len(self.script_hooks[event]),
                "python_hooks": len(self.python_hooks[event]),
                "total": len(self.script_hooks[event]) + len(self.python_hooks[event])
            }

        total_script = sum(len(hooks) for hooks in self.script_hooks.values())
        total_python = sum(len(hooks) for hooks in self.python_hooks.values())

        return {
            "script_hooks": total_script,
            "python_hooks": total_python,
            "total": total_script + total_python
        }
