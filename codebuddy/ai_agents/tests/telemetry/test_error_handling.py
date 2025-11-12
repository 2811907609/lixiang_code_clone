"""
Tests for telemetry error handling and reliability infrastructure.

This module tests the fail-safe design principles of the telemetry system,
ensuring that telemetry failures never impact core system functionality.
"""

import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from ai_agents.telemetry.error_handler import (
    TelemetryErrorHandler,
    get_error_handler,
    safe_telemetry_operation,
    safe_telemetry_call,
    safe_storage_operation,
    safe_instrumentation,
    with_fallback_data,
    log_telemetry_error,
    ensure_safe_json_serialization,
    create_fallback_session,
)
from ai_agents.telemetry.types import (
    TaskStatus,
    TelemetrySession,
    EnvironmentInfo,
)


class TestTelemetryErrorHandler:
    """Test the TelemetryErrorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = TelemetryErrorHandler()

    def test_initialization(self):
        """Test error handler initialization."""
        assert self.error_handler._error_counts == {}
        assert self.error_handler._disabled_components == set()
        assert self.error_handler._corrupted_files == set()
        assert self.error_handler._max_errors_per_component == 10

    def test_handle_storage_error(self):
        """Test storage error handling."""
        error = Exception("Storage failed")

        # First error should be handled gracefully
        self.error_handler.handle_storage_error(error, "test_operation")

        assert self.error_handler._error_counts["storage_test_operation"] == 1
        assert "persistent_storage" not in self.error_handler._disabled_components

    def test_handle_storage_error_threshold(self):
        """Test storage error threshold handling."""
        error = Exception("Storage failed")

        # Trigger multiple errors to exceed threshold
        for i in range(11):
            self.error_handler.handle_storage_error(error, "test_operation")

        assert self.error_handler._error_counts["storage_test_operation"] == 11
        assert "persistent_storage" in self.error_handler._disabled_components

    def test_handle_instrumentation_error(self):
        """Test instrumentation error handling."""
        error = Exception("Instrumentation failed")
        component = "test_component"

        self.error_handler.handle_instrumentation_error(error, component)

        assert self.error_handler._error_counts[f"instrumentation_{component}"] == 1
        assert component in self.error_handler._disabled_components

    def test_handle_data_corruption(self):
        """Test data corruption handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_file.json"
            test_file.write_text("corrupted data")

            error = Exception("Corruption detected")
            self.error_handler.handle_data_corruption(test_file, error)

            assert str(test_file) in self.error_handler._corrupted_files
            # File should be archived (renamed)
            assert not test_file.exists()
            # Check that an archived file exists
            archived_files = list(Path(temp_dir).glob("test_file.corrupted_*"))
            assert len(archived_files) == 1

    def test_handle_serialization_error(self):
        """Test serialization error handling."""
        error = Exception("Serialization failed")
        data_type = "test_data"

        self.error_handler.handle_serialization_error(error, data_type)

        assert self.error_handler._error_counts[f"serialization_{data_type}"] == 1

    def test_handle_collection_error(self):
        """Test collection error handling."""
        error = Exception("Collection failed")
        operation = "test_operation"

        self.error_handler.handle_collection_error(error, operation)

        assert self.error_handler._error_counts[f"collection_{operation}"] == 1

    def test_is_component_disabled(self):
        """Test component disabled checking."""
        component = "test_component"

        assert not self.error_handler.is_component_disabled(component)

        # Disable the component
        self.error_handler._disabled_components.add(component)

        assert self.error_handler.is_component_disabled(component)

    def test_is_file_corrupted(self):
        """Test file corruption checking."""
        file_path = "/test/path/file.json"

        assert not self.error_handler.is_file_corrupted(file_path)

        # Mark file as corrupted
        self.error_handler._corrupted_files.add(file_path)

        assert self.error_handler.is_file_corrupted(file_path)

    def test_get_error_summary(self):
        """Test error summary generation."""
        # Add some errors
        self.error_handler._error_counts["test_error"] = 5
        self.error_handler._disabled_components.add("test_component")
        self.error_handler._corrupted_files.add("/test/file.json")

        summary = self.error_handler.get_error_summary()

        assert summary["error_counts"]["test_error"] == 5
        assert "test_component" in summary["disabled_components"]
        assert "/test/file.json" in summary["corrupted_files"]
        assert summary["total_errors"] == 5

    def test_reset_error_state(self):
        """Test error state reset."""
        # Add some errors
        self.error_handler._error_counts["test_error"] = 5
        self.error_handler._disabled_components.add("test_component")
        self.error_handler._corrupted_files.add("/test/file.json")

        self.error_handler.reset_error_state()

        assert self.error_handler._error_counts == {}
        assert self.error_handler._disabled_components == set()
        assert self.error_handler._corrupted_files == set()


