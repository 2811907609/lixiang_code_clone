"""
AI Agent 代码编辑模块

本模块提供智能代码编辑功能，支持多种编辑格式和匹配策略。
基于对主流AI编程助手（Aider、Codex、Cline等）的深入分析实现。

主要特性：
- 多格式支持（Aider、Codex、Cline格式）
- 分层匹配策略（精确 → 容错 → 模糊 → 锚点）
- 智能错误处理和详细反馈
- Unicode标准化和缩进保持
- 高性能和可靠性

使用示例：
    # 使用CodeEditor类
    from ai_agents.tools.code_editing import CodeEditor, EditFormat

    editor = CodeEditor(default_format=EditFormat.CLINE)
    result = editor.apply_edit(
        file_path="src/main.py",
        edit_instruction={
            "format": "cline",
            "search": "def old_function():",
            "replace": "def new_function():"
        }
    )

    # 使用工具函数（推荐用于AI Agent）
    from ai_agents.tools.code_editing import cline_search_replace

    result = cline_search_replace(
        file_path="src/main.py",
        search_content="def old_function():\n    return 'old'",
        replace_content="def new_function():\n    return 'new'"
    )
"""

__version__ = "0.1.0"
__author__ = "AI Agents Team"

# 导出核心类和函数
from .core.editor import apply_file_edit, EditFormat, EditResult, apply_edit_to_content
from .core.cline_diff import apply_cline_diff, SearchAndReplaceError
from .core.codex_diff import apply_codex_diff, simple_codex_update, CodexDiffError
from .cline_editor_tool import search_and_replace
from .codex_editor_tool import codex_patch_apply, codex_simple_update, get_codex_patch_format_help

__all__ = [
    # 核心类和函数
    "apply_file_edit",
    "apply_edit_to_content",
    "EditFormat",
    "EditResult",

    # Cline diff处理
    "apply_cline_diff",
    "SearchAndReplaceError",

    # Codex diff处理
    "apply_codex_diff",
    "simple_codex_update",
    "CodexDiffError",

    # 工具函数
    "search_and_replace",
    "codex_patch_apply",
    "codex_simple_update",
    "get_codex_patch_format_help",
]
