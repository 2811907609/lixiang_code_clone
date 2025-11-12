

import os

import arrow
import fire

import ai_agents.lib.tracing  # noqa: F401
from ai_agents.lib.smolagents import LogLevel, new_agent_logger
from ai_agents.tools.vendor_tools import (
    ensure_all_tools,
    add_tools_to_path,
)
from ai_agents.supervisor_agents.simple import (
    run_agent,
)
from ai_agents.core.runtime import runtime
from ai_agents.core.hooks import (
    HookContext, HookResult,
    register_pre_tool_hook, register_post_tool_hook
)

runtime.app = "SimpleCli"
runtime.biz_id = f"{arrow.now().format('YYYY-MM-DD_HH_mm')}"


def demo_pre_tool_hook(context: HookContext) -> HookResult:
    """Demo hook that logs tool usage before execution."""
    print(f"🔧 [PRE-HOOK] Tool: {context.tool_name}")
    print(f"   Arguments: {context.tool_input}")
    return HookResult.success_result()


def demo_post_tool_hook(context: HookContext) -> HookResult:
    """Demo hook that logs tool completion after execution."""
    print(f"✅ [POST-HOOK] Tool: {context.tool_name} completed")
    if context.tool_response:
        # Truncate long responses for readability
        response_str = str(context.tool_response)
        if len(response_str) > 100:
            response_str = response_str[:100] + "..."
        print(f"   Response: {response_str}")
    return HookResult.success_result()


def setup_demo_hooks():
    """Register demo hooks to show tool usage."""
    print("🪝 Setting up demo hooks...")

    # Register hooks for all tools to demonstrate the system
    register_pre_tool_hook("*", demo_pre_tool_hook)
    register_post_tool_hook("*", demo_post_tool_hook)

    print("   ✓ Pre-tool hook registered (logs tool name and arguments)")
    print("   ✓ Post-tool hook registered (logs tool completion)")
    print()


def run(
    task: str,
    working_dir: str=".",
):
    agent_logger = new_agent_logger(None, level=LogLevel.DEBUG)

    print("=" * 80)
    print("Simple SOP Agent with Demo Hooks")
    print("=" * 80)
    print(f"Target repo: {working_dir}")
    print(f"Current directory: {os.getcwd()}")
    print()

    # Set up demo hooks to show how they work
    setup_demo_hooks()

    try:
        result = run_agent(agent_logger, task, project_path=working_dir)
        print("\n" + "=" * 80)
        print("Issue resolution completed!")
        print("=" * 80)
        print(result)
    except KeyboardInterrupt:
        print("\n\nIssue resolution interrupted by user")
    except Exception as e:
        print(f"\nError during resolution: {e}")
        import traceback
        traceback.print_exc()


def main():
    ensure_all_tools()
    add_tools_to_path()
    fire.Fire(run)


if __name__ == "__main__":
    main()
