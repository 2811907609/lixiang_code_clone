"""Tests for hook system data models and types."""

import json
import pytest
from ai_agents.core.hooks.types import (
    HookEvent,
    HookContext,
    HookResult,
    ScriptHook,
    PythonHook,
)


class TestHookEvent:
    """Test HookEvent enum."""

    def test_hook_event_values(self):
        """Test that HookEvent has correct values."""
        assert HookEvent.PRE_TOOL_USE.value == "PreToolUse"
        assert HookEvent.POST_TOOL_USE.value == "PostToolUse"
        assert HookEvent.POST_TOOL_ERROR.value == "PostToolError"
        assert HookEvent.USER_PROMPT_SUBMIT.value == "UserPromptSubmit"


class TestHookContext:
    """Test HookContext dataclass."""

    def test_hook_context_creation(self):
        """Test creating HookContext."""
        context = HookContext(
            session_id="test-session",
            cwd="/test/dir",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"},
            tool_response={"result": "success"}
        )

        assert context.session_id == "test-session"
        assert context.cwd == "/test/dir"
        assert context.hook_event_name == "PreToolUse"
        assert context.tool_name == "TestTool"
        assert context.tool_input == {"param": "value"}
        assert context.tool_response == {"result": "success"}

    def test_hook_context_to_json(self):
        """Test HookContext JSON serialization."""
        context = HookContext(
            session_id="test-session",
            cwd="/test/dir",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"},
            tool_response={"result": "success"}
        )

        json_str = context.to_json()
        parsed = json.loads(json_str)

        assert parsed["session_id"] == "test-session"
        assert parsed["cwd"] == "/test/dir"
        assert parsed["hook_event_name"] == "PreToolUse"
        assert parsed["tool_name"] == "TestTool"
        assert parsed["tool_input"] == {"param": "value"}
        assert parsed["tool_response"] == {"result": "success"}

    def test_hook_context_optional_response(self):
        """Test HookContext with optional tool_response."""
        context = HookContext(
            session_id="test-session",
            cwd="/test/dir",
            hook_event_name="PreToolUse",
            tool_name="TestTool",
            tool_input={"param": "value"}
        )

        assert context.tool_response is None

        json_str = context.to_json()
        parsed = json.loads(json_str)
        assert parsed["tool_response"] is None


