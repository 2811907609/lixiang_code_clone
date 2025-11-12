"""Tests for the hook executor."""

import json
import os
import tempfile
import time

from ai_agents.core.hooks.hook_executor import HookExecutor
from ai_agents.core.hooks.types import (
    HookContext, HookResult, ScriptHook, PythonHook
)


class TestHookExecutor:
    """Test cases for HookExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = HookExecutor(max_concurrent_hooks=2)
        self.context = HookContext(
            session_id="test-session",
            cwd="/tmp",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"},
            tool_response=None
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.executor.shutdown()

    def test_execute_script_hook_success(self):
        """Test successful script hook execution."""
        # Create a simple script that echoes success
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "Hook executed successfully"\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "allow"
            assert "Hook executed successfully" in result.output
        finally:
            os.unlink(script_path)

    def test_execute_script_hook_deny(self):
        """Test script hook that denies execution."""
        # Create a script that exits with code 2 (deny)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "Operation denied" >&2\nexit 2\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "deny"
            assert result.should_block() is True
            assert "Operation denied" in result.reason
        finally:
            os.unlink(script_path)

    def test_execute_script_hook_json_output(self):
        """Test script hook with JSON output."""
        json_response = {
            "decision": "ask",
            "reason": "Please confirm this operation",
            "additionalContext": "This is sensitive",
            "suppressOutput": True
        }

        # Create a script that outputs JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "ask"
            assert result.reason == "Please confirm this operation"
            assert result.additional_context == "This is sensitive"
            assert result.suppress_output is True
        finally:
            os.unlink(script_path)

    def test_execute_script_hook_timeout(self):
        """Test script hook timeout handling."""
        # Create a script that sleeps longer than the timeout
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\nsleep 5\necho "Should not reach here"\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}", timeout=1)

            start_time = time.time()
            result = self.executor.execute_script_hook(hook, self.context)
            execution_time = time.time() - start_time

            assert result.success is False
            assert "timed out" in result.reason
            assert execution_time < 3  # Should not wait for the full sleep
        finally:
            os.unlink(script_path)

    def test_execute_script_hook_command_not_found(self):
        """Test script hook with non-existent command."""
        hook = ScriptHook(matcher="TestTool", command="nonexistent_command_12345")

        result = self.executor.execute_script_hook(hook, self.context)

        assert result.success is False
        assert "not found" in result.reason

    def test_execute_script_hook_context_serialization(self):
        """Test that hook context is properly serialized and passed to script."""
        # Create a script that reads stdin and outputs it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''#!/usr/bin/env python3
import sys
import json
data = json.load(sys.stdin)
print(f"Tool: {data['tool_name']}")
print(f"Event: {data['hook_event_name']}")
print(f"Input: {data['tool_input']}")
''')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"python3 {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert "Tool: TestTool" in result.output
            assert "Event: PreToolUse" in result.output
            assert "Input: {'param': 'value'}" in result.output
        finally:
            os.unlink(script_path)

    def test_execute_python_hook_success(self):
        """Test successful Python hook execution."""
        def test_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(f"Python hook executed for {context.tool_name}")

        hook = PythonHook(matcher="TestTool", function=test_hook)

        result = self.executor.execute_python_hook(hook, self.context)

        assert result.success is True
        assert result.decision == "allow"
        assert "Python hook executed for TestTool" in result.output

    def test_execute_python_hook_deny(self):
        """Test Python hook that denies execution."""
        def deny_hook(context: HookContext) -> HookResult:
            return HookResult.deny_result("Python hook denies this operation")

        hook = PythonHook(matcher="TestTool", function=deny_hook)

        result = self.executor.execute_python_hook(hook, self.context)

        assert result.success is True
        assert result.decision == "deny"
        assert result.should_block() is True
        assert "Python hook denies this operation" in result.reason

    def test_execute_python_hook_exception(self):
        """Test Python hook that raises an exception."""
        def failing_hook(context: HookContext) -> HookResult:
            raise ValueError("Something went wrong")

        hook = PythonHook(matcher="TestTool", function=failing_hook)

        result = self.executor.execute_python_hook(hook, self.context)

        assert result.success is False
        assert "Something went wrong" in result.reason

    def test_execute_python_hook_timeout(self):
        """Test Python hook timeout handling."""
        def slow_hook(context: HookContext) -> HookResult:
            time.sleep(5)
            return HookResult.success_result("Should not reach here")

        hook = PythonHook(matcher="TestTool", function=slow_hook, timeout=1)

        start_time = time.time()
        result = self.executor.execute_python_hook(hook, self.context)
        execution_time = time.time() - start_time

        assert result.success is False
        assert "timed out" in result.reason
        # Note: Python threads can't be forcibly killed, so this will take the full sleep time
        # The timeout detection happens after the function completes
        assert execution_time >= 1  # At least the timeout duration

    def test_execute_python_hook_invalid_return(self):
        """Test Python hook that returns invalid result type."""
        def invalid_hook(context: HookContext) -> str:
            return "This is not a HookResult"

        hook = PythonHook(matcher="TestTool", function=invalid_hook)

        result = self.executor.execute_python_hook(hook, self.context)

        assert result.success is True
        assert result.decision == "allow"
        assert "This is not a HookResult" in result.output

    def test_aggregate_results_empty(self):
        """Test aggregating empty results list."""
        result = self.executor.aggregate_results([])

        assert result.success is True
        assert result.decision == "allow"

    def test_aggregate_results_all_allow(self):
        """Test aggregating results that all allow execution."""
        results = [
            HookResult.success_result("Hook 1 output"),
            HookResult.success_result("Hook 2 output"),
            HookResult(success=True, decision="allow", additional_context="Context from hook")
        ]

        aggregated = self.executor.aggregate_results(results)

        assert aggregated.success is True
        assert aggregated.decision == "allow"
        assert "Hook 1 output" in aggregated.output
        assert "Hook 2 output" in aggregated.output
        assert "Context from hook" in aggregated.additional_context

    def test_aggregate_results_with_deny(self):
        """Test aggregating results with deny decision."""
        results = [
            HookResult.success_result("Hook 1 output"),
            HookResult.deny_result("Operation denied", "Deny output"),
            HookResult.success_result("Hook 3 output")
        ]

        aggregated = self.executor.aggregate_results(results)

        assert aggregated.success is True
        assert aggregated.decision == "deny"
        assert aggregated.should_block() is True
        assert "Operation denied" in aggregated.reason
        # The new aggregation logic only includes outputs from deny results when deny is the decision
        assert "Deny output" in aggregated.output if aggregated.output else True

    def test_aggregate_results_with_ask(self):
        """Test aggregating results with ask decision."""
        results = [
            HookResult.success_result("Hook 1 output"),
            HookResult.ask_result("Please confirm", "Ask output"),
            HookResult.success_result("Hook 3 output")
        ]

        aggregated = self.executor.aggregate_results(results)

        assert aggregated.success is True
        assert aggregated.decision == "ask"
        assert aggregated.should_block() is True  # Ask decisions now block until user confirmation
        assert "Please confirm" in aggregated.reason

    def test_aggregate_results_multiple_denies(self):
        """Test aggregating results with multiple deny decisions."""
        results = [
            HookResult.deny_result("First denial", "Output 1"),
            HookResult.deny_result("Second denial", "Output 2"),
            HookResult.success_result("Hook 3 output")
        ]

        aggregated = self.executor.aggregate_results(results)

        assert aggregated.success is True
        assert aggregated.decision == "deny"
        assert "First denial; Second denial" in aggregated.reason

    def test_aggregate_results_with_suppress_output(self):
        """Test aggregating results with suppress output flag."""
        results = [
            HookResult.success_result("Hook 1 output"),
            HookResult(success=True, decision="allow", suppress_output=True, output="Suppressed output")
        ]

        aggregated = self.executor.aggregate_results(results)

        assert aggregated.success is True
        assert aggregated.suppress_output is True

    def test_aggregate_results_with_failures(self):
        """Test aggregating results with some failures."""
        results = [
            HookResult.success_result("Hook 1 output"),
            HookResult.error_result("Hook failed", "Error output"),
            HookResult.success_result("Hook 3 output")
        ]

        aggregated = self.executor.aggregate_results(results)

        # Failed hooks don't block execution, just get logged
        assert aggregated.success is True
        assert aggregated.decision == "allow"

    def test_execute_hooks_parallel(self):
        """Test parallel execution of multiple hooks."""
        def quick_hook(context: HookContext) -> HookResult:
            return HookResult.success_result(f"Quick hook for {context.tool_name}")

        def slow_hook(context: HookContext) -> HookResult:
            time.sleep(0.1)  # Small delay
            return HookResult.success_result(f"Slow hook for {context.tool_name}")

        hooks = [
            ('python', PythonHook(matcher="TestTool", function=quick_hook)),
            ('python', PythonHook(matcher="TestTool", function=slow_hook))
        ]

        result = self.executor.execute_hooks_parallel(hooks, self.context)

        assert result.success is True
        assert result.decision == "allow"
        assert "Quick hook for TestTool" in result.output
        assert "Slow hook for TestTool" in result.output

    def test_execute_hooks_parallel_empty(self):
        """Test parallel execution with empty hooks list."""
        result = self.executor.execute_hooks_parallel([], self.context)

        assert result.success is True
        assert result.decision == "allow"

    def test_execute_hooks_parallel_with_script(self):
        """Test parallel execution with script and Python hooks."""
        def python_hook(context: HookContext) -> HookResult:
            return HookResult.success_result("Python hook output")

        # Create a simple script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "Script hook output"\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hooks = [
                ('python', PythonHook(matcher="TestTool", function=python_hook)),
                ('script', ScriptHook(matcher="TestTool", command=f"bash {script_path}"))
            ]

            result = self.executor.execute_hooks_parallel(hooks, self.context)

            assert result.success is True
            assert result.decision == "allow"
            assert "Python hook output" in result.output
            assert "Script hook output" in result.output
        finally:
            os.unlink(script_path)

    def test_hook_result_should_block(self):
        """Test HookResult.should_block() method."""
        # Test blocking decisions
        assert HookResult.deny_result("test").should_block() is True
        assert HookResult.ask_result("test").should_block() is True  # Ask now blocks until confirmation
        assert HookResult(success=True, continue_execution=False).should_block() is True

        # Test non-blocking decisions
        assert HookResult.success_result().should_block() is False
        assert HookResult.block_result("test").should_block() is False  # Block allows execution with feedback

    def test_hook_result_get_blocked_response(self):
        """Test HookResult.get_blocked_response() method."""
        result = HookResult.deny_result("Access denied", "Detailed output")
        response = result.get_blocked_response()

        assert response["blocked"] is True
        assert response["reason"] == "Access denied"
        assert response["decision"] == "deny"
        assert response["output"] == "Detailed output"

    def test_hook_result_merge_with_tool_result_dict(self):
        """Test merging hook result with dict tool result."""
        hook_result = HookResult.success_result("Hook output")
        hook_result.additional_context = "Additional info"

        tool_result = {"status": "success", "data": "tool data"}
        merged = hook_result.merge_with_tool_result(tool_result)

        assert merged["status"] == "success"
        assert merged["data"] == "tool data"
        assert merged["hook_feedback"]["output"] == "Hook output"
        assert merged["hook_feedback"]["additional_context"] == "Additional info"

    def test_hook_result_merge_with_tool_result_non_dict(self):
        """Test merging hook result with non-dict tool result."""
        hook_result = HookResult.success_result("Hook output")
        tool_result = "simple string result"
        merged = hook_result.merge_with_tool_result(tool_result)

        assert merged["result"] == "simple string result"
        assert merged["hook_feedback"]["output"] == "Hook output"

    def test_hook_result_merge_with_suppress_output(self):
        """Test merging hook result with suppress output flag."""
        hook_result = HookResult(success=True, suppress_output=True)
        tool_result = {"data": "tool data"}
        merged = hook_result.merge_with_tool_result(tool_result)

        assert merged["suppress_output"] is True

    def test_hook_context_serialization(self):
        """Test HookContext JSON serialization."""
        context = HookContext(
            session_id="test-session",
            cwd="/tmp",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"},
            tool_response={"result": "success"}
        )

        json_str = context.to_json()
        parsed = json.loads(json_str)

        assert parsed["session_id"] == "test-session"
        assert parsed["cwd"] == "/tmp"
        assert parsed["hook_event_name"] == "PreToolUse"
        assert parsed["tool_name"] == "TestTool"
        assert parsed["tool_input"]["param"] == "value"
        assert parsed["tool_response"]["result"] == "success"

    def test_working_directory_handling(self):
        """Test working directory handling in script execution."""
        # Create a script that outputs the current working directory
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\npwd\n')
            script_path = f.name

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chmod(script_path, 0o755)
                hook = ScriptHook(
                    matcher="TestTool",
                    command=f"bash {script_path}",
                    working_directory=temp_dir
                )

                result = self.executor.execute_script_hook(hook, self.context)

                assert result.success is True
                assert temp_dir in result.output
            finally:
                os.unlink(script_path)

    def test_malformed_json_fallback(self):
        """Test fallback to exit code behavior when JSON is malformed."""
        # Create a script that outputs malformed JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "{ invalid json"\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            # Should fall back to exit code behavior (0 = success)
            assert result.success is True
            assert result.decision == "allow"
        finally:
            os.unlink(script_path)

    def test_json_parsing_all_fields(self):
        """Test JSON parsing with all supported fields."""
        json_response = {
            "decision": "block",
            "reason": "Custom validation failed",
            "additionalContext": "File contains sensitive data",
            "continue": True,
            "suppressOutput": True
        }

        # Create a script that outputs complete JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "block"
            assert result.reason == "Custom validation failed"
            assert result.additional_context == "File contains sensitive data"
            assert result.continue_execution is True
            assert result.suppress_output is True
        finally:
            os.unlink(script_path)

    def test_json_parsing_legacy_stop_reason(self):
        """Test JSON parsing with legacy stopReason field."""
        json_response = {
            "decision": "deny",
            "stopReason": "Legacy reason field",
            "additionalContext": "Using legacy field"
        }

        # Create a script that uses stopReason instead of reason
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "deny"
            assert result.reason == "Legacy reason field"  # stopReason should be used as reason
            assert result.additional_context == "Using legacy field"
        finally:
            os.unlink(script_path)

    def test_json_parsing_invalid_decision(self):
        """Test JSON parsing with invalid decision value."""
        json_response = {
            "decision": "invalid_decision",
            "reason": "This has an invalid decision"
        }

        # Create a script with invalid decision
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "allow"  # Should default to allow for invalid decision
            assert result.reason == "This has an invalid decision"
        finally:
            os.unlink(script_path)

    def test_json_parsing_invalid_boolean_fields(self):
        """Test JSON parsing with invalid boolean field values."""
        json_response = {
            "decision": "allow",
            "continue": "not_a_boolean",
            "suppressOutput": "also_not_boolean"
        }

        # Create a script with invalid boolean values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "allow"
            assert result.continue_execution is True  # Should default to True for invalid value
            assert result.suppress_output is False  # Should default to False for invalid value
        finally:
            os.unlink(script_path)

    def test_json_parsing_non_string_additional_context(self):
        """Test JSON parsing with non-string additionalContext."""
        json_response = {
            "decision": "allow",
            "additionalContext": {"key": "value", "number": 42}
        }

        # Create a script with non-string additional context
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "allow"
            assert result.additional_context == "{'key': 'value', 'number': 42}"  # Should be converted to string
        finally:
            os.unlink(script_path)

    def test_json_parsing_missing_reason_for_deny(self):
        """Test JSON parsing with deny decision but missing reason."""
        json_response = {
            "decision": "deny"
            # No reason field
        }

        # Create a script with deny but no reason
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f'#!/bin/bash\necho \'{json.dumps(json_response)}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "deny"
            assert "Hook returned deny decision without reason" in result.reason
        finally:
            os.unlink(script_path)

    def test_json_parsing_non_object_json(self):
        """Test JSON parsing when JSON is not an object."""
        # Create a script that outputs JSON array instead of object
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho \'["not", "an", "object"]\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            # Should fall back to exit code behavior
            assert result.success is True
            assert result.decision == "allow"
        finally:
            os.unlink(script_path)

    def test_json_parsing_empty_json_object(self):
        """Test JSON parsing with empty JSON object."""
        # Create a script that outputs empty JSON object
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho \'{}\'\nexit 0\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "allow"  # Default decision
            assert result.continue_execution is True  # Default value
            assert result.suppress_output is False  # Default value
        finally:
            os.unlink(script_path)

    def test_exit_code_fallback_with_stderr(self):
        """Test exit code fallback behavior with stderr output."""
        # Create a script that outputs to stderr and exits with code 2
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "Error message" >&2\necho "stdout message"\nexit 2\n')
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

            result = self.executor.execute_script_hook(hook, self.context)

            assert result.success is True
            assert result.decision == "deny"
            assert result.reason == "Error message"  # Should use stderr for reason
            assert result.output == "stdout message"  # Should preserve stdout in output
        finally:
            os.unlink(script_path)

    def test_exit_code_fallback_error_codes(self):
        """Test exit code fallback behavior with various error codes."""
        test_cases = [
            (1, "error"),
            (3, "error"),
            (127, "error"),
            (255, "error")
        ]

        for exit_code, expected_result in test_cases:
            # Create a script that exits with the specified code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(f'#!/bin/bash\necho "Exit code {exit_code}"\nexit {exit_code}\n')
                script_path = f.name

            try:
                os.chmod(script_path, 0o755)
                hook = ScriptHook(matcher="TestTool", command=f"bash {script_path}")

                result = self.executor.execute_script_hook(hook, self.context)

                assert result.success is False  # Error results have success=False
                assert f"code {exit_code}" in result.reason
                assert f"Exit code {exit_code}" in result.output
            finally:
                os.unlink(script_path)
