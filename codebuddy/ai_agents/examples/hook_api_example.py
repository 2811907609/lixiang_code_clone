#!/usr/bin/env python3
"""Example usage of the programmatic hook registration API."""

from ai_agents.core.hooks import (
    HookEvent, HookContext, HookResult,
    register_hook, register_pre_tool_hook, register_post_tool_hook,
    pre_tool_hook, post_tool_hook,
    list_registered_hooks, get_hook_statistics, clear_registered_hooks,
    HookManager
)


def example_validation_hook(context: HookContext) -> HookResult:
    """Example hook that validates file operations."""
    print(f"🔍 Validating tool: {context.tool_name}")

    # Check if this is a dangerous file operation
    if "delete" in context.tool_input.get("operation", "").lower():
        return HookResult.ask_result(
            f"Are you sure you want to delete files with {context.tool_name}?",
            output="File deletion requires confirmation"
        )

    # Allow other operations
    return HookResult.success_result(output="Operation validated")


def example_logging_hook(context: HookContext) -> HookResult:
    """Example hook that logs tool usage."""
    print(f"📝 Tool executed: {context.tool_name}")
    if context.tool_response:
        print(f"   Response: {str(context.tool_response)[:100]}...")

    return HookResult.success_result()


@pre_tool_hook("File*")
def decorated_file_hook(context: HookContext) -> HookResult:
    """Example decorator-based hook for file operations."""
    print(f"🗂️  File operation detected: {context.tool_name}")
    return HookResult.success_result()


@post_tool_hook("*")
def decorated_audit_hook(context: HookContext) -> HookResult:
    """Example decorator-based audit hook."""
    print(f"✅ Audit: {context.tool_name} completed successfully")
    return HookResult.success_result()


def main():
    """Demonstrate the programmatic hook registration API."""
    print("🚀 Programmatic Hook Registration API Example\n")

    # Clear any existing hooks
    clear_registered_hooks()

    # Example 1: Register hooks using functions
    print("1. Registering hooks using functions...")
    register_pre_tool_hook("*delete*", example_validation_hook)
    register_post_tool_hook("*", example_logging_hook)

    # Example 2: Hooks are automatically registered via decorators
    print("2. Hooks registered via decorators are already active")

    # Example 3: List registered hooks
    print("\n3. Listing registered hooks...")
    hooks = list_registered_hooks()
    for event, hook_list in hooks.items():
        if hook_list:
            print(f"   {event}: {len(hook_list)} hooks")
            for hook_info in hook_list:
                print(f"     - {hook_info['function_name']} (matcher: {hook_info['matcher']})")

    # Example 4: Get statistics
    print("\n4. Hook system statistics...")
    stats = get_hook_statistics()
    print(f"   Total hooks: {stats['hook_counts']['total']}")
    print(f"   Python hooks: {stats['hook_counts']['python_hooks']}")
    print(f"   Tracked registrations: {stats['api_statistics']['total_tracked_hooks']}")

    # Example 5: Simulate hook execution
    print("\n5. Simulating hook execution...")
    hook_manager = HookManager.get_instance()

    # Simulate a file deletion operation
    print("   Simulating file deletion...")
    result = hook_manager.trigger_hooks(
        HookEvent.PRE_TOOL_USE,
        "file_delete_tool",
        {"operation": "delete", "files": ["temp.txt"]}
    )
    print(f"   Hook result: decision={result.decision}, reason={result.reason}")

    # Simulate a regular file operation
    print("   Simulating file read...")
    result = hook_manager.trigger_hooks(
        HookEvent.PRE_TOOL_USE,
        "FileReader",
        {"operation": "read", "file": "data.txt"}
    )
    print(f"   Hook result: decision={result.decision}")

    # Simulate post-tool execution
    print("   Simulating post-tool execution...")
    result = hook_manager.trigger_hooks(
        HookEvent.POST_TOOL_USE,
        "FileReader",
        {"operation": "read"},
        {"status": "success", "data": "file content"}
    )
    print(f"   Hook result: decision={result.decision}")

    # Example 6: Advanced hook with custom logic
    print("\n6. Registering advanced hook with custom logic...")

    def advanced_security_hook(context: HookContext) -> HookResult:
        """Advanced hook with security checks."""
        tool_name = context.tool_name.lower()

        # Block potentially dangerous tools
        dangerous_tools = ["system", "exec", "shell"]
        if any(dangerous in tool_name for dangerous in dangerous_tools):
            return HookResult.deny_result(
                f"Tool {context.tool_name} is blocked by security policy",
                output="Security violation detected"
            )

        # Require confirmation for network tools
        network_tools = ["http", "request", "download", "upload"]
        if any(network in tool_name for network in network_tools):
            return HookResult.ask_result(
                f"Network operation with {context.tool_name} requires approval",
                output="Network access requires confirmation"
            )

        return HookResult.success_result()

    register_hook(HookEvent.PRE_TOOL_USE, "*", advanced_security_hook)

    # Test the advanced hook
    print("   Testing security hook with dangerous tool...")
    result = hook_manager.trigger_hooks(
        HookEvent.PRE_TOOL_USE,
        "system_exec",
        {"command": "rm -rf /"}
    )
    print(f"   Security result: decision={result.decision}, reason={result.reason}")

    print("\n✅ Example completed! The programmatic hook registration API provides:")
    print("   • Simple function-based registration")
    print("   • Convenient decorator-based registration")
    print("   • Flexible hook management (list, unregister, clear)")
    print("   • Duplicate prevention and validation")
    print("   • Integration with the existing hook system")
    print("   • Comprehensive statistics and monitoring")

    # Clean up
    clear_registered_hooks()


if __name__ == "__main__":
    main()
