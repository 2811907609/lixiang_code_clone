"""
Cline风格的diff处理器

基于Cline的TypeScript实现，使用纯函数提供SEARCH/REPLACE块处理能力。
支持多层次回退匹配策略：精确匹配 → 行级trim匹配 → 块锚点匹配。

参考: https://github.com/cline/cline/blob/main/src/core/assistant-message/diff.ts
"""

from typing import Tuple, Optional, List, NamedTuple


class SearchAndReplaceError(Exception):
    """Cline diff处理异常"""
    pass


class SearchReplaceBlock(NamedTuple):
    """搜索替换块"""
    search_content: str
    replace_content: str


# 格式标记常量
SEARCH_BLOCK_START = "------- SEARCH"
SEARCH_BLOCK_END = "======="
REPLACE_BLOCK_END = "+++++++ REPLACE"


def apply_cline_diff(original_content: str, diff_content: str) -> str:
    """
    应用Cline风格的diff到原始内容上

    基于SEARCH/REPLACE块格式处理diff，支持多层次匹配策略：
    1. 精确匹配 - 字符串完全匹配
    2. 行级trim匹配 - 忽略每行首尾空白符的匹配
    3. 块锚点匹配 - 使用首尾行作为锚点的模糊匹配

    Args:
        original_content (str): 原始文件内容
        diff_content (str): 包含SEARCH/REPLACE块的diff内容，格式为：
            ------- SEARCH
            要搜索的内容
            =======
            替换后的内容
            +++++++ REPLACE

    Returns:
        str: 应用diff后的修改内容

    Raises:
        SearchAndReplaceError: 当SEARCH块无法在原始内容中找到匹配时抛出

    Example:
        >>> original = "def hello():\n    print('hello')"
        >>> diff = '''------- SEARCH
        def hello():
            print('hello')
        =======
        def hello():
            print('hello world')
        +++++++ REPLACE'''
        >>> result = apply_cline_diff(original, diff)
        >>> print(result)
        def hello():
            print('hello world')
    """

    # 解析SEARCH/REPLACE块
    blocks = parse_search_replace_blocks(diff_content)

    if not blocks:
        return original_content

    # 按顺序应用每个块
    result = original_content
    processed_index = 0

    for block in blocks:
        # 查找匹配位置
        match_result = find_match_in_content(
            result,
            block.search_content,
            processed_index
        )

        if not match_result:
            raise SearchAndReplaceError(
                f"SEARCH块无法在文件中找到匹配:\n{block.search_content.rstrip()}\n"
                "请检查搜索内容是否与文件中的内容完全一致。"
            )

        start_idx, end_idx = match_result
        replacement_content = block.replace_content

        # 应用替换
        result = (
            result[:start_idx] +
            replacement_content +
            result[end_idx:]
        )

        # 更新处理位置
        processed_index = start_idx + len(replacement_content)

    return result


def parse_search_replace_blocks(diff_content: str) -> List[SearchReplaceBlock]:
    """
    解析diff内容中的SEARCH/REPLACE块

    Args:
        diff_content: diff内容字符串

    Returns:
        List[SearchReplaceBlock]: 解析出的搜索替换块列表
    """
    blocks = []
    lines = diff_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        if line == SEARCH_BLOCK_START:
            # 找到搜索块开始
            search_lines = []
            i += 1

            # 收集搜索内容直到分隔符
            while i < len(lines) and lines[i] != SEARCH_BLOCK_END:
                search_lines.append(lines[i])
                i += 1

            if i >= len(lines):
                raise SearchAndReplaceError("缺少SEARCH块结束标记 '======='")

            # 跳过分隔符
            i += 1

            # 收集替换内容直到REPLACE标记
            replace_lines = []
            while i < len(lines) and lines[i] != REPLACE_BLOCK_END:
                replace_lines.append(lines[i])
                i += 1

            if i >= len(lines):
                raise SearchAndReplaceError("缺少REPLACE块结束标记 '+++++++ REPLACE'")

            # 创建搜索替换块
            search_content = "\n".join(search_lines) + ("\n" if search_lines else "")
            replace_content = "\n".join(replace_lines) + ("\n" if replace_lines else "")

            blocks.append(SearchReplaceBlock(search_content, replace_content))

        i += 1

    return blocks


