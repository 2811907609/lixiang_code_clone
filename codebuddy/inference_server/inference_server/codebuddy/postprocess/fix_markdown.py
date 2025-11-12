
from inference_server.types import CompletionItem


def remove_markdown_code_blocks(item: CompletionItem, *args, **kwargs):
    """移除模型返回结果中的 markdown 代码块标记

    一些模型可能返回如下格式的结果：
    ```python
    <the_completion_code>
    ```

    此函数将移除开头的语言标记行和结尾的结束标记，只保留实际的代码内容。
    """
    if item.is_empty_output or not item.out_lines:
        return

    lines = item.out_lines.copy()
    modified = False

    # 移除开头的 markdown 代码块标记 (如 ```python, ```js, ``` 等)
    if lines and lines[0].strip().startswith('```'):
        lines.pop(0)
        modified = True

    # 移除结尾的 markdown 代码块结束标记 (```)
    if lines and lines[-1].strip() == '```':
        lines.pop()
        modified = True

    if modified:
        item.out_lines = lines
        item.fixed_kinds.add(remove_markdown_code_blocks.__name__)
