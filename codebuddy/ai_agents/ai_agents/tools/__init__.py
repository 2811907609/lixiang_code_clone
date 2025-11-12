"""Tools package for AI agents."""

from ai_agents.tools.code_editing import (
    search_and_replace,
    # codex_patch_apply,
)
from ai_agents.tools.ast_grep import (
    grep_func_content_by_keywords,
)
from ai_agents.tools.git import (
    get_git_diff_content,
    git_grep_files,
    is_path_in_repo,
)
from ai_agents.tools.sequential_thinking import sequential_thinking
from .grep.text_grep import search_keyword_in_directory, search_keyword_with_context
from .file_ops import (
    create_new_file,
    read_file_content,
    read_file_lines,
    get_file_info,
    get_file_outline,
    browse_directory,
)
from .parsers import (
    parse_code_elements,
    parse_code_with_treesitter,
    parse_code_with_regex,
    compare_parsers,
    analyze_file_structure,
)

# 工具函数映射表
_TOOLS_MAP = {
    'search_keyword_in_directory': search_keyword_in_directory,
    'search_keyword_with_context': search_keyword_with_context,
    'create_new_file': create_new_file,
    'read_file_content': read_file_content,
    'read_file_lines': read_file_lines,
    'get_file_info': get_file_info,
    'get_file_outline': get_file_outline,
    'browse_directory': browse_directory,
    'parse_code_elements': parse_code_elements,
    'analyze_file_structure': analyze_file_structure,
    'parse_code_with_treesitter': parse_code_with_treesitter,
    'parse_code_with_regex': parse_code_with_regex,
    'compare_parsers': compare_parsers,
    'search_and_replace': search_and_replace,
    'grep_func_content_by_keywords': grep_func_content_by_keywords,
    'get_git_diff_content': get_git_diff_content,
    'git_grep_files': git_grep_files,
    'is_path_in_repo': is_path_in_repo,
    'sequential_thinking': sequential_thinking
    }


def get_tool_by_name(tool_name: str):
    """
    根据工具名称返回对应的工具函数。

    Args:
        tool_name (str): 工具函数的名称

    Returns:
        callable: 对应的工具函数，如果找不到则返回 None
    """
    return _TOOLS_MAP.get(tool_name)


# 从 tools map 生成 __all__ 列表，并添加额外的导出项
__all__ = list(_TOOLS_MAP.keys()) + [
    # 'codex_patch_apply',  # 注释掉的导入，但仍在 __all__ 中
    'get_tool_by_name',   # 新增的函数
]
