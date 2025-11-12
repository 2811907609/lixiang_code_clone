"""
Backward compatibility tests for the hook system.
Ensures existing tools work unchanged with the hook system integration.
"""
import pytest
import time
from unittest.mock import patch, MagicMock

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.tools import tool


class TestToolDecoratorBackwardCompatibility:
    """Test that existing @tool decorated functions work unchanged."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_simple_tool_unchanged(self):
        """Test that simple tools work exactly as before."""
        @tool
        def simple_tool(message: str) -> str:
            """A simple tool for testing.

            Args:
                message: The message to process

            Returns:
                The processed message
            """
            return f"Processed: {message}"

        # Should work exactly as before
        result = simple_tool("test message")
        assert "Processed: test message" in str(result)

    def test_tool_with_multiple_parameters(self):
        """Test tools with multiple parameters work unchanged."""
        @tool
        def multi_param_tool(name: str, age: int, active: bool = True) -> dict:
            """Tool with multiple parameters.

            Args:
                name: The person's name
                age: The person's age
                active: Whether the person is active

            Returns:
                A dictionary with the processed information
            """
            return {
                "name": name,
                "age": age,
                "active": active,
                "processed": True
            }

        result = multi_param_tool("John", 30, False)
        expected = {
            "name": "John",
            "age": 30,
            "active": False,
            "processed": True
        }

        # Result should match exactly
        assert result == expected

    def test_tool_with_complex_return_types(self):
        """Test tools with complex return types work unchanged."""
        @tool
        def complex_return_tool(data: list) -> dict:
            """Tool that returns complex data structures.

            Args:
                data: A list of data items to process

            Returns:
                A dictionary with processed data and metadata
            """
            return {
                "input_length": len(data),
                "processed_data": [item.upper() if isinstance(item, str) else item for item in data],
                "metadata": {
                    "timestamp": "2024-01-01",
                    "version": "1.0"
                }
            }

        input_data = ["hello", "world", 123, True]
        result = complex_return_tool(input_data)

        assert result["input_length"] == 4
        assert result["processed_data"] == ["HELLO", "WORLD", 123, True]
        assert result["metadata"]["version"] == "1.0"

    def test_tool_with_exceptions(self):
        """Test that tools that raise exceptions still work unchanged."""
        @tool
        def exception_tool(should_fail: bool) -> str:
            """Tool that may raise exceptions.

            Args:
                should_fail: Whether the tool should fail

            Returns:
                A success message if not failing
            """
            if should_fail:
                raise ValueError("Tool failed as requested")
            return "Success"

        # Should work normally
        result = exception_tool(False)
        assert result == "Success"

        # Should still raise exceptions
        with pytest.raises(ValueError, match="Tool failed as requested"):
            exception_tool(True)

    def test_tool_with_side_effects(self):
        """Test that tools with side effects work unchanged."""
        side_effect_log = []

        @tool
        def side_effect_tool(action: str) -> str:
            """Tool that has side effects.

            Args:
                action: The action to perform

            Returns:
                A message about the executed action
            """
            side_effect_log.append(f"Action: {action}")
            return f"Executed: {action}"

        result = side_effect_tool("test_action")

        assert result == "Executed: test_action"
        assert "Action: test_action" in side_effect_log

    def test_tool_performance_unchanged(self):
        """Test that tool performance is not significantly impacted."""
        @tool
        def performance_tool(iterations: int) -> int:
            """Tool for performance testing.

            Args:
                iterations: Number of iterations to perform

            Returns:
                The sum of all iterations
            """
            total = 0
            for i in range(iterations):
                total += i
            return total

        # Measure execution time
        start_time = time.perf_counter()
        result = performance_tool(10000)
        end_time = time.perf_counter()

        execution_time = end_time - start_time

        # Should complete quickly and return correct result
        assert result == sum(range(10000))
        assert execution_time < 1.0  # Should be very fast

    def test_tool_metadata_preservation(self):
        """Test that tool metadata (docstrings, names, etc.) is preserved."""
        @tool
        def documented_tool(param: str) -> str:
            """This is a well-documented tool.

            Args:
                param: A string parameter

            Returns:
                A processed string
            """
            return f"Documented: {param}"

        # Function metadata should be preserved
        assert documented_tool.__name__ == "documented_tool"
        assert "well-documented tool" in documented_tool.__doc__

        # Should still work functionally
        result = documented_tool("test")
        assert "Documented: test" in str(result)


class TestExistingToolIntegration:
    """Test integration with existing tools from the codebase."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_file_operations_tools_unchanged(self):
        """Test that file operation tools work unchanged."""
        # Mock file operations to avoid actual file system changes
        with patch('builtins.open', create=True) as mock_open:
            with patch('os.path.exists', return_value=True):
                @tool
                def read_file_tool(filepath: str) -> str:
                    """Read content from a file.

                    Args:
                        filepath: Path to the file to read

                    Returns:
                        The file content as a string
                    """
                    with open(filepath, 'r') as f:
                        return f.read()

                # Mock file content
                mock_open.return_value.__enter__.return_value.read.return_value = "file content"

                result = read_file_tool("test.txt")
                assert "file content" in str(result)

    def test_data_processing_tools_unchanged(self):
        """Test that data processing tools work unchanged."""
        @tool
        def process_data_tool(data: list, operation: str) -> list:
            """Process data with specified operation.

            Args:
                data: The data list to process
                operation: The operation to perform (sort, reverse, unique)

            Returns:
                The processed data list
            """
            if operation == "sort":
                return sorted(data)
            elif operation == "reverse":
                return list(reversed(data))
            elif operation == "unique":
                return list(set(data))
            else:
                return data

        # Test various operations
        test_data = [3, 1, 4, 1, 5, 9, 2, 6]

        sorted_result = process_data_tool(test_data, "sort")
        assert sorted_result == [1, 1, 2, 3, 4, 5, 6, 9]

        reversed_result = process_data_tool(test_data, "reverse")
        assert reversed_result == [6, 2, 9, 5, 1, 4, 1, 3]

        unique_result = process_data_tool(test_data, "unique")
        assert set(unique_result) == {1, 2, 3, 4, 5, 6, 9}

    def test_api_tools_unchanged(self):
        """Test that API-related tools work unchanged."""
        with patch('requests.get') as mock_get:
            @tool
            def api_call_tool(url: str, params: dict = None) -> dict:
                """Make an API call and return the response.

                Args:
                    url: The API URL to call
                    params: Optional parameters for the API call

                Returns:
                    The API response as a dictionary
                """
                import requests
                response = requests.get(url, params=params)
                return response.json()

            # Mock API response
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "success", "data": "test"}
            mock_get.return_value = mock_response

            result = api_call_tool("https://api.example.com/test")
            assert result["status"] == "success"
            assert result["data"] == "test"