class TestHookResult:
    """Test HookResult dataclass."""

    def test_hook_result_creation(self):
        """Test creating HookResult."""
        result = HookResult(
            success=True,
            decision="allow",
            reason="Test reason",
            additional_context="Test context",
            suppress_output=False,
            continue_execution=True,
            output="Test output"
        )

        assert result.success is True
        assert result.decision == "allow"
        assert result.reason == "Test reason"
        assert result.additional_context == "Test context"
        assert result.suppress_output is False
        assert result.continue_execution is True
        assert result.output == "Test output"

    def test_should_block_deny(self):
        """Test should_block returns True for deny decision."""
        result = HookResult(success=True, decision="deny")
        assert result.should_block() is True

    def test_should_block_ask(self):
        """Test should_block returns True for ask decision (requires confirmation)."""
        result = HookResult(success=True, decision="ask")
        assert result.should_block() is True

    def test_should_block_continue_false(self):
        """Test should_block returns True when continue_execution is False."""
        result = HookResult(success=True, continue_execution=False)
        assert result.should_block() is True

    def test_should_block_failed_hook_no_allow(self):
        """Test should_block returns True for failed hook without explicit allow."""
        result = HookResult(success=False, decision=None)
        assert result.should_block() is True

    def test_should_block_failed_hook_with_allow(self):
        """Test should_block returns False for failed hook with explicit allow."""
        result = HookResult(success=False, decision="allow")
        assert result.should_block() is False

    def test_should_block_allow(self):
        """Test should_block returns False for allow decision."""
        result = HookResult(success=True, decision="allow")
        assert result.should_block() is False

    def test_should_block_block(self):
        """Test should_block returns False for block decision (allows execution with feedback)."""
        result = HookResult(success=True, decision="block")
        assert result.should_block() is False

    def test_should_block_none_decision(self):
        """Test should_block returns False for None decision with continue_execution=True."""
        result = HookResult(success=True, decision=None, continue_execution=True)
        assert result.should_block() is False

    def test_get_blocked_response_deny(self):
        """Test get_blocked_response method for deny decision."""
        result = HookResult(
            success=True,
            decision="deny",
            reason="Access denied",
            output="Test output",
            additional_context="Test context"
        )

        response = result.get_blocked_response()

        assert response["blocked"] is True
        assert response["reason"] == "Access denied"
        assert response["decision"] == "deny"
        assert response["type"] == "denied"
        assert response["message"] == "Tool execution was denied: Access denied"
        assert response["output"] == "Test output"
        assert response["additional_context"] == "Test context"

    def test_get_blocked_response_ask(self):
        """Test get_blocked_response method for ask decision."""
        result = HookResult(
            success=True,
            decision="ask",
            reason="Confirm deletion",
            output="Confirmation needed"
        )

        response = result.get_blocked_response()

        assert response["blocked"] is True
        assert response["reason"] == "Confirm deletion"
        assert response["decision"] == "ask"
        assert response["type"] == "confirmation_required"
        assert response["message"] == "Confirm tool execution: Confirm deletion"

    def test_get_blocked_response_hook_error(self):
        """Test get_blocked_response method for failed hook."""
        result = HookResult(
            success=False,
            reason="Script timeout",
            output="Error details"
        )

        response = result.get_blocked_response()

        assert response["blocked"] is True
        assert response["reason"] == "Script timeout"
        assert response["type"] == "hook_error"
        assert response["message"] == "Hook execution failed: Script timeout"

    def test_get_blocked_response_default_reasons(self):
        """Test get_blocked_response with default reasons for different types."""
        # Test deny with no reason
        result = HookResult(success=True, decision="deny")
        response = result.get_blocked_response()
        assert response["reason"] == "Tool execution denied by hook"
        assert response["message"] == "Tool execution was denied: No reason provided"

        # Test ask with no reason
        result = HookResult(success=True, decision="ask")
        response = result.get_blocked_response()
        assert response["reason"] == "User confirmation required"
        assert response["message"] == "Confirm tool execution: Hook requires user approval"

        # Test failed hook with no reason
        result = HookResult(success=False)
        response = result.get_blocked_response()
        assert response["reason"] == "Hook execution failed"
        assert response["message"] == "Hook execution failed: Unknown error"

    def test_merge_with_tool_result_dict(self):
        """Test merging hook result with dict tool result."""
        result = HookResult(
            success=True,
            decision="allow",
            reason="Test reason",
            additional_context="Test context",
            output="Test output"
        )

        tool_result = {"data": "test", "status": "success"}
        merged = result.merge_with_tool_result(tool_result)

        assert merged["data"] == "test"
        assert merged["status"] == "success"
        assert merged["hook_feedback"]["decision"] == "allow"
        assert merged["hook_feedback"]["reason"] == "Test reason"
        assert merged["hook_feedback"]["additional_context"] == "Test context"
        assert merged["hook_feedback"]["output"] == "Test output"
        assert merged["hook_feedback"]["success"] is True
        assert merged["hook_processed"] is True

    def test_merge_with_tool_result_non_dict(self):
        """Test merging hook result with non-dict tool result."""
        result = HookResult(
            success=True,
            decision="allow",
            reason="Test reason"
        )

        tool_result = "simple string result"
        merged = result.merge_with_tool_result(tool_result)

        assert merged["result"] == "simple string result"
        assert merged["hook_feedback"]["decision"] == "allow"
        assert merged["hook_feedback"]["reason"] == "Test reason"
        assert merged["hook_processed"] is True

    def test_merge_with_block_decision(self):
        """Test merging with block decision provides feedback."""
        result = HookResult(
            success=True,
            decision="block",
            reason="Needs review",
            output="Block output"
        )

        tool_result = {"data": "test"}
        merged = result.merge_with_tool_result(tool_result)

        assert merged["hook_blocked"] is True
        assert merged["hook_message"] == "Needs review"
        assert merged["hook_feedback"]["decision"] == "block"

    def test_merge_with_allow_and_additional_context(self):
        """Test merging with allow decision and additional context injection."""
        result = HookResult(
            success=True,
            decision="allow",
            additional_context="Important context for agent"
        )

        tool_result = {"data": "test"}
        merged = result.merge_with_tool_result(tool_result)

        assert merged["agent_context_injection"] == "Important context for agent"
        assert merged["hook_feedback"]["additional_context"] == "Important context for agent"

    def test_merge_with_suppress_output_dict(self):
        """Test merging with suppress_output flag for dict result."""
        result = HookResult(
            success=True,
            suppress_output=True,
            output="Suppressed output"
        )

        tool_result = {"data": "test", "status": "success"}
        merged = result.merge_with_tool_result(tool_result)

        assert merged["suppress_output"] is True
        assert merged["original_tool_output"] == {"data": "test", "status": "success"}
        assert merged["result"] == "Suppressed output"
        assert merged["hook_feedback"]["success"] is True

    def test_merge_with_suppress_output_non_dict(self):
        """Test merging with suppress_output flag for non-dict result."""
        result = HookResult(
            success=True,
            suppress_output=True,
            output="Suppressed output"
        )

        tool_result = "original result"
        merged = result.merge_with_tool_result(tool_result)

        assert merged["suppress_output"] is True
        assert merged["original_result"] == "original result"
        assert merged["result"] == "Suppressed output"
        assert merged["hook_feedback"]["success"] is True

    def test_merge_without_additional_context(self):
        """Test merging without additional_context doesn't include it in feedback."""
        result = HookResult(
            success=True,
            decision="allow",
            reason="Test reason"
        )

        tool_result = {"data": "test"}
        merged = result.merge_with_tool_result(tool_result)

        assert "additional_context" not in merged["hook_feedback"]

    def test_success_result_factory(self):
        """Test success_result factory method."""
        result = HookResult.success_result("Test output")

        assert result.success is True
        assert result.decision == "allow"
        assert result.continue_execution is True
        assert result.output == "Test output"

    def test_deny_result_factory(self):
        """Test deny_result factory method."""
        result = HookResult.deny_result("Access denied", "Error output")

        assert result.success is True
        assert result.decision == "deny"
        assert result.reason == "Access denied"
        assert result.continue_execution is False
        assert result.output == "Error output"

    def test_block_result_factory(self):
        """Test block_result factory method."""
        result = HookResult.block_result("Blocked for review", "Block output")

        assert result.success is True
        assert result.decision == "block"
        assert result.reason == "Blocked for review"
        assert result.continue_execution is True
        assert result.output == "Block output"

    def test_ask_result_factory(self):
        """Test ask_result factory method."""
        result = HookResult.ask_result("Confirm action", "Ask output")

        assert result.success is True
        assert result.decision == "ask"
        assert result.reason == "Confirm action"
        assert result.continue_execution is True
        assert result.output == "Ask output"

    def test_error_result_factory(self):
        """Test error_result factory method."""
        result = HookResult.error_result("Hook failed", "Error output")

        assert result.success is False
        assert result.reason == "Hook failed"
        assert result.continue_execution is True
        assert result.output == "Error output"

    def test_aggregate_results_empty_list(self):
        """Test aggregate_results with empty list returns success."""
        result = HookResult.aggregate_results([])

        assert result.success is True
        assert result.decision == "allow"
        assert result.continue_execution is True

    def test_aggregate_results_all_failed(self):
        """Test aggregate_results when all hooks failed."""
        failed_results = [
            HookResult.error_result("Hook 1 failed"),
            HookResult.error_result("Hook 2 failed")
        ]

        result = HookResult.aggregate_results(failed_results)

        assert result.success is False
        assert "All hooks failed" in result.reason
        assert "Hook 1 failed" in result.reason
        assert "Hook 2 failed" in result.reason

    def test_aggregate_results_deny_precedence(self):
        """Test aggregate_results gives deny highest precedence."""
        results = [
            HookResult.success_result(),
            HookResult.ask_result("Need confirmation"),
            HookResult.deny_result("Access denied"),
            HookResult.block_result("Blocked for review")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "deny"
        assert "Denied by hooks" in result.reason
        assert "Access denied" in result.reason

    def test_aggregate_results_ask_precedence(self):
        """Test aggregate_results gives ask second highest precedence."""
        results = [
            HookResult.success_result(),
            HookResult.ask_result("Need confirmation"),
            HookResult.block_result("Blocked for review")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "ask"
        assert "Confirmation required" in result.reason
        assert "Need confirmation" in result.reason

    def test_aggregate_results_block_precedence(self):
        """Test aggregate_results gives block third highest precedence."""
        results = [
            HookResult.success_result(),
            HookResult.block_result("Blocked for review"),
            HookResult(success=True, decision="allow", additional_context="Some context")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "block"
        assert "Blocked with feedback" in result.reason
        assert "Blocked for review" in result.reason

    def test_aggregate_results_multiple_deny(self):
        """Test aggregate_results combines multiple deny reasons."""
        results = [
            HookResult.deny_result("Access denied"),
            HookResult.deny_result("Permission error")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "deny"
        assert "Access denied" in result.reason
        assert "Permission error" in result.reason

    def test_aggregate_results_multiple_ask(self):
        """Test aggregate_results combines multiple ask reasons."""
        results = [
            HookResult.ask_result("Confirm deletion"),
            HookResult.ask_result("Confirm overwrite")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "ask"
        assert "Confirm deletion" in result.reason
        assert "Confirm overwrite" in result.reason

    def test_aggregate_results_multiple_block(self):
        """Test aggregate_results combines multiple block reasons and outputs."""
        results = [
            HookResult.block_result("Review needed", "Block output 1"),
            HookResult.block_result("Security check", "Block output 2")
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "block"
        assert "Review needed" in result.reason
        assert "Security check" in result.reason
        assert "Block output 1" in result.output
        assert "Block output 2" in result.output

    def test_aggregate_results_combine_additional_context(self):
        """Test aggregate_results combines additional context from all results."""
        results = [
            HookResult(success=True, decision="allow", additional_context="Context 1"),
            HookResult(success=True, decision="allow", additional_context="Context 2"),
            HookResult(success=True, decision="allow")  # No additional context
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "allow"
        assert "Context 1" in result.additional_context
        assert "Context 2" in result.additional_context

    def test_aggregate_results_combine_outputs(self):
        """Test aggregate_results combines outputs from all results."""
        results = [
            HookResult(success=True, decision="allow", output="Output 1"),
            HookResult(success=True, decision="allow", output="Output 2"),
            HookResult(success=True, decision="allow")  # No output
        ]

        result = HookResult.aggregate_results(results)

        assert result.decision == "allow"
        assert "Output 1" in result.output
        assert "Output 2" in result.output

    def test_aggregate_results_suppress_output_any(self):
        """Test aggregate_results sets suppress_output if any result has it."""
        results = [
            HookResult(success=True, decision="allow", suppress_output=False),
            HookResult(success=True, decision="allow", suppress_output=True),
            HookResult(success=True, decision="allow", suppress_output=False)
        ]

        result = HookResult.aggregate_results(results)

        assert result.suppress_output is True

    def test_aggregate_results_mixed_success_failure(self):
        """Test aggregate_results handles mix of successful and failed hooks."""
        results = [
            HookResult.error_result("Hook 1 failed"),
            HookResult.success_result("Success output"),
            HookResult.ask_result("Need confirmation")
        ]

        result = HookResult.aggregate_results(results)

        # Should prioritize successful hooks' decisions
        assert result.decision == "ask"
        assert "Need confirmation" in result.reason


class TestScriptHook:
    """Test ScriptHook dataclass."""

    def test_script_hook_creation(self):
        """Test creating ScriptHook."""
        hook = ScriptHook(
            matcher="TestTool",
            command="echo test",
            timeout=30,
            working_directory="/test/dir"
        )

        assert hook.matcher == "TestTool"
        assert hook.command == "echo test"
        assert hook.timeout == 30
        assert hook.working_directory == "/test/dir"

    def test_script_hook_defaults(self):
        """Test ScriptHook default values."""
        hook = ScriptHook(
            matcher="TestTool",
            command="echo test"
        )

        assert hook.timeout == 60
        assert hook.working_directory is None

    def test_script_hook_validation_empty_matcher(self):
        """Test ScriptHook validation for empty matcher."""
        with pytest.raises(ValueError, match="Script hook matcher cannot be empty"):
            ScriptHook(matcher="", command="echo test")

    def test_script_hook_validation_empty_command(self):
        """Test ScriptHook validation for empty command."""
        with pytest.raises(ValueError, match="Script hook command cannot be empty"):
            ScriptHook(matcher="TestTool", command="")

    def test_script_hook_validation_negative_timeout(self):
        """Test ScriptHook validation for negative timeout."""
        with pytest.raises(ValueError, match="Script hook timeout must be positive"):
            ScriptHook(matcher="TestTool", command="echo test", timeout=-1)

    def test_script_hook_validation_zero_timeout(self):
        """Test ScriptHook validation for zero timeout."""
        with pytest.raises(ValueError, match="Script hook timeout must be positive"):
            ScriptHook(matcher="TestTool", command="echo test", timeout=0)


class TestPythonHook:
    """Test PythonHook dataclass."""

    def test_python_hook_creation(self):
        """Test creating PythonHook."""
        def test_function(context):
            return HookResult.success_result()

        hook = PythonHook(
            matcher="TestTool",
            function=test_function,
            timeout=30
        )

        assert hook.matcher == "TestTool"
        assert hook.function == test_function
        assert hook.timeout == 30

    def test_python_hook_defaults(self):
        """Test PythonHook default values."""
        def test_function(context):
            return HookResult.success_result()

        hook = PythonHook(
            matcher="TestTool",
            function=test_function
        )

        assert hook.timeout == 60

    def test_python_hook_validation_empty_matcher(self):
        """Test PythonHook validation for empty matcher."""
        def test_function(context):
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Python hook matcher cannot be empty"):
            PythonHook(matcher="", function=test_function)

    def test_python_hook_validation_non_callable(self):
        """Test PythonHook validation for non-callable function."""
        with pytest.raises(ValueError, match="Python hook function must be callable"):
            PythonHook(matcher="TestTool", function="not a function")

    def test_python_hook_validation_negative_timeout(self):
        """Test PythonHook validation for negative timeout."""
        def test_function(context):
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Python hook timeout must be positive"):
            PythonHook(matcher="TestTool", function=test_function, timeout=-1)

    def test_python_hook_validation_zero_timeout(self):
        """Test PythonHook validation for zero timeout."""
        def test_function(context):
            return HookResult.success_result()

        with pytest.raises(ValueError, match="Python hook timeout must be positive"):
            PythonHook(matcher="TestTool", function=test_function, timeout=0)