class TestSafeTelemetryOperation:
    """Test the safe_telemetry_operation context manager."""

    def test_successful_operation(self):
        """Test successful operation within context."""
        result = None

        with safe_telemetry_operation("test_operation"):
            result = "success"

        assert result == "success"

    def test_exception_handling(self):
        """Test exception handling within context."""
        with safe_telemetry_operation("test_operation"):
            # This should not raise an exception
            raise Exception("Test error")

        # Should reach here without exception
        assert True

    def test_error_logging(self):
        """Test that errors are logged properly."""
        with patch('ai_agents.telemetry.error_handler._error_handler') as mock_handler:
            with safe_telemetry_operation("test_operation"):
                raise Exception("Test error")

            mock_handler.handle_collection_error.assert_called_once()


class TestSafeTelemetryCall:
    """Test the safe_telemetry_call decorator."""

    def test_successful_call(self):
        """Test successful function call."""
        @safe_telemetry_call("test_call")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_exception_handling(self):
        """Test exception handling in decorated function."""
        @safe_telemetry_call("test_call")
        def test_function():
            raise Exception("Test error")

        result = test_function()
        assert result is None  # Should return None on error

    def test_error_logging(self):
        """Test that errors are logged properly."""
        with patch('ai_agents.telemetry.error_handler._error_handler') as mock_handler:
            @safe_telemetry_call("test_call")
            def test_function():
                raise Exception("Test error")

            test_function()
            mock_handler.handle_collection_error.assert_called_once()


class TestSafeStorageOperation:
    """Test the safe_storage_operation decorator."""

    def test_successful_storage(self):
        """Test successful storage operation."""
        @safe_storage_operation("test_storage")
        def test_function():
            return True

        result = test_function()
        assert result is True

    def test_exception_handling(self):
        """Test exception handling in storage operation."""
        @safe_storage_operation("test_storage")
        def test_function():
            raise Exception("Storage error")

        result = test_function()
        assert result is False  # Should return False on error

    def test_error_logging(self):
        """Test that storage errors are logged properly."""
        with patch('ai_agents.telemetry.error_handler._error_handler') as mock_handler:
            @safe_storage_operation("test_storage")
            def test_function():
                raise Exception("Storage error")

            test_function()
            mock_handler.handle_storage_error.assert_called_once()


class TestSafeInstrumentation:
    """Test the safe_instrumentation decorator."""

    def test_successful_instrumentation(self):
        """Test successful instrumentation."""
        @safe_instrumentation("test_component")
        def test_function(original_method):
            return original_method

        original = Mock()
        result = test_function(original)
        assert result == original

    def test_exception_handling(self):
        """Test exception handling in instrumentation."""
        @safe_instrumentation("test_component")
        def test_function(self, original_method):
            raise Exception("Instrumentation error")

        original = Mock()
        result = test_function(Mock(), original)
        assert result == original  # Should return original method on error

    def test_error_logging(self):
        """Test that instrumentation errors are logged properly."""
        with patch('ai_agents.telemetry.error_handler._error_handler') as mock_handler:
            @safe_instrumentation("test_component")
            def test_function(original_method):
                raise Exception("Instrumentation error")

            test_function(Mock())
            mock_handler.handle_instrumentation_error.assert_called_once()