class TestHookSystemTransparency:
    """Test that the hook system is transparent when no hooks are configured."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_no_hooks_configured_transparency(self):
        """Test that tools work normally when no hooks are configured."""
        @tool
        def transparent_tool(value: str) -> str:
            """Tool to test transparency.

            Args:
                value: The value to process

            Returns:
                The processed value
            """
            return f"Transparent: {value}"

        # No hooks configured - should work exactly as before
        result = transparent_tool("test")
        assert "Transparent: test" in str(result)

    def test_empty_hook_configuration_transparency(self):
        """Test transparency with empty hook configuration."""
        import tempfile
        import json

        empty_config = {"hooks": {}, "hook_settings": {}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(empty_config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                self.hook_manager.load_configuration()

                @tool
                def empty_config_tool(message: str) -> str:
                    """Tool with empty hook config.

                    Args:
                        message: The message to process

                    Returns:
                        The processed message
                    """
                    return f"Empty config: {message}"

                result = empty_config_tool("test")
                assert "Empty config: test" in str(result)

        finally:
            import os
            os.unlink(config_path)

    def test_non_matching_hooks_transparency(self):
        """Test transparency when hooks don't match the tool."""
        import tempfile
        import json

        non_matching_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "DifferentTool",
                    "hooks": [{"type": "command", "command": "echo 'should not execute'"}]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(non_matching_config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                self.hook_manager.load_configuration()

                @tool
                def non_matching_tool(data: str) -> str:
                    """Tool that doesn't match any hooks.

                    Args:
                        data: The data to process

                    Returns:
                        The processed data
                    """
                    return f"Non-matching: {data}"

                result = non_matching_tool("test")
                assert "Non-matching: test" in str(result)

        finally:
            import os
            os.unlink(config_path)

    def test_hook_system_overhead_minimal(self):
        """Test that hook system adds minimal overhead when not used."""
        @tool
        def overhead_test_tool(iterations: int) -> int:
            """Tool to test overhead.

            Args:
                iterations: Number of iterations to perform

            Returns:
                The sum of the iterations
            """
            return sum(range(iterations))

        # Measure execution time with hook system (but no hooks)
        start_time = time.perf_counter()
        for _ in range(100):
            result = overhead_test_tool(1000)
        end_time = time.perf_counter()

        execution_time = end_time - start_time

        # Should be very fast even with hook system
        assert execution_time < 1.0  # Should complete 100 iterations in under 1 second
        assert result == sum(range(1000))  # Should return correct result


class TestLegacyToolCompatibility:
    """Test compatibility with legacy tool patterns and usage."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_legacy_tool_patterns(self):
        """Test that legacy tool patterns still work."""
        # Pattern 1: Simple function tool
        @tool
        def legacy_simple(text: str) -> str:
            """Simple legacy tool.

            Args:
                text: Text to convert to uppercase

            Returns:
                Uppercase text
            """
            return text.upper()

        assert legacy_simple("hello") == "HELLO"

        # Pattern 2: Tool with default parameters
        @tool
        def legacy_defaults(text: str, prefix: str = "Result: ") -> str:
            """Legacy tool with default parameters.

            Args:
                text: Text to process
                prefix: Prefix to add to the text

            Returns:
                Prefixed text
            """
            return f"{prefix}{text}"

        assert legacy_defaults("test") == "Result: test"
        assert legacy_defaults("test", "Output: ") == "Output: test"

        # Pattern 3: Tool with *args and **kwargs
        @tool
        def legacy_varargs(*args, **kwargs) -> dict:
            """Legacy tool with variable arguments.

            Args:
                *args: Variable positional arguments
                **kwargs: Variable keyword arguments

            Returns:
                Dictionary containing args and kwargs
            """
            return {"args": args, "kwargs": kwargs}

        result = legacy_varargs("a", "b", key="value")
        assert result["args"] == ("a", "b")
        assert result["kwargs"] == {"key": "value"}

    def test_legacy_error_handling(self):
        """Test that legacy error handling patterns still work."""
        @tool
        def legacy_error_tool(mode: str) -> str:
            """Legacy tool that can raise errors.

            Args:
                mode: The error mode to test

            Returns:
                Success message if no error
            """
            if mode == "value_error":
                raise ValueError("Legacy value error")
            elif mode == "type_error":
                raise TypeError("Legacy type error")
            elif mode == "custom_error":
                class CustomError(Exception):
                    pass
                raise CustomError("Legacy custom error")
            else:
                return "Success"

        # Should work normally
        assert legacy_error_tool("success") == "Success"

        # Should preserve exception types
        with pytest.raises(ValueError, match="Legacy value error"):
            legacy_error_tool("value_error")

        with pytest.raises(TypeError, match="Legacy type error"):
            legacy_error_tool("type_error")

        with pytest.raises(Exception, match="Legacy custom error"):
            legacy_error_tool("custom_error")

    def test_legacy_return_types(self):
        """Test that legacy return types are preserved."""
        @tool
        def legacy_none_return(should_return_none: bool):
            """Legacy tool that may return None.

            Args:
                should_return_none: Whether to return None

            Returns:
                None or a string
            """
            if should_return_none:
                return None
            return "Not None"

        assert legacy_none_return(True) is None
        assert legacy_none_return(False) == "Not None"

        @tool
        def legacy_generator_return(count: int):
            """Legacy tool that returns a generator.

            Args:
                count: Number of items to generate

            Returns:
                Generator yielding integers
            """
            for i in range(count):
                yield i

        result = list(legacy_generator_return(3))
        assert result == [0, 1, 2]

    def test_legacy_tool_composition(self):
        """Test that tool composition patterns still work."""
        @tool
        def legacy_tool_a(value: int) -> int:
            """Legacy tool A for composition.

            Args:
                value: Value to multiply

            Returns:
                Value multiplied by 2
            """
            return value * 2

        @tool
        def legacy_tool_b(value: int) -> int:
            """Legacy tool B for composition.

            Args:
                value: Value to add to

            Returns:
                Value plus 10
            """
            return value + 10

        @tool
        def legacy_composed_tool(value: int) -> int:
            """Legacy composed tool.

            Args:
                value: Value to process through composition

            Returns:
                Result of composed operations
            """
            intermediate = legacy_tool_a(value)
            return legacy_tool_b(intermediate)

        # Tool composition should work
        result = legacy_composed_tool(5)
        assert result == 20  # (5 * 2) + 10

    def test_legacy_tool_with_state(self):
        """Test that tools with state/closure still work."""
        counter = {"value": 0}

        @tool
        def legacy_stateful_tool(increment: int) -> int:
            """Legacy stateful tool.

            Args:
                increment: Value to increment counter by

            Returns:
                Current counter value
            """
            counter["value"] += increment
            return counter["value"]

        assert legacy_stateful_tool(1) == 1
        assert legacy_stateful_tool(5) == 6
        assert legacy_stateful_tool(2) == 8

    def test_legacy_tool_inheritance_patterns(self):
        """Test that inheritance patterns with tools still work."""
        class LegacyToolBase:
            def __init__(self, prefix: str):
                self.prefix = prefix

            @tool
            def base_tool(self, text: str) -> str:
                """Base tool method.

                Args:
                    text: Text to prefix

                Returns:
                    Prefixed text
                """
                return f"{self.prefix}: {text}"

        class LegacyToolDerived(LegacyToolBase):
            @tool
            def derived_tool(self, text: str) -> str:
                """Derived tool method.

                Args:
                    text: Text to process

                Returns:
                    Derived processed text
                """
                base_result = self.base_tool(text)
                return f"Derived {base_result}"

        instance = LegacyToolDerived("Test")

        base_result = instance.base_tool("hello")
        assert "Test: hello" in str(base_result)

        derived_result = instance.derived_tool("world")
        assert "Derived" in str(derived_result)
        assert "Test: world" in str(derived_result)
