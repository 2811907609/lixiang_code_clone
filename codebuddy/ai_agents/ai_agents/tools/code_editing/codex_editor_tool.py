"""
OpenAI Codex风格的代码编辑工具

提供基于Codex结构化补丁格式的代码编辑功能，可作为AI Agent工具使用。
"""

import logging
from pathlib import Path

from .core.editor import apply_file_edit, EditFormat
from .core.codex_diff import CodexDiffError


def codex_patch_apply(
    file_path: str,
    patch_content: str,
    create_backup: bool = False,
    encoding: str = "utf-8"
) -> str:
    """
    使用OpenAI Codex风格的结构化补丁格式编辑代码文件。

    这个工具实现了OpenAI Codex的补丁算法，支持：
    - *** Begin Patch / *** End Patch 格式
    - *** Update File: / *** Add File: / *** Delete File: 操作
    - @@ 上下文标记用于精确定位
    - Unicode标点符号标准化
    - 多层次匹配策略（精确 → 忽略行尾空白 → 忽略所有空白）

    相比传统的行号diff，Codex格式使用上下文来定位代码，更适合AI生成。

    Args:
        file_path: 要编辑的文件路径
        patch_content: 完整的Codex格式补丁内容
        create_backup: 是否创建备份文件（默认False）
        encoding: 文件编码（默认utf-8）

    Returns:
        str: 操作结果描述

    Raises:
        ValueError: 参数无效或补丁应用失败时

    Examples:
        # 基本的更新操作
        >>> patch = '''*** Begin Patch
        ... *** Update File: app.py
        ... @@ def main():
        ... - print("Hello")
        ... + print("Hello, World!")
        ... *** End Patch'''
        >>> codex_patch_apply("app.py", patch)

        # 带上下文标记的复杂更新
        >>> patch = '''*** Begin Patch
        ... *** Update File: models.py
        ... @@ class UserModel:
        ... @@ def validate(self):
        ...     if not self.email:
        ...         return False
        ... -     return True
        ... +     return self.email.endswith('@company.com')
        ... *** End Patch'''
        >>> codex_patch_apply("models.py", patch)
    """
    # 参数验证
    if not file_path or not file_path.strip():
        raise ValueError("file_path不能为空")

    if not patch_content or not patch_content.strip():
        raise ValueError("patch_content不能为空")

    # 创建编辑指令
    edit_instruction = {
        'format': EditFormat.CODEX.value,
        'diff_content': patch_content
    }

    # 执行编辑
    try:
        result = apply_file_edit(file_path, edit_instruction, create_backup, encoding)

        if result.success:
            return result.message
        else:
            # 编辑失败，提供详细的错误信息
            error_msg = f"编辑失败: {result.message}"

            # 如果是上下文匹配失败，提供更多帮助信息
            if "无效的上下文" in result.message:
                error_msg += "\n\n建议检查："
                error_msg += "\n1. @@ 上下文标记是否正确"
                error_msg += "\n2. 代码上下文是否与文件中的内容匹配"
                error_msg += "\n3. 确保删除行（-）与文件中的实际内容一致"
                error_msg += "\n4. 检查Unicode字符和标点符号"

            raise ValueError(error_msg)

    except CodexDiffError as e:
        raise ValueError(f"Codex补丁处理错误: {e}") from e
    except Exception as e:
        logging.error(f"代码编辑工具发生未预期错误: {e}")
        raise ValueError(f"编辑操作失败: {e}") from e


def codex_simple_update(
    file_path: str,
    search_content: str,
    replace_content: str,
    context_marker: str = "",
    create_backup: bool = False,
    encoding: str = "utf-8"
) -> str:
    """
    使用Codex格式进行简单的搜索替换操作。

    这是codex_patch_apply的简化版本，自动构建Codex补丁格式。
    适用于简单的代码替换场景。

    Args:
        file_path: 要编辑的文件路径
        search_content: 要搜索的代码内容（将被删除）
        replace_content: 要替换的新代码内容（将被插入）
        context_marker: 可选的上下文标记，如 "@@ class MyClass" 或 "@@ def method():"
        create_backup: 是否创建备份文件（默认False）
        encoding: 文件编码（默认utf-8）

    Returns:
        str: 操作结果描述

    Examples:
        # 简单替换
        >>> codex_simple_update(
        ...     "app.py",
        ...     'print("Hello")',
        ...     'print("Hello, World!")'
        ... )

        # 带上下文标记的替换
        >>> codex_simple_update(
        ...     "models.py",
        ...     "return True",
        ...     "return self.is_valid()",
        ...     "@@ class UserModel:"
        ... )
    """
    # 参数验证
    if not file_path or not file_path.strip():
        raise ValueError("file_path不能为空")

    if search_content is None:
        raise ValueError("search_content不能为None")

    if replace_content is None:
        raise ValueError("replace_content不能为None")

    # 构建Codex格式补丁
    patch_content = f"""*** Begin Patch
*** Update File: {Path(file_path).name}
{context_marker}
- {search_content.strip()}
+ {replace_content.strip()}
*** End Patch"""

    # 使用完整的补丁应用工具
    return codex_patch_apply(file_path, patch_content, create_backup, encoding)


def get_codex_patch_format_help() -> str:
    """
    获取Codex补丁格式的帮助信息

    Returns:
        str: 格式说明
    """
    return """
OpenAI Codex 补丁格式说明:

基本结构:
*** Begin Patch
*** [ACTION] File: [path/to/file]
[补丁内容]
*** End Patch

支持的操作:
1. *** Update File: path/to/file  - 更新现有文件
2. *** Add File: path/to/file     - 添加新文件
3. *** Delete File: path/to/file  - 删除文件

更新文件格式:
*** Update File: example.py
@@ class MyClass:          # 可选的上下文标记
@@ def method():           # 可以有多个上下文标记
    [3行上下文]
-   [要删除的代码行]        # 前缀 - 表示删除
+   [要添加的代码行]        # 前缀 + 表示添加
    [3行上下文]

特点:
1. 使用上下文而非行号定位代码
2. Unicode标点符号自动标准化
3. 多层次匹配策略（精确 → 忽略空白 → 模糊匹配）
4. @@ 标记用于指定类或函数上下文
5. 支持复杂的代码结构变更

匹配策略（按优先级）:
1. 精确匹配 - Unicode标准化后完全相同
2. 忽略行尾空白 - 忽略每行末尾的空白字符
3. 忽略所有空白 - 忽略行首尾的所有空白字符

注意事项:
- 删除行（-）必须与文件中的实际内容完全匹配
- 上下文行用于精确定位，通常需要3行
- 可以使用多个@@ 标记来指定嵌套的上下文
- 文件路径只能是相对路径，不支持绝对路径
"""


if __name__ == "__main__":
    # 简单的测试
    print("Codex编辑工具已加载")
    print(get_codex_patch_format_help())
