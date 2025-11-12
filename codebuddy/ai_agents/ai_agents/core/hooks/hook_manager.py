"""Hook manager as central coordination point for the hook system."""

import logging
import os
import uuid
from typing import Callable, Dict, Any, Optional
from threading import Lock

from .config_loader import ConfigurationLoader, ConfigurationError
from .hook_registry import HookRegistry
from .hook_executor import HookExecutor
from .hook_matcher import HookMatcher
from .error_handler import HookErrorHandler
from .types import HookEvent, HookContext, HookResult, PythonHook


logger = logging.getLogger(__name__)


class HookManager:
    """Central manager for all hook operations (Singleton)."""

    _instance: Optional['HookManager'] = None
    _lock = Lock()

    def __init__(self, debug_mode: bool = False):
        """Initialize the hook manager components.

        Args:
            debug_mode: Enable verbose debug logging
        """
        if HookManager._instance is not None:
            raise RuntimeError("HookManager is a singleton. Use get_instance() instead.")

        self.debug_mode = debug_mode
        self.config_loader = ConfigurationLoader()
        self.hook_registry = HookRegistry()
        self.hook_executor = HookExecutor(debug_mode=debug_mode)
        self.hook_matcher = HookMatcher()
        self.error_handler = HookErrorHandler(debug_mode=debug_mode)

        # Configuration state
        self._configuration_loaded = False
        self._session_id = str(uuid.uuid4())

        # Configure logging level based on debug mode
        if debug_mode:
            logger.setLevel(logging.DEBUG)

        logger.debug("HookManager initialized")

    @classmethod
    def get_instance(cls, debug_mode: bool = False) -> 'HookManager':
        """Get the singleton instance of HookManager.

        Args:
            debug_mode: Enable verbose debug logging (only used on first creation)
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(debug_mode=debug_mode)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.hook_executor.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down hook executor during reset: {e}")
            cls._instance = None

    def trigger_hooks(self, event: HookEvent, tool_name: str,
                     tool_input: Dict[str, Any], tool_response: Optional[Dict[str, Any]] = None) -> HookResult:
        """
        Trigger hooks for a specific event and tool.

        Args:
            event: The hook event that occurred
            tool_name: Name of the tool being executed
            tool_input: Input parameters passed to the tool
            tool_response: Response from the tool (for post-execution hooks)

        Returns:
            Aggregated HookResult from all matching hooks
        """
        try:
            # Ensure configuration is loaded
            if not self._configuration_loaded:
                self.load_configuration()

            # Create hook context
            context = HookContext(
                session_id=self._session_id,
                cwd=os.getcwd(),
                hook_event_name=event.value,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_response=tool_response
            )

            # Get matching hooks
            matching_hooks = self.hook_registry.get_matching_hooks(event, tool_name)

            if not matching_hooks:
                logger.debug(f"No hooks found for event {event.value} and tool {tool_name}")
                # Return a special result indicating no hooks were executed
                result = HookResult.success_result()
                result._no_hooks_executed = True  # Internal flag
                return result

            logger.debug(f"Found {len(matching_hooks)} matching hooks for event {event.value} and tool {tool_name}")

            # Prepare hooks for execution
            hooks_to_execute = []
            for hook in matching_hooks:
                if hasattr(hook, 'command'):  # ScriptHook
                    hooks_to_execute.append(('script', hook))
                elif hasattr(hook, 'function'):  # PythonHook
                    hooks_to_execute.append(('python', hook))
                else:
                    logger.warning(f"Unknown hook type: {type(hook)}")

            # Execute hooks and aggregate results
            result = self.hook_executor.execute_hooks_parallel(hooks_to_execute, context)

            logger.debug(f"Hook execution completed for {tool_name}: decision={result.decision}, success={result.success}")
            return result

        except Exception as e:
            logger.error(f"Error triggering hooks for {tool_name}: {str(e)}")
            return HookResult.error_result(
                f"Hook system error: {str(e)}",
                output=f"Event: {event.value}\nTool: {tool_name}\nError: {str(e)}"
            )

    def register_python_hook(self, event: HookEvent, matcher: str,
                           hook_func: Callable[[HookContext], HookResult],
                           timeout: int = 60) -> None:
        """
        Register a Python function hook programmatically.

        Args:
            event: The hook event to register for
            matcher: Pattern to match tool names
            hook_func: Python function to execute
            timeout: Timeout in seconds for hook execution

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            # Validate parameters
            if not isinstance(event, HookEvent):
                raise ValueError(f"Invalid hook event: {event}")
            if not matcher or not isinstance(matcher, str):
                raise ValueError("Matcher must be a non-empty string")
            if not callable(hook_func):
                raise ValueError("Hook function must be callable")
            if timeout <= 0:
                raise ValueError("Timeout must be positive")

            # Create Python hook
            python_hook = PythonHook(
                matcher=matcher,
                function=hook_func,
                timeout=timeout
            )

            # Register the hook
            self.hook_registry.register_python_hook(event, python_hook)

            logger.info(f"Registered Python hook for event {event.value} with matcher '{matcher}'")

        except Exception as e:
            logger.error(f"Error registering Python hook: {str(e)}")
            raise

    def load_configuration(self) -> None:
        """
        Load hook configurations from JSON files and register script hooks.

        Raises:
            ConfigurationError: If configuration loading fails critically
        """
        try:
            logger.debug("Loading hook configurations")

            # Load configurations from all sources
            config = self.config_loader.load_configurations()

            # Parse and register script hooks
            script_hooks = self.config_loader.parse_script_hooks_from_config(config)

            # Register all script hooks
            total_registered = 0
            for event, hooks in script_hooks.items():
                for hook in hooks:
                    self.hook_registry.register_script_hook(event, hook)
                    total_registered += 1

            self._configuration_loaded = True

            if total_registered > 0:
                logger.info(f"Successfully loaded and registered {total_registered} script hooks")
            else:
                logger.debug("No script hooks found in configuration")

        except ConfigurationError as e:
            self.error_handler.handle_configuration_error("hook configuration", e, "loading hook configurations")
            # Mark as loaded even if configuration failed to avoid repeated attempts
            self._configuration_loaded = True
            raise
        except Exception as e:
            self.error_handler.handle_configuration_error("hook configuration", e, "unexpected error during configuration loading")
            self._configuration_loaded = True
            raise ConfigurationError(f"Failed to load hook configuration: {str(e)}")

    def reload_configuration(self) -> None:
        """
        Reload hook configurations, clearing existing script hooks.

        This method clears all existing script hooks and reloads them from configuration.
        Python hooks registered programmatically are preserved.
        """
        try:
            logger.info("Reloading hook configurations")

            # Clear existing script hooks
            for event in HookEvent:
                # Get current script hooks and remove them
                script_hooks = self.hook_registry.list_script_hooks(event)[event]
                for hook in script_hooks:
                    self.hook_registry.remove_script_hook(event, hook)

            # Reset configuration state and reload
            self._configuration_loaded = False
            self.load_configuration()

            logger.info("Hook configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Error reloading configuration: {str(e)}")
            raise

    def get_hook_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about registered hooks and errors.

        Returns:
            Dictionary containing hook statistics and error information
        """
        try:
            stats = {
                "session_id": self._session_id,
                "configuration_loaded": self._configuration_loaded,
                "debug_mode": self.debug_mode,
                "hook_counts": self.hook_registry.get_hook_count(),
                "hook_counts_by_event": {}
            }

            # Get counts by event
            for event in HookEvent:
                event_counts = self.hook_registry.get_hook_count(event)
                stats["hook_counts_by_event"][event.value] = event_counts

            # Get pattern cache statistics
            stats["pattern_cache_size"] = self.hook_matcher.get_cache_size()

            # Get error statistics from both error handlers
            stats["error_statistics"] = {
                "hook_manager_errors": self.error_handler.get_error_statistics(),
                "hook_executor_errors": self.hook_executor.get_error_statistics()
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting hook statistics: {str(e)}")
            return {
                "error": str(e),
                "session_id": self._session_id,
                "configuration_loaded": self._configuration_loaded,
                "debug_mode": self.debug_mode
            }

    def clear_all_hooks(self) -> None:
        """
        Clear all registered hooks (both script and Python hooks).

        This is primarily useful for testing or when you want to start fresh.
        """
        try:
            logger.info("Clearing all registered hooks")
            self.hook_registry.clear_hooks()
            self.hook_matcher.clear_cache()
            logger.info("All hooks cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing hooks: {str(e)}")
            raise

    def clear_error_statistics(self) -> None:
        """Clear error statistics from all error handlers."""
        try:
            self.error_handler.clear_error_statistics()
            self.hook_executor.clear_error_statistics()
            logger.info("Error statistics cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing error statistics: {str(e)}")
            raise

    def set_debug_mode(self, debug_mode: bool) -> None:
        """Enable or disable debug mode for the entire hook system.

        Args:
            debug_mode: Whether to enable debug mode
        """
        try:
            self.debug_mode = debug_mode
            self.error_handler.set_debug_mode(debug_mode)
            self.hook_executor.set_debug_mode(debug_mode)

            if debug_mode:
                logger.setLevel(logging.DEBUG)
                logger.debug("Debug mode enabled for hook manager")
            else:
                logger.setLevel(logging.INFO)
                logger.info("Debug mode disabled for hook manager")
        except Exception as e:
            logger.error(f"Error setting debug mode: {str(e)}")
            raise

    def shutdown(self) -> None:
        """
        Shutdown the hook manager and clean up resources.
        """
        try:
            logger.info("Shutting down hook manager")
            self.hook_executor.shutdown()
            self.clear_all_hooks()
            logger.info("Hook manager shutdown completed")
        except Exception as e:
            logger.error(f"Error during hook manager shutdown: {str(e)}")
