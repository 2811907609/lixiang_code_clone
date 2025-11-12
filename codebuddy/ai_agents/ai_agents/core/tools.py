import ast
import json
import inspect
import textwrap
import warnings
from collections.abc import Callable
from functools import wraps

from smolagents.tools import Tool, TypeHintParsingException, get_json_schema

def tool(tool_function: Callable) -> Tool:
    """
    Convert a function into an instance of a dynamically created Tool subclass.

    Args:
        tool_function (`Callable`): Function to convert into a Tool subclass.
            Should have type hints for each input and a type hint for the output.
            Should also have a docstring including the description of the function
            and an 'Args:' part where each argument is described.
    """
    tool_json_schema = get_json_schema(tool_function)["function"]
    if "return" not in tool_json_schema:
        if len(tool_json_schema["parameters"]["properties"]) == 0:
            tool_json_schema["return"] = {"type": "null"}
        else:
            raise TypeHintParsingException(
                "Tool return type not found: make sure your function has a return type hint!"
            )

    class SimpleTool(Tool):
        def __init__(self):
            self.is_initialized = True

    # Set the class attributes
    SimpleTool.name = tool_json_schema["name"]
    SimpleTool.description = tool_json_schema["description"]
    SimpleTool.inputs = tool_json_schema["parameters"]["properties"]
    SimpleTool.output_type = tool_json_schema["return"]["type"]

    @wraps(tool_function)
    def wrapped_function(*args, **kwargs):
        # Import hook system components here to avoid circular imports
        try:
            from .hooks.hook_manager import HookManager
            from .hooks.types import HookEvent
            hook_manager = HookManager.get_instance()
            hooks_enabled = True
        except ImportError:
            # Hook system not available, proceed without hooks
            hooks_enabled = False
            hook_manager = None

        tool_name = tool_json_schema["name"]

        pre_hook_executed = False
        if hooks_enabled and hook_manager:
            # Pre-execution hooks
            try:
                pre_result = hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE,
                    tool_name,
                    kwargs
                )

                # Check if hooks want to block execution
                if pre_result.should_block():
                    return pre_result.get_blocked_response()

                # Check if pre-hooks were actually executed
                if not (hasattr(pre_result, '_no_hooks_executed') and pre_result._no_hooks_executed):
                    pre_hook_executed = True

            except Exception as hook_error:
                # Log hook error but don't fail the tool execution
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Pre-execution hook error for tool {tool_name}: {hook_error}")

        # Execute original tool
        try:
            result = tool_function(*args, **kwargs)

            if hooks_enabled and hook_manager:
                # Post-execution hooks
                try:
                    post_result = hook_manager.trigger_hooks(
                        HookEvent.POST_TOOL_USE,
                        tool_name,
                        kwargs,
                        {"result": result} if result is not None else {}
                    )

                    # Check if post-hooks were actually executed
                    post_hook_executed = not (hasattr(post_result, '_no_hooks_executed') and post_result._no_hooks_executed)

                    # Merge hook feedback if any hooks were executed (pre or post)
                    if pre_hook_executed or post_hook_executed:
                        return post_result.merge_with_tool_result(result)
                    else:
                        # No hooks were actually executed, return original result
                        return result

                except Exception as hook_error:
                    # Log hook error but return original result
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Post-execution hook error for tool {tool_name}: {hook_error}")
                    # If pre-hooks were executed, we still need to indicate that
                    if pre_hook_executed:
                        # Create a simple success result to merge
                        from .hooks.types import HookResult
                        fallback_result = HookResult.success_result()
                        return fallback_result.merge_with_tool_result(result)
                    return result
            else:
                # If pre-hooks were executed but post-hooks are disabled, still merge
                if pre_hook_executed:
                    from .hooks.types import HookResult
                    fallback_result = HookResult.success_result()
                    return fallback_result.merge_with_tool_result(result)
                return result

        except Exception as tool_error:
            if hooks_enabled and hook_manager:
                # Post-error hooks
                try:
                    hook_manager.trigger_hooks(
                        HookEvent.POST_TOOL_ERROR,
                        tool_name,
                        kwargs,
                        {"error": str(tool_error), "error_type": type(tool_error).__name__}
                    )
                except Exception as hook_error:
                    # Log hook error but don't interfere with original exception
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Post-error hook error for tool {tool_name}: {hook_error}")

            # Re-raise the original tool exception
            raise tool_error

    # Bind the copied function to the forward method
    SimpleTool.forward = staticmethod(wrapped_function)

    # Get the signature parameters of the tool function
    sig = inspect.signature(tool_function)
    # - Add "self" as first parameter to tool_function signature
    new_sig = sig.replace(
        parameters=[inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)] + list(sig.parameters.values())
    )
    # - Set the signature of the forward method
    SimpleTool.forward.__signature__ = new_sig

    # Create and attach the source code of the dynamically created tool class and forward method
    # - Get the source code of tool_function
    tool_source = textwrap.dedent(inspect.getsource(tool_function))
    # - Remove the tool decorator and function definition line
    lines = tool_source.splitlines()
    tree = ast.parse(tool_source)
    #   - Find function definition
    func_node = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)), None)
    if not func_node:
        raise ValueError(
            "No function definition found in the provided source of {tool_function.__name__}. "
            "Ensure the input is a standard function."
        )
    #   - Extract decorator lines
    decorator_lines = ""
    if func_node.decorator_list:
        tool_decorators = [d for d in func_node.decorator_list if isinstance(d, ast.Name) and d.id == "tool"]
        if len(tool_decorators) > 1:
            raise ValueError(
                f"Multiple @tool decorators found on function '{func_node.name}'. Only one @tool decorator is allowed."
            )
        if len(tool_decorators) < len(func_node.decorator_list):
            warnings.warn(
                f"Function '{func_node.name}' has decorators other than @tool. "
                "This may cause issues with serialization in the remote executor. See issue #1626."
            )
        decorator_start = tool_decorators[0].end_lineno if tool_decorators else 0
        decorator_end = func_node.decorator_list[-1].end_lineno
        decorator_lines = "\n".join(lines[decorator_start:decorator_end])
    #   - Extract tool source body
    body_start = func_node.body[0].lineno - 1  # AST lineno starts at 1
    tool_source_body = "\n".join(lines[body_start:])
    # - Create the forward method source, including def line and indentation
    forward_method_source = f"def forward{new_sig}:\n{tool_source_body}"
    # - Create the class source
    indent = " " * 4  # for class method
    class_source = (
        textwrap.dedent(f"""
        class SimpleTool(Tool):
            name: str = "{tool_json_schema["name"]}"
            description: str = {json.dumps(textwrap.dedent(tool_json_schema["description"]).strip())}
            inputs: dict[str, dict[str, str]] = {tool_json_schema["parameters"]["properties"]}
            output_type: str = "{tool_json_schema["return"]["type"]}"

            def __init__(self):
                self.is_initialized = True

        """)
        + textwrap.indent(decorator_lines, indent)
        + textwrap.indent(forward_method_source, indent)
    )
    # - Store the source code on both class and method for inspection
    SimpleTool.__source__ = class_source
    SimpleTool.forward.__source__ = forward_method_source

    simple_tool = SimpleTool()
    return simple_tool
