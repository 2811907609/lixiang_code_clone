"""
Documentation tests for the hook system.
Tests that all public APIs have proper documentation and examples work.
"""
import inspect

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.config_loader import ConfigurationLoader
from ai_agents.core.hooks.hook_executor import HookExecutor
from ai_agents.core.hooks.hook_registry import HookRegistry
from ai_agents.core.hooks.hook_matcher import HookMatcher
from ai_agents.core.hooks.error_handler import HookErrorHandler
from ai_agents.core.hooks.types import HookEvent, HookContext, HookResult, ScriptHook, PythonHook


class TestPublicAPIDocumentation:
    """Test that all public APIs have proper documentation."""

    def test_hook_manager_documentation(self):
        """Test HookManager class documentation."""
        assert HookManager.__doc__ is not None
        assert len(HookManager.__doc__.strip()) > 0

        # Test public method documentation
        public_methods = [
            'get_instance',
            'trigger_hooks',
            'register_python_hook',
            'load_configuration'
        ]

        for method_name in public_methods:
            method = getattr(HookManager, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_configuration_loader_documentation(self):
        """Test ConfigurationLoader class documentation."""
        assert ConfigurationLoader.__doc__ is not None
        assert len(ConfigurationLoader.__doc__.strip()) > 0

        public_methods = [
            'load_configurations',
            'validate_configuration',
            'merge_configurations'
        ]

        for method_name in public_methods:
            method = getattr(ConfigurationLoader, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_hook_executor_documentation(self):
        """Test HookExecutor class documentation."""
        assert HookExecutor.__doc__ is not None
        assert len(HookExecutor.__doc__.strip()) > 0

        public_methods = [
            'execute_script_hook',
            'execute_python_hook',
            'aggregate_results'
        ]

        for method_name in public_methods:
            method = getattr(HookExecutor, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_hook_registry_documentation(self):
        """Test HookRegistry class documentation."""
        assert HookRegistry.__doc__ is not None
        assert len(HookRegistry.__doc__.strip()) > 0

        public_methods = [
            'register_script_hook',
            'register_python_hook',
            'get_matching_hooks'
        ]

        for method_name in public_methods:
            method = getattr(HookRegistry, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_hook_matcher_documentation(self):
        """Test HookMatcher class documentation."""
        assert HookMatcher.__doc__ is not None
        assert len(HookMatcher.__doc__.strip()) > 0

        public_methods = [
            'matches',
            'compile_pattern'
        ]

        for method_name in public_methods:
            method = getattr(HookMatcher, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_error_handler_documentation(self):
        """Test HookErrorHandler class documentation."""
        assert HookErrorHandler.__doc__ is not None
        assert len(HookErrorHandler.__doc__.strip()) > 0

        public_methods = [
            'handle_script_timeout',
            'handle_script_error',
            'handle_python_error',
            'handle_configuration_error'
        ]

        for method_name in public_methods:
            method = getattr(HookErrorHandler, method_name)
            assert method.__doc__ is not None, f"Method {method_name} lacks documentation"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty documentation"

    def test_data_types_documentation(self):
        """Test that all data types have proper documentation."""
        data_types = [HookEvent, HookContext, HookResult, ScriptHook, PythonHook]

        for data_type in data_types:
            assert data_type.__doc__ is not None, f"Type {data_type.__name__} lacks documentation"
            assert len(data_type.__doc__.strip()) > 0, f"Type {data_type.__name__} has empty documentation"


class TestDocumentationExamples:
    """Test that documentation examples work correctly."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_hook_manager_usage_example(self):
        """Test HookManager usage example from documentation."""
        # Example from documentation should work
        hook_manager = HookManager.get_instance()

        # Register a simple Python hook
        def example_hook(context):
            return HookResult(
                success=True,
                continue_execution=True,
                output=f"Hook executed for {context.tool_name}"
            )

        hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "ExampleTool", example_hook
        )

        # Trigger the hook
        result = hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "ExampleTool", {"param": "value"}
        )

        assert result.success
        assert "Hook executed for ExampleTool" in result.output

    def test_configuration_example(self):
        """Test configuration example from documentation."""
        import tempfile
        import json

        # Example configuration from documentation
        example_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "FileWriter",
                    "hooks": [{
                        "type": "command",
                        "command": "echo 'File operation detected'",
                        "timeout": 30
                    }]
                }]
            },
            "hook_settings": {
                "default_timeout": 60,
                "max_concurrent_hooks": 5
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(example_config, f)
            config_path = f.name

        try:
            from unittest.mock import patch
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                hook_manager = HookManager.get_instance()
                hook_manager.load_configuration()

                # Should load successfully
                result = hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, "FileWriter", {"file": "test.txt"}
                )

                assert result.success

        finally:
            import os
            os.unlink(config_path)

    def test_hook_result_example(self):
        """Test HookResult usage example from documentation."""
        # Example from documentation
        result = HookResult(
            success=True,
            decision="allow",
            reason="Operation approved",
            additional_context="File validation passed",
            continue_execution=True,
            output="Hook completed successfully"
        )

        # Test helper methods
        assert not result.should_block()
        assert result.continue_execution

        # Test blocking result
        blocking_result = HookResult(
            success=True,
            decision="deny",
            reason="Operation blocked",
            continue_execution=False
        )

        assert blocking_result.should_block()
        blocked_response = blocking_result.get_blocked_response()
        assert "blocked" in str(blocked_response).lower()

    def test_pattern_matching_examples(self):
        """Test pattern matching examples from documentation."""
        matcher = HookMatcher()

        # Examples from documentation
        assert matcher.matches("ExactTool", "ExactTool")  # Exact match
        assert matcher.matches("File.*", "FileWriter")    # Regex pattern
        assert matcher.matches("Edit|Write", "EditTool")  # Alternation
        assert matcher.matches("*", "AnyTool")            # Wildcard

        # Negative examples
        assert not matcher.matches("ExactTool", "DifferentTool")
        assert not matcher.matches("File.*", "DocumentTool")
        assert not matcher.matches("Edit|Write", "ReadTool")


class TestAPISignatureStability:
    """Test that public API signatures are stable and well-defined."""

    def test_hook_manager_signatures(self):
        """Test HookManager method signatures."""
        # get_instance should be a class method with no parameters
        sig = inspect.signature(HookManager.get_instance)
        assert len(sig.parameters) == 0

        # trigger_hooks should have specific parameters
        sig = inspect.signature(HookManager.trigger_hooks)
        expected_params = ['self', 'event', 'tool_name', 'tool_input', 'tool_response']
        assert list(sig.parameters.keys()) == expected_params

        # register_python_hook should have specific parameters
        sig = inspect.signature(HookManager.register_python_hook)
        expected_params = ['self', 'event', 'matcher', 'hook_func']
        assert list(sig.parameters.keys()) == expected_params

    def test_hook_result_signatures(self):
        """Test HookResult method signatures."""
        # should_block should have no parameters
        sig = inspect.signature(HookResult.should_block)
        assert len(sig.parameters) == 1  # Only 'self'

        # get_blocked_response should have no parameters
        sig = inspect.signature(HookResult.get_blocked_response)
        assert len(sig.parameters) == 1  # Only 'self'

        # merge_with_tool_result should have one parameter
        sig = inspect.signature(HookResult.merge_with_tool_result)
        assert len(sig.parameters) == 2  # 'self' and 'tool_result'

    def test_data_type_fields(self):
        """Test that data types have expected fields."""
        # HookContext should have specific fields
        context_fields = set(HookContext.__dataclass_fields__.keys())
        expected_context_fields = {
            'session_id', 'cwd', 'hook_event_name',
            'tool_name', 'tool_input', 'tool_response'
        }
        assert context_fields == expected_context_fields

        # HookResult should have specific fields
        result_fields = set(HookResult.__dataclass_fields__.keys())
        expected_result_fields = {
            'success', 'decision', 'reason', 'additional_context',
            'suppress_output', 'continue_execution', 'output'
        }
        assert result_fields == expected_result_fields

        # ScriptHook should have specific fields
        script_fields = set(ScriptHook.__dataclass_fields__.keys())
        expected_script_fields = {'matcher', 'command', 'timeout', 'working_directory'}
        assert script_fields == expected_script_fields

        # PythonHook should have specific fields
        python_fields = set(PythonHook.__dataclass_fields__.keys())
        expected_python_fields = {'matcher', 'function', 'timeout'}
        assert python_fields == expected_python_fields


class TestDocumentationCompleteness:
    """Test that documentation covers all important aspects."""

    def test_hook_events_documented(self):
        """Test that all hook events are documented."""
        for event in HookEvent:
            # Each event should have a meaningful name and value
            assert event.name is not None
            assert event.value is not None
            assert len(event.value) > 0

    def test_error_handling_documented(self):
        """Test that error handling is properly documented."""
        error_handler = HookErrorHandler()

        # All error handling methods should be documented
        error_methods = [
            'handle_script_timeout',
            'handle_script_error',
            'handle_python_error',
            'handle_configuration_error'
        ]

        for method_name in error_methods:
            method = getattr(error_handler, method_name)
            assert method.__doc__ is not None
            assert "error" in method.__doc__.lower() or "timeout" in method.__doc__.lower()

    def test_configuration_schema_documented(self):
        """Test that configuration schema is documented."""
        config_loader = ConfigurationLoader()

        # validate_configuration should document expected schema
        assert config_loader.validate_configuration.__doc__ is not None
        doc = config_loader.validate_configuration.__doc__.lower()
        assert "configuration" in doc or "schema" in doc or "validate" in doc

    def test_pattern_matching_documented(self):
        """Test that pattern matching is documented."""
        matcher = HookMatcher()

        # matches method should document pattern types
        assert matcher.matches.__doc__ is not None
        doc = matcher.matches.__doc__.lower()
        assert "pattern" in doc or "match" in doc

        # Should document different pattern types
        assert "regex" in doc or "wildcard" in doc or "exact" in doc


class TestDocumentationConsistency:
    """Test that documentation is consistent across the API."""

    def test_parameter_documentation_consistency(self):
        """Test that parameter documentation is consistent."""
        # All methods that take 'event' parameter should document it consistently
        methods_with_event = [
            HookManager.trigger_hooks,
            HookManager.register_python_hook,
            HookRegistry.register_script_hook,
            HookRegistry.register_python_hook,
            HookRegistry.get_matching_hooks
        ]

        for method in methods_with_event:
            if 'event' in inspect.signature(method).parameters:
                assert method.__doc__ is not None
                # Should mention event or HookEvent in documentation
                doc = method.__doc__.lower()
                assert "event" in doc or "hookevent" in doc

    def test_return_type_documentation_consistency(self):
        """Test that return type documentation is consistent."""
        # Methods that return HookResult should document it
        result_returning_methods = [
            HookManager.trigger_hooks,
            HookExecutor.execute_script_hook,
            HookExecutor.execute_python_hook,
            HookExecutor.aggregate_results
        ]

        for method in result_returning_methods:
            assert method.__doc__ is not None
            doc = method.__doc__.lower()
            # Should mention result or return in documentation
            assert "result" in doc or "return" in doc

    def test_exception_documentation_consistency(self):
        """Test that exception documentation is consistent."""
        # Methods that can raise exceptions should document them
        exception_methods = [
            ConfigurationLoader.load_configurations,
            ConfigurationLoader.validate_configuration,
            HookExecutor.execute_script_hook,
            HookExecutor.execute_python_hook
        ]

        for method in exception_methods:
            if method.__doc__ is not None:
                doc = method.__doc__.lower()
                # Should mention exceptions, errors, or raises
                # (Not all methods may document exceptions, but if they do, it should be consistent)
                if "raise" in doc or "exception" in doc or "error" in doc:
                    # If exceptions are documented, they should be specific
                    assert len([word for word in doc.split() if "error" in word or "exception" in word]) > 0


class TestUsageExamples:
    """Test that usage examples in documentation work correctly."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_basic_usage_example(self):
        """Test basic usage example works."""
        # This should be a common usage pattern from documentation
        hook_manager = HookManager.get_instance()

        def validation_hook(context):
            # Simple validation logic
            if "invalid" in str(context.tool_input):
                return HookResult(
                    success=True,
                    decision="deny",
                    reason="Invalid input detected",
                    continue_execution=False
                )
            return HookResult(success=True, continue_execution=True)

        hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "*", validation_hook
        )

        # Valid input should pass
        valid_result = hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {"data": "valid"}
        )
        assert valid_result.success
        assert valid_result.continue_execution

        # Invalid input should be blocked
        invalid_result = hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TestTool", {"data": "invalid"}
        )
        assert invalid_result.success
        assert not invalid_result.continue_execution
        assert invalid_result.decision == "deny"

    def test_advanced_usage_example(self):
        """Test advanced usage example works."""
        # Advanced example with multiple hooks and aggregation
        hook_manager = HookManager.get_instance()

        def logging_hook(context):
            return HookResult(
                success=True,
                continue_execution=True,
                output=f"Logged: {context.tool_name}"
            )

        def metrics_hook(context):
            return HookResult(
                success=True,
                continue_execution=True,
                additional_context="metrics_collected=true"
            )

        # Register multiple hooks
        hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE, "*", logging_hook
        )
        hook_manager.register_python_hook(
            HookEvent.POST_TOOL_USE, "*", metrics_hook
        )

        # Execute hooks
        result = hook_manager.trigger_hooks(
            HookEvent.POST_TOOL_USE, "TestTool",
            {"input": "test"}, {"output": "success"}
        )

        assert result.success
        # Should aggregate results from both hooks
        assert "Logged: TestTool" in result.output or result.additional_context is not None
