"""
代码编辑器主类

集成多种编辑策略，提供统一的代码编辑接口。
"""

import logging
from pathlib import Path
from typing import Dict, Any, NamedTuple
from enum import Enum

from .cline_diff import apply_cline_diff, SearchAndReplaceError
from .codex_diff import apply_codex_diff, CodexDiffError


class EditFormat(Enum):
    """支持的编辑格式"""
    CLINE = "cline"
    AIDER = "aider"  # 待实现
    CODEX = "codex"  # 待实现


class EditResult(NamedTuple):
    """编辑结果"""
    success: bool
    message: str
    original_content: str = ""
    new_content: str = ""
    changes_made: int = 0


def apply_file_edit(
    file_path: str,
    edit_instruction: Dict[str, Any],
    create_backup: bool = False,
    encoding: str = "utf-8"
) -> EditResult:
    """
    应用代码编辑到文件

    Args:
        file_path: 目标文件路径
        edit_instruction: 编辑指令，包含格式和内容
        create_backup: 是否创建备份文件
        encoding: 文件编码

    Returns:
        EditResult: 编辑结果
    """
    try:
        # 验证文件路径
        path = Path(file_path)
        if not path.exists():
            return EditResult(False, f"文件不存在: {file_path}")

        if not path.is_file():
            return EditResult(False, f"路径不是文件: {file_path}")

        # 读取原始内容
        try:
            with open(path, 'r', encoding=encoding) as f:
                original_content = f.read()
        except UnicodeDecodeError as e:
            return EditResult(False, f"文件编码错误: {e}")

        # 创建备份
        if create_backup:
            backup_path = path.with_suffix(path.suffix + '.backup')
            backup_path.write_text(original_content, encoding=encoding)
            logging.info(f"创建备份文件: {backup_path}")

        # 应用编辑
        new_content = apply_edit_to_content(original_content, edit_instruction)

        # 检查是否有变化
        if new_content == original_content:
            return EditResult(True, "文件内容无变化", original_content, new_content, 0)

        # 写入新内容
        try:
            with open(path, 'w', encoding=encoding) as f:
                f.write(new_content)
        except Exception as e:
            return EditResult(False, f"写入文件失败: {e}")

        # 计算变化统计
        changes_made = count_line_changes(original_content, new_content)

        logging.info(f"成功编辑文件: {file_path}, 变化数: {changes_made}")

        return EditResult(
            True,
            f"成功应用编辑，共 {changes_made} 处变化",
            original_content,
            new_content,
            changes_made
        )

    except Exception as e:
        logging.error(f"编辑文件时发生错误: {e}")
        return EditResult(False, f"编辑失败: {e}")


def apply_edit_to_content(content: str, edit_instruction: Dict[str, Any]) -> str:
    """
    应用编辑指令到内容

    Args:
        content: 原始内容
        edit_instruction: 编辑指令

    Returns:
        str: 编辑后的内容

    Raises:
        SearchAndReplaceError: 编辑失败时抛出
    """
    # 确定编辑格式
    format_str = edit_instruction.get('format', EditFormat.CLINE.value)
    edit_format = EditFormat(format_str)

    if edit_format == EditFormat.CLINE:
        return _apply_cline_edit(content, edit_instruction)
    elif edit_format == EditFormat.CODEX:
        return _apply_codex_edit(content, edit_instruction)
    elif edit_format == EditFormat.AIDER:
        raise SearchAndReplaceError("Aider格式暂未实现")
    else:
        raise SearchAndReplaceError(f"不支持的编辑格式: {edit_format}")


def _apply_cline_edit(content: str, edit_instruction: Dict[str, Any]) -> str:
    """应用Cline格式的编辑"""
    # 从指令中提取diff内容
    if 'diff_content' in edit_instruction:
        diff_content = edit_instruction['diff_content']
    elif 'search' in edit_instruction and 'replace' in edit_instruction:
        # 从search/replace构建diff格式
        search = edit_instruction['search']
        replace = edit_instruction['replace']
        diff_content = f"""------- SEARCH
{search}
=======
{replace}
+++++++ REPLACE"""
    else:
        raise SearchAndReplaceError("编辑指令缺少必要的diff_content或search/replace字段")

    return apply_cline_diff(content, diff_content)


def _apply_codex_edit(content: str, edit_instruction: Dict[str, Any]) -> str:
    """应用Codex格式的编辑"""
    # 从指令中提取diff内容
    if 'diff_content' in edit_instruction:
        diff_content = edit_instruction['diff_content']
    elif 'search' in edit_instruction and 'replace' in edit_instruction:
        # 从search/replace构建Codex格式
        search = edit_instruction['search']
        replace = edit_instruction['replace']
        context_marker = edit_instruction.get('context_marker', '')

        diff_content = f"""*** Begin Patch
*** Update File: content
{context_marker}
- {search.strip()}
+ {replace.strip()}
*** End Patch"""
    else:
        raise CodexDiffError("编辑指令缺少必要的diff_content或search/replace字段")

    return apply_codex_diff(content, diff_content)


def count_line_changes(original: str, new: str) -> int:
    """计算变化的行数"""
    original_lines = original.splitlines()
    new_lines = new.splitlines()

    # 简单的行级别差异计算
    max_lines = max(len(original_lines), len(new_lines))
    changes = 0

    for i in range(max_lines):
        orig_line = original_lines[i] if i < len(original_lines) else ""
        new_line = new_lines[i] if i < len(new_lines) else ""

        if orig_line != new_line:
            changes += 1

    return changes


def validate_edit_instruction(edit_instruction: Dict[str, Any]) -> tuple[bool, str]:
    """
    验证编辑指令的有效性

    Args:
        edit_instruction: 编辑指令

    Returns:
        tuple: (是否有效, 错误信息)
    """
    if not isinstance(edit_instruction, dict):
        return False, "编辑指令必须是字典类型"

    # 检查格式
    format_str = edit_instruction.get('format', EditFormat.CLINE.value)
    try:
        EditFormat(format_str)
    except ValueError:
        return False, f"不支持的编辑格式: {format_str}"

    # 检查必要字段
    if format_str == EditFormat.CLINE.value:
        if 'diff_content' not in edit_instruction:
            if not ('search' in edit_instruction and 'replace' in edit_instruction):
                return False, "Cline格式需要diff_content字段或search/replace字段"
    elif format_str == EditFormat.CODEX.value:
        if 'diff_content' not in edit_instruction:
            if not ('search' in edit_instruction and 'replace' in edit_instruction):
                return False, "Codex格式需要diff_content字段或search/replace字段"

    return True, ""


def create_cline_edit_instruction(search: str, replace: str) -> Dict[str, Any]:
    """
    创建Cline格式的编辑指令

    Args:
        search: 要搜索的内容
        replace: 要替换的内容

    Returns:
        Dict: 编辑指令
    """
    return {
        'format': EditFormat.CLINE.value,
        'search': search,
        'replace': replace
    }


def create_cline_diff_instruction(diff_content: str) -> Dict[str, Any]:
    """
    创建Cline格式的diff编辑指令

    Args:
        diff_content: 完整的diff内容

    Returns:
        Dict: 编辑指令
    """
    return {
        'format': EditFormat.CLINE.value,
        'diff_content': diff_content
    }
