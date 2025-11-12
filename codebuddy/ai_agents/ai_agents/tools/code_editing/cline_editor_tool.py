"""
Cline风格的代码编辑工具

提供基于Cline SEARCH/REPLACE格式的代码编辑功能，可作为AI Agent工具使用。
"""

import logging

from .core.editor import apply_file_edit, EditFormat
from .core.cline_diff import SearchAndReplaceError

def search_and_replace(
    file_path: str,
    diff_content: str,
    create_backup: bool = False,
    encoding: str = "utf-8"
) -> str:
    """
    使用智能差异格式编辑代码文件。

    这个工具支持使用 SEARCH/REPLACE 差异格式对代码文件进行精确编辑。

    主要特性：
    - 精确匹配：基于完整内容匹配进行替换
    - 智能空白符处理：自动处理缩进和空白符差异

    差异格式：
    ------- SEARCH
    [要搜索的精确代码内容]
    =======
    [要替换成的新代码内容]
    +++++++ REPLACE

    Args:
        file_path (str): 要编辑的文件路径
        diff_content (str): 包含搜索替换指令的差异内容，使用标准 SEARCH/REPLACE 格式
        create_backup (bool, optional): 是否在编辑前创建备份文件。默认为 False
        encoding (str, optional): 文件编码格式。默认为 "utf-8"

    Returns:
        str: 编辑操作的结果描述，包含成功信息或错误详情

    Raises:
        ValueError: 当参数无效、文件内容匹配失败或编辑操作失败时
        FileNotFoundError: 当指定的文件不存在时
        PermissionError: 当文件权限不足无法编辑时

    注意事项:
        - 搜索内容必须与文件中的内容精确匹配
        - 保持原有代码的缩进风格和格式
        - 建议在重要文件编辑前启用备份功能
    """
    if not file_path or not file_path.strip():
        raise ValueError("file_path不能为空")

    if not diff_content or not diff_content.strip():
        raise ValueError("diff_content不能为空")

    # 创建编辑指令
    edit_instruction = {
        'format': EditFormat.CLINE.value,
        'diff_content': diff_content
    }

    # 执行编辑
    try:
        result = apply_file_edit(file_path, edit_instruction, create_backup, encoding)

        if result.success:
            return result.message
        else:
            raise ValueError(f"编辑失败: {result.message}")

    except SearchAndReplaceError as e:
        raise ValueError(f"Cline diff处理错误: {e}") from e
    except Exception as e:
        logging.error(f"代码编辑工具发生未预期错误: {e}")
        raise ValueError(f"编辑操作失败: {e}") from e