def find_match_in_content(content: str, search_text: str, start_index: int = 0) -> Optional[Tuple[int, int]]:
    """
    在内容中查找匹配，使用多层次匹配策略

    Args:
        content: 要搜索的内容
        search_text: 要查找的文本
        start_index: 开始搜索的位置

    Returns:
        Optional[Tuple[int, int]]: 匹配的开始和结束位置，如果未找到返回None
    """
    # 处理空搜索的特殊情况
    if not search_text.strip():
        if not content:
            return (0, 0)  # 新文件
        else:
            return (0, len(content))  # 替换整个文件

    # 1. 精确匹配
    exact_index = content.find(search_text, start_index)
    if exact_index != -1:
        return (exact_index, exact_index + len(search_text))

    # 2. 行级trim匹配
    line_match = _line_trimmed_match(content, search_text, start_index)
    if line_match:
        return line_match

    # 3. 块锚点匹配
    block_match = _block_anchor_match(content, search_text, start_index)
    if block_match:
        return block_match

    return None


def _line_trimmed_match(content: str, search_text: str, start_index: int) -> Optional[Tuple[int, int]]:
    """行级trim匹配，忽略每行首尾空白符"""
    content_lines = content.split("\n")
    search_lines = search_text.split("\n")

    # 移除搜索内容末尾的空行
    if search_lines and search_lines[-1] == "":
        search_lines.pop()

    if not search_lines:
        return None

    # 找到start_index对应的行号
    start_line_num = 0
    current_index = 0
    while current_index < start_index and start_line_num < len(content_lines):
        current_index += len(content_lines[start_line_num]) + 1  # +1 for \n
        start_line_num += 1

    # 在内容中查找匹配
    for i in range(start_line_num, len(content_lines) - len(search_lines) + 1):
        matches = True

        # 尝试匹配所有搜索行
        for j in range(len(search_lines)):
            if i + j >= len(content_lines):
                matches = False
                break
            content_trimmed = content_lines[i + j].strip()
            search_trimmed = search_lines[j].strip()
            if content_trimmed != search_trimmed:
                matches = False
                break

        if matches:
            # 计算精确的字符位置
            match_start_index = sum(len(content_lines[k]) + 1 for k in range(i))
            match_end_index = match_start_index + sum(
                len(content_lines[i + k]) + 1 for k in range(len(search_lines))
            )
            return (match_start_index, match_end_index)

    return None


def _block_anchor_match(content: str, search_text: str, start_index: int) -> Optional[Tuple[int, int]]:
    """块锚点匹配，使用首尾行作为锚点"""
    content_lines = content.split("\n")
    search_lines = search_text.split("\n")

    # 只对3行以上的块使用此策略
    if len(search_lines) < 3:
        return None

    # 移除末尾空行
    if search_lines and search_lines[-1] == "":
        search_lines.pop()

    if len(search_lines) < 3:
        return None

    first_line_search = search_lines[0].strip()
    last_line_search = search_lines[-1].strip()
    search_block_size = len(search_lines)

    # 找到start_index对应的行号
    start_line_num = 0
    current_index = 0
    while current_index < start_index and start_line_num < len(content_lines):
        current_index += len(content_lines[start_line_num]) + 1
        start_line_num += 1

    # 查找匹配的首尾锚点
    for i in range(start_line_num, len(content_lines) - search_block_size + 1):
        # 检查首行是否匹配
        if content_lines[i].strip() != first_line_search:
            continue

        # 检查尾行是否匹配
        if i + search_block_size - 1 >= len(content_lines):
            continue
        if content_lines[i + search_block_size - 1].strip() != last_line_search:
            continue

        # 计算精确字符位置
        match_start_index = sum(len(content_lines[k]) + 1 for k in range(i))
        match_end_index = match_start_index + sum(
            len(content_lines[i + k]) + 1 for k in range(search_block_size)
        )
        return (match_start_index, match_end_index)

    return None
