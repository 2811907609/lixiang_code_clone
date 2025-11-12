"""Core data models and types for the hook system."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional
import json


class HookEvent(Enum):
    """Events that can trigger hooks."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_ERROR = "PostToolError"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"


@dataclass
class HookContext:
    """Context information passed to hooks during execution."""
    session_id: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_response: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert context to JSON string for passing to external scripts."""
        return json.dumps({
            "session_id": self.session_id,
            "cwd": self.cwd,
            "hook_event_name": self.hook_event_name,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_response": self.tool_response,
        })


@dataclass
class HookResult:
    """Result returned by hook execution."""
    success: bool
    decision: Optional[str] = None  # "allow", "deny", "ask", "block"
    reason: Optional[str] = None
    additional_context: Optional[str] = None
    suppress_output: bool = False
    continue_execution: bool = True
    output: Optional[str] = None

    def should_block(self) -> bool:
        """Check if this hook result should block tool execution.

        Returns True if:
        - Decision is "deny" (prevents tool execution entirely)
        - Decision is "ask" (requires user confirmation before proceeding)
        - continue_execution is False
        - Hook execution failed and decision is not explicitly "allow"

        Returns False if:
        - Decision is "allow" (explicitly allows execution)
        - Decision is "block" (allows execution but provides feedback)
        - Decision is None and continue_execution is True (default allow)
        """
        # If hook failed and no explicit allow decision, block execution
        if not self.success and self.decision != "allow":
            return True

        # Explicit deny always blocks
        if self.decision == "deny":
            return True

        # Ask decision blocks until user confirmation
        if self.decision == "ask":
            return True

        # Check continue_execution flag
        if not self.continue_execution:
            return True

        # All other cases (allow, block, None) don't block execution
        return False

    def get_blocked_response(self) -> Dict[str, Any]:
        """Get appropriate response when tool execution is blocked.

        Returns different response formats based on the decision type:
        - "deny": Tool execution prevented with reason
        - "ask": User confirmation required
        - Failed hook: Error information
        """
        base_response = {
            "blocked": True,
            "decision": self.decision,
            "output": self.output,
            "additional_context": self.additional_context,
        }

        if self.decision == "deny":
            base_response.update({
                "reason": self.reason or "Tool execution denied by hook",
                "type": "denied",
                "message": f"Tool execution was denied: {self.reason or 'No reason provided'}"
            })
        elif self.decision == "ask":
            base_response.update({
                "reason": self.reason or "User confirmation required",
                "type": "confirmation_required",
                "message": f"Confirm tool execution: {self.reason or 'Hook requires user approval'}"
            })
        elif not self.success:
            base_response.update({
                "reason": self.reason or "Hook execution failed",
                "type": "hook_error",
                "message": f"Hook execution failed: {self.reason or 'Unknown error'}"
            })
        else:
            base_response.update({
                "reason": self.reason or "Tool execution blocked by hook",
                "type": "blocked",
                "message": f"Tool execution blocked: {self.reason or 'No reason provided'}"
            })

        return base_response

    def merge_with_tool_result(self, tool_result: Any) -> Any:
        """Merge hook feedback with tool result.

        Combines hook decisions and context with the original tool result.
        Handles different decision types appropriately:
        - "allow": Passes through tool result with minimal hook info
        - "block": Adds hook feedback to tool result
        - "deny"/"ask": Should not reach here (blocked earlier)

        Also handles additional_context injection into agent context.
        """
        # Create hook feedback object
        hook_feedback = {
            "decision": self.decision,
            "reason": self.reason,
            "output": self.output,
            "success": self.success,
        }

        # Only include additional_context if it exists
        if self.additional_context:
            hook_feedback["additional_context"] = self.additional_context

        if not isinstance(tool_result, dict):
            # If tool result is not a dict, wrap it
            merged_result = {
                "result": tool_result,
                "hook_feedback": hook_feedback
            }
        else:
            # If tool result is a dict, add hook feedback
            merged_result = tool_result.copy()
            merged_result["hook_feedback"] = hook_feedback

        # Handle different decision types
        if self.decision == "block":
            # Block decision provides feedback but allows execution
            merged_result["hook_blocked"] = True
            merged_result["hook_message"] = self.reason or "Hook provided blocking feedback"

        elif self.decision == "allow" and self.additional_context:
            # Allow with additional context - inject into agent context
            merged_result["agent_context_injection"] = self.additional_context

        # Handle output suppression
        if self.suppress_output:
            merged_result["suppress_output"] = True
            # If suppressing output, replace or modify the main result
            if "result" in merged_result:
                merged_result["original_result"] = merged_result["result"]
                merged_result["result"] = self.output or "Output suppressed by hook"
            else:
                # For dict tool results, preserve original data and add suppressed result
                merged_result["original_tool_output"] = tool_result
                merged_result["result"] = self.output or "Output suppressed by hook"

        # Add hook execution metadata
        merged_result["hook_processed"] = True

        return merged_result

    @classmethod
    def success_result(cls, output: Optional[str] = None) -> "HookResult":
        """Create a successful hook result."""
        return cls(
            success=True,
            decision="allow",
            continue_execution=True,
            output=output,
        )

    @classmethod
    def deny_result(cls, reason: str, output: Optional[str] = None) -> "HookResult":
        """Create a hook result that denies tool execution."""
        return cls(
            success=True,
            decision="deny",
            reason=reason,
            continue_execution=False,
            output=output,
        )

    @classmethod
    def block_result(cls, reason: str, output: Optional[str] = None) -> "HookResult":
        """Create a hook result that blocks with feedback."""
        return cls(
            success=True,
            decision="block",
            reason=reason,
            continue_execution=True,
            output=output,
        )

    @classmethod
    def ask_result(cls, reason: str, output: Optional[str] = None) -> "HookResult":
        """Create a hook result that asks for user confirmation."""
        return cls(
            success=True,
            decision="ask",
            reason=reason,
            continue_execution=True,
            output=output,
        )

    @classmethod
    def error_result(cls, reason: str, output: Optional[str] = None) -> "HookResult":
        """Create a hook result for error conditions."""
        return cls(
            success=False,
            reason=reason,
            continue_execution=True,
            output=output,
        )

    @classmethod
    def aggregate_results(cls, results: list["HookResult"]) -> "HookResult":
        """Aggregate multiple hook results into a single result.

        Decision precedence (highest to lowest):
        1. deny - any deny blocks everything
        2. ask - any ask requires confirmation
        3. block - any block provides feedback
        4. allow - explicit allow
        5. None - default (no decision)

        Args:
            results: List of HookResult objects to aggregate

        Returns:
            Single HookResult representing the aggregate decision
        """
        if not results:
            return cls.success_result()

        # Filter out failed results for decision making, but track them
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        # If all hooks failed, return error
        if not successful_results:
            combined_reasons = "; ".join(r.reason or "Unknown error" for r in failed_results)
            return cls.error_result(f"All hooks failed: {combined_reasons}")

        # Check for deny decisions (highest precedence)
        deny_results = [r for r in successful_results if r.decision == "deny"]
        if deny_results:
            combined_reasons = "; ".join(r.reason or "Denied" for r in deny_results)
            return cls.deny_result(f"Denied by hooks: {combined_reasons}")

        # Check for ask decisions
        ask_results = [r for r in successful_results if r.decision == "ask"]
        if ask_results:
            combined_reasons = "; ".join(r.reason or "Confirmation required" for r in ask_results)
            return cls.ask_result(f"Confirmation required: {combined_reasons}")

        # Check for block decisions
        block_results = [r for r in successful_results if r.decision == "block"]
        if block_results:
            combined_reasons = "; ".join(r.reason or "Blocked" for r in block_results)
            combined_output = "; ".join(r.output for r in block_results if r.output)
            return cls.block_result(
                f"Blocked with feedback: {combined_reasons}",
                combined_output if combined_output else None
            )

        # Combine additional context from all results
        additional_contexts = [r.additional_context for r in successful_results if r.additional_context]
        combined_additional_context = "; ".join(additional_contexts) if additional_contexts else None

        # Combine outputs
        outputs = [r.output for r in successful_results if r.output]
        combined_output = "; ".join(outputs) if outputs else None

        # Check if any result wants to suppress output
        suppress_output = any(r.suppress_output for r in successful_results)

        # Default to allow with combined context
        return cls(
            success=True,
            decision="allow",
            reason="All hooks passed",
            additional_context=combined_additional_context,
            suppress_output=suppress_output,
            continue_execution=True,
            output=combined_output,
        )


@dataclass
class ScriptHook:
    """Configuration for external script hooks."""
    matcher: str
    command: str
    timeout: int = 60
    working_directory: Optional[str] = None

    def __post_init__(self):
        """Validate script hook configuration."""
        if not self.matcher:
            raise ValueError("Script hook matcher cannot be empty")
        if not self.command:
            raise ValueError("Script hook command cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Script hook timeout must be positive")


@dataclass
class PythonHook:
    """Configuration for Python function hooks."""
    matcher: str
    function: Callable[[HookContext], HookResult]
    timeout: int = 60

    def __post_init__(self):
        """Validate Python hook configuration."""
        if not self.matcher:
            raise ValueError("Python hook matcher cannot be empty")
        if not callable(self.function):
            raise ValueError("Python hook function must be callable")
        if self.timeout <= 0:
            raise ValueError("Python hook timeout must be positive")
