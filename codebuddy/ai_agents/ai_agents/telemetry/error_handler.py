"""
Telemetry error handling and reliability infrastructure.

This module implements fail-safe error handling that ensures telemetry failures
never impact core system functionality. All telemetry operations are designed
to gracefully degrade and continue operation even when errors occur.
"""

import logging
import traceback
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar, Union
from datetime import datetime
import json

from .types import TelemetrySession

# Configure telemetry-specific logger
logger = logging.getLogger("ai_agents.telemetry")
logger.setLevel(logging.WARNING)  # Only log warnings and errors by default

# Create console handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

F = TypeVar('F', bound=Callable[..., Any])


class TelemetryErrorHandler:
    """
    Centralized error handling for telemetry operations.

    Implements fail-safe design principles:
    - Never block core functionality
    - Graceful degradation for missing data
    - Silent failures with logging
    - Resource protection and cleanup
    """

    def __init__(self):
        self._error_counts: Dict[str, int] = {}
        self._disabled_components: set = set()
        self._max_errors_per_component = 10
        self._corrupted_files: set = set()

    def handle_storage_error(self, error: Exception, operation: str = "storage") -> None:
        """
        Handle storage-related errors.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        """
        error_key = f"storage_{operation}"
        self._increment_error_count(error_key)

        logger.warning(
            f"Telemetry storage error in {operation}: {error}. "
            f"Continuing with in-memory storage only."
        )

        # If too many storage errors, disable persistent storage
        if self._error_counts.get(error_key, 0) >= self._max_errors_per_component:
            self._disabled_components.add("persistent_storage")
            logger.error(
                f"Too many storage errors ({self._max_errors_per_component}). "
                f"Disabling persistent storage for this session."
            )

    def handle_instrumentation_error(self, error: Exception, component: str) -> None:
        """
        Handle instrumentation-related errors.

        Args:
            error: The exception that occurred
            component: Name of the component that failed
        """
        error_key = f"instrumentation_{component}"
        self._increment_error_count(error_key)

        logger.warning(
            f"Telemetry instrumentation error in {component}: {error}. "
            f"Disabling telemetry for this component."
        )

        # Disable the problematic component
        self._disabled_components.add(component)

        if self._error_counts.get(error_key, 0) >= self._max_errors_per_component:
            logger.error(
                f"Too many instrumentation errors in {component}. "
                f"Component permanently disabled for this session."
            )

    def handle_data_corruption(self, file_path: Path, error: Exception) -> None:
        """
        Handle corrupted telemetry data files.

        Args:
            file_path: Path to the corrupted file
            error: The exception that occurred during file operations
        """
        self._corrupted_files.add(str(file_path))

        logger.warning(
            f"Corrupted telemetry file detected: {file_path}. "
            f"Error: {error}. Archiving and starting fresh."
        )

        try:
            # Archive the corrupted file
            archive_path = file_path.with_suffix(f".corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if file_path.exists():
                file_path.rename(archive_path)
                logger.info(f"Corrupted file archived to: {archive_path}")
        except Exception as archive_error:
            logger.error(f"Failed to archive corrupted file {file_path}: {archive_error}")

    def handle_serialization_error(self, error: Exception, data_type: str) -> None:
        """
        Handle data serialization/deserialization errors.

        Args:
            error: The exception that occurred
            data_type: Type of data that failed to serialize
        """
        error_key = f"serialization_{data_type}"
        self._increment_error_count(error_key)

        logger.warning(
            f"Telemetry serialization error for {data_type}: {error}. "
            f"Skipping this data point."
        )

    def handle_collection_error(self, error: Exception, operation: str) -> None:
        """
        Handle data collection errors.

        Args:
            error: The exception that occurred
            operation: Description of the collection operation
        """
        error_key = f"collection_{operation}"
        self._increment_error_count(error_key)

        logger.warning(
            f"Telemetry collection error in {operation}: {error}. "
            f"Continuing without this data point."
        )

    def is_component_disabled(self, component: str) -> bool:
        """
        Check if a component has been disabled due to errors.

        Args:
            component: Name of the component to check

        Returns:
            True if the component is disabled, False otherwise
        """
        return component in self._disabled_components

    def is_file_corrupted(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file has been marked as corrupted.

        Args:
            file_path: Path to check

        Returns:
            True if the file is marked as corrupted, False otherwise
        """
        return str(file_path) in self._corrupted_files

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all errors encountered.

        Returns:
            Dictionary containing error statistics
        """
        return {
            "error_counts": self._error_counts.copy(),
            "disabled_components": list(self._disabled_components),
            "corrupted_files": list(self._corrupted_files),
            "total_errors": sum(self._error_counts.values()),
        }

    def reset_error_state(self) -> None:
        """Reset error tracking state (useful for testing)."""
        self._error_counts.clear()
        self._disabled_components.clear()
        self._corrupted_files.clear()

    def _increment_error_count(self, error_key: str) -> None:
        """Increment error count for a specific error type."""
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1


# Global error handler instance
_error_handler = TelemetryErrorHandler()


def get_error_handler() -> TelemetryErrorHandler:
    """Get the global telemetry error handler instance."""
    return _error_handler


@contextmanager
def safe_telemetry_operation(operation_name: str = "telemetry_operation"):
    """
    Context manager for safe telemetry operations.

    Ensures that any exceptions within the context are caught and handled
    gracefully without affecting the main application flow.

    Args:
        operation_name: Name of the operation for error reporting

    Example:
        with safe_telemetry_operation("token_collection"):
            collector.record_llm_call(model, tokens)
    """
    try:
        yield
    except Exception as e:
        _error_handler.handle_collection_error(e, operation_name)


def safe_telemetry_call(operation_name: str = "telemetry_call"):
    """
    Decorator for safe telemetry function calls.

    Wraps functions to ensure exceptions are caught and handled gracefully.

    Args:
        operation_name: Name of the operation for error reporting

    Example:
        @safe_telemetry_call("llm_instrumentation")
        def instrument_model_call(self, model, *args, **kwargs):
            # Telemetry code here
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _error_handler.handle_collection_error(e, operation_name)
                return None  # Return None on error to indicate failure
        return wrapper
    return decorator


def safe_storage_operation(operation_name: str = "storage_operation"):
    """
    Decorator for safe storage operations.

    Wraps storage functions to handle file I/O errors gracefully.

    Args:
        operation_name: Name of the storage operation

    Example:
        @safe_storage_operation("session_save")
        def save_session_data(self, session_data):
            # Storage code here
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _error_handler.handle_storage_error(e, operation_name)
                return False  # Return False to indicate storage failure
        return wrapper
    return decorator


def safe_instrumentation(component_name: str):
    """
    Decorator for safe instrumentation operations.

    Wraps instrumentation functions to handle errors without breaking
    the instrumented functionality.

    Args:
        component_name: Name of the component being instrumented

    Example:
        @safe_instrumentation("model_calls")
        def instrument_model_generate(self, original_method):
            # Instrumentation code here
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _error_handler.handle_instrumentation_error(e, component_name)
                # Return the original function/method unchanged on error
                if len(args) > 1:
                    return args[1]  # Assume second arg is original method
                elif len(args) == 1:
                    return args[0]  # Return first arg if only one
                return None
        return wrapper
    return decorator


def with_fallback_data(fallback_value: Any = None):
    """
    Decorator that provides fallback data when telemetry data collection fails.

    Args:
        fallback_value: Value to return if the operation fails

    Example:
        @with_fallback_data(TokenUsage())
        def get_token_usage(self):
            # Code that might fail
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result if result is not None else fallback_value
            except Exception as e:
                _error_handler.handle_collection_error(e, func.__name__)
                return fallback_value
        return wrapper
    return decorator


def log_telemetry_error(error: Exception, context: str = "telemetry") -> None:
    """
    Log telemetry errors with appropriate detail level.

    Args:
        error: The exception to log
        context: Context information about where the error occurred
    """
    logger.warning(f"Telemetry error in {context}: {error}")

    # Log full traceback at debug level
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Full traceback for {context}:\n{traceback.format_exc()}")


def ensure_safe_json_serialization(data: Any) -> str:
    """
    Safely serialize data to JSON with fallback handling.

    Args:
        data: Data to serialize

    Returns:
        JSON string, or error placeholder if serialization fails
    """
    try:
        # First try normal serialization
        return json.dumps(data, indent=2)
    except (TypeError, ValueError, RecursionError):
        # If that fails, try with default=str
        try:
            return json.dumps(data, default=str, indent=2)
        except Exception as e2:
            # If even that fails, return error structure
            _error_handler.handle_serialization_error(e2, type(data).__name__)
            return json.dumps({
                "error": "Serialization failed",
                "data_type": type(data).__name__,
                "timestamp": datetime.now().isoformat(),
                "original_error": str(e2),
            }, indent=2)


def create_fallback_session(session_id: str) -> TelemetrySession:
    """
    Create a minimal fallback session when normal session creation fails.

    Args:
        session_id: ID for the fallback session

    Returns:
        Minimal TelemetrySession with basic information
    """
    from .types import EnvironmentInfo

    try:
        import platform
        import sys
        import os

        env_info = EnvironmentInfo(
            os_type=platform.system(),
            os_version=platform.release(),
            python_version=sys.version.split()[0],
            working_directory=os.getcwd(),
            project_root=os.getcwd(),
            user_name=os.environ.get("USER") or os.environ.get("USERNAME"),
            timezone="UTC",
        )
    except Exception as e:
        _error_handler.handle_collection_error(e, "environment_info")
        env_info = EnvironmentInfo("unknown", "unknown", "unknown", "unknown", "unknown")

    return TelemetrySession(
        session_id=session_id,
        start_time=datetime.now(),
        environment=env_info,
    )