class TestWithFallbackData:
    """Test the with_fallback_data decorator."""

    def test_successful_operation(self):
        """Test successful operation returns actual data."""
        @with_fallback_data("fallback")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_fallback_on_exception(self):
        """Test fallback data is returned on exception."""
        @with_fallback_data("fallback")
        def test_function():
            raise Exception("Test error")

        result = test_function()
        assert result == "fallback"

    def test_fallback_on_none(self):
        """Test fallback data is returned when function returns None."""
        @with_fallback_data("fallback")
        def test_function():
            return None

        result = test_function()
        assert result == "fallback"

    def test_error_logging(self):
        """Test that errors are logged properly."""
        with patch('ai_agents.telemetry.error_handler._error_handler') as mock_handler:
            @with_fallback_data("fallback")
            def test_function():
                raise Exception("Test error")

            test_function()
            mock_handler.handle_collection_error.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions for error handling."""

    def test_log_telemetry_error(self):
        """Test telemetry error logging."""
        error = Exception("Test error")

        with patch('ai_agents.telemetry.error_handler.logger') as mock_logger:
            log_telemetry_error(error, "test_context")

            mock_logger.warning.assert_called_once()
            assert "test_context" in str(mock_logger.warning.call_args)

    def test_ensure_safe_json_serialization_success(self):
        """Test successful JSON serialization."""
        data = {"key": "value", "number": 42}

        result = ensure_safe_json_serialization(data)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_ensure_safe_json_serialization_failure(self):
        """Test JSON serialization failure handling."""
        # Create an object that can't be serialized even with default=str
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot convert to string")
            def __repr__(self):
                raise Exception("Cannot convert to repr")

        data = UnserializableObject()

        result = ensure_safe_json_serialization(data)

        # Should return error placeholder JSON
        parsed = json.loads(result)
        assert parsed["error"] == "Serialization failed"
        assert "data_type" in parsed
        assert "timestamp" in parsed

    def test_create_fallback_session(self):
        """Test fallback session creation."""
        session_id = "test_session"

        session = create_fallback_session(session_id)

        assert isinstance(session, TelemetrySession)
        assert session.session_id == session_id
        assert isinstance(session.environment, EnvironmentInfo)
        assert session.start_time is not None

    def test_create_fallback_session_with_errors(self):
        """Test fallback session creation when environment collection fails."""
        session_id = "test_session"

        # Mock platform functions to raise exceptions
        with patch('platform.system', side_effect=Exception("Platform error")):
            session = create_fallback_session(session_id)

            assert isinstance(session, TelemetrySession)
            assert session.session_id == session_id
            # Should have fallback environment info
            assert session.environment.os_type == "unknown"


class TestGlobalErrorHandler:
    """Test the global error handler instance."""

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns the same instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2
        assert isinstance(handler1, TelemetryErrorHandler)


class TestConcurrentErrorHandling:
    """Test error handling under concurrent conditions."""

    def test_concurrent_error_counting(self):
        """Test that error counting is thread-safe."""
        error_handler = TelemetryErrorHandler()
        errors = []

        def generate_errors():
            for i in range(10):
                try:
                    raise Exception(f"Error {i}")
                except Exception as e:
                    error_handler.handle_collection_error(e, "concurrent_test")
                    errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_errors)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have counted all errors
        assert error_handler._error_counts["collection_concurrent_test"] == 50
        assert len(errors) == 50

    def test_concurrent_component_disabling(self):
        """Test that component disabling is thread-safe."""
        error_handler = TelemetryErrorHandler()

        def disable_components(thread_id):
            for i in range(10):
                error_handler.handle_instrumentation_error(
                    Exception(f"Error {i}"),
                    f"component_{thread_id}_{i}"  # Make component names unique per thread
                )

        # Run multiple threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=disable_components, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have disabled all components (30 unique components)
        assert len(error_handler._disabled_components) == 30


class TestErrorHandlingIntegration:
    """Test error handling integration with telemetry components."""

    def test_collector_error_handling(self):
        """Test that collector methods handle errors gracefully."""
        from ai_agents.telemetry.collector import TelemetryCollector

        collector = TelemetryCollector()

        # These should not raise exceptions even with invalid data
        collector.start_task("", "")  # Empty strings
        collector.end_task("nonexistent", TaskStatus.COMPLETED)  # Non-existent task
        collector.record_llm_call("", -1, -1, -1.0)  # Invalid values

        # Should reach here without exceptions
        assert True

    def test_data_store_error_handling(self):
        """Test that data store methods handle errors gracefully."""
        from ai_agents.telemetry.data_store import TelemetryDataStore

        # Use invalid storage directory
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_dir = Path(temp_dir) / "nonexistent" / "deeply" / "nested"

            # This should not raise an exception
            store = TelemetryDataStore(storage_dir=invalid_dir)

            # These operations should not raise exceptions
            store.store_session_data("test", None)  # None session
            result = store.get_session_data("nonexistent")  # Non-existent session

            assert result is None  # Should return None gracefully

    def test_manager_error_handling(self):
        """Test that manager methods handle errors gracefully."""
        from ai_agents.telemetry.manager import TelemetryManager

        manager = TelemetryManager()

        # These should not raise exceptions
        manager.initialize()
        collector = manager.get_collector()
        manager.flush_data()
        manager.shutdown()

        assert collector is not None


class TestFailSafeDesignPrinciples:
    """Test that fail-safe design principles are maintained."""

    def test_never_block_core_functionality(self):
        """Test that telemetry errors never block core functionality."""
        # Simulate a core function that uses telemetry
        def core_function():
            with safe_telemetry_operation("core_operation"):
                # Simulate telemetry failure
                raise Exception("Telemetry failed")

            # Core functionality should continue
            return "core_result"

        result = core_function()
        assert result == "core_result"

    def test_graceful_degradation(self):
        """Test graceful degradation with missing data."""
        @with_fallback_data({"status": "degraded"})
        def get_telemetry_data():
            raise Exception("Data unavailable")

        result = get_telemetry_data()
        assert result["status"] == "degraded"

    def test_silent_failures(self):
        """Test that failures are silent but logged."""
        with patch('ai_agents.telemetry.error_handler.logger') as mock_logger:
            @safe_telemetry_call("silent_test")
            def failing_function():
                raise Exception("Silent failure")

            result = failing_function()

            # Should return None without raising
            assert result is None

            # Should have logged the error
            mock_logger.warning.assert_called()

    def test_resource_protection(self):
        """Test that resources are protected from exhaustion."""
        error_handler = TelemetryErrorHandler()

        # Generate many errors to test resource protection
        for i in range(100):
            error_handler.handle_collection_error(Exception(f"Error {i}"), "resource_test")

        # Error handler should still be functional
        summary = error_handler.get_error_summary()
        assert summary["total_errors"] == 100

        # Memory usage should be bounded (error counts are aggregated)
        assert len(error_handler._error_counts) == 1  # Only one error type


if __name__ == "__main__":
    pytest.main([__file__])
