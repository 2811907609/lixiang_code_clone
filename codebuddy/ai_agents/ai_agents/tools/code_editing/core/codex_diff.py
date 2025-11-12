"""
OpenAI Codex风格的diff处理器

基于OpenAI Codex的结构化补丁格式实现，支持：
- *** Begin Patch / *** End Patch 格式
- *** Update File: / *** Add File: / *** Delete File: 操作
- @@ 上下文标记
- Unicode标点符号标准化
- 多层次匹配策略

参考: https://github.com/openai/codex/blob/main/codex-cli/src/utils/agent/apply-patch.ts
"""

import unicodedata
from typing import List, Dict, Optional, Tuple, NamedTuple
from enum import Enum


class CodexDiffError(Exception):
    """Codex diff处理异常"""
    pass


class ActionType(Enum):
    """操作类型"""
    ADD = "add"
    DELETE = "delete"
    UPDATE = "update"


class Chunk(NamedTuple):
    """代码块"""
    orig_index: int  # 原始文件中的行索引
    del_lines: List[str]  # 要删除的行
    ins_lines: List[str]  # 要插入的行


class PatchAction(NamedTuple):
    """补丁操作"""
    type: ActionType
    new_file: Optional[str] = None  # 新文件内容（ADD操作）
    chunks: List[Chunk] = []  # 代码块列表（UPDATE操作）
    move_path: Optional[str] = None  # 移动目标路径


class Patch(NamedTuple):
    """补丁"""
    actions: Dict[str, PatchAction]


# 格式标记常量
PATCH_PREFIX = "*** Begin Patch"
PATCH_SUFFIX = "*** End Patch"
UPDATE_FILE_PREFIX = "*** Update File: "
ADD_FILE_PREFIX = "*** Add File: "
DELETE_FILE_PREFIX = "*** Delete File: "
MOVE_FILE_TO_PREFIX = "*** Move File To: "
END_OF_FILE_PREFIX = "*** End of File"
HUNK_ADD_LINE_PREFIX = "+"


def apply_codex_diff(original_content: str, diff_content: str) -> str:
    """
    应用Codex风格的diff到原始内容

    Args:
        original_content: 原始文件内容
        diff_content: 包含Codex格式补丁的内容

    Returns:
        str: 应用diff后的新内容

    Raises:
        CodexDiffError: diff处理失败时抛出
    """
    # 使用简化版本实现
    return apply_codex_diff_simple(original_content, diff_content)


def text_to_patch(text: str, orig: Dict[str, str]) -> Tuple[Patch, int]:
    """
    将文本转换为补丁对象

    Args:
        text: 补丁文本
        orig: 原始文件内容字典

    Returns:
        Tuple[Patch, int]: 补丁对象和模糊匹配分数
    """
    lines = text.strip().split("\n")

    if (len(lines) < 2 or
        not lines[0].startswith(PATCH_PREFIX.strip()) or
        lines[-1] != PATCH_SUFFIX.strip()):
        raise CodexDiffError("无效的补丁格式：必须以 '*** Begin Patch' 开始，'*** End Patch' 结束")

    parser = CodexParser(orig, lines)
    parser.index = 1  # 跳过开始标记
    parser.parse()

    return Patch(parser.patch_actions), parser.fuzz


class CodexParser:
    """Codex补丁解析器"""

    def __init__(self, current_files: Dict[str, str], lines: List[str]):
        self.current_files = current_files
        self.lines = lines
        self.index = 0
        self.patch_actions: Dict[str, PatchAction] = {}
        self.fuzz = 0

    def is_done(self, prefixes: Optional[List[str]] = None) -> bool:
        """检查是否解析完成"""
        if self.index >= len(self.lines):
            return True

        if prefixes:
            current_line = self.lines[self.index]
            return any(current_line.startswith(p.strip()) for p in prefixes)

        return False

    def startswith(self, prefix) -> bool:
        """检查当前行是否以指定前缀开始"""
        if self.index >= len(self.lines):
            return False

        prefixes = prefix if isinstance(prefix, list) else [prefix]
        return any(self.lines[self.index].startswith(p) for p in prefixes)

    def read_str(self, prefix: str = "", return_everything: bool = False) -> str:
        """读取字符串"""
        if self.index >= len(self.lines):
            raise CodexDiffError(f"索引超出范围: {self.index} >= {len(self.lines)}")

        if self.lines[self.index].startswith(prefix):
            text = (self.lines[self.index] if return_everything
                   else self.lines[self.index][len(prefix):])
            self.index += 1
            return text

        return ""

    def parse(self) -> None:
        """解析补丁"""
        while not self.is_done([PATCH_SUFFIX]):
            # 尝试解析Update File
            path = self.read_str(UPDATE_FILE_PREFIX)
            if path:
                if path in self.patch_actions:
                    raise CodexDiffError(f"重复的文件路径: {path}")

                move_to = self.read_str(MOVE_FILE_TO_PREFIX)

                if path not in self.current_files:
                    raise CodexDiffError(f"文件不存在: {path}")

                text = self.current_files[path]
                action = self._parse_update_file(text)

                self.patch_actions[path] = PatchAction(
                    type=ActionType.UPDATE,
                    chunks=action.chunks,
                    move_path=move_to if move_to else None
                )
                continue

            # 尝试解析Delete File
            path = self.read_str(DELETE_FILE_PREFIX)
            if path:
                if path in self.patch_actions:
                    raise CodexDiffError(f"重复的文件路径: {path}")

                if path not in self.current_files:
                    raise CodexDiffError(f"要删除的文件不存在: {path}")

                self.patch_actions[path] = PatchAction(type=ActionType.DELETE)
                continue

            # 尝试解析Add File
            path = self.read_str(ADD_FILE_PREFIX)
            if path:
                if path in self.patch_actions:
                    raise CodexDiffError(f"重复的文件路径: {path}")

                if path in self.current_files:
                    raise CodexDiffError(f"文件已存在: {path}")

                action = self._parse_add_file()
                self.patch_actions[path] = action
                continue

            raise CodexDiffError(f"未知的行: {self.lines[self.index]}")

        if not self.startswith(PATCH_SUFFIX.strip()):
            raise CodexDiffError("缺少结束标记")

        self.index += 1

    def _parse_update_file(self, text: str) -> PatchAction:
        """解析更新文件操作"""
        chunks = []
        file_lines = text.split("\n")
        index = 0

        while not self.is_done([
            PATCH_SUFFIX, UPDATE_FILE_PREFIX, DELETE_FILE_PREFIX,
            ADD_FILE_PREFIX, END_OF_FILE_PREFIX
        ]):
            # 处理@@ 上下文标记
            def_str = self.read_str("@@ ")
            section_str = ""

            if not def_str and self.index < len(self.lines) and self.lines[self.index] == "@@":
                section_str = self.lines[self.index]
                self.index += 1

            if not (def_str or section_str or index == 0):
                raise CodexDiffError(f"无效的行: {self.lines[self.index]}")

            if def_str.strip():
                # 查找上下文定义行
                found = False
                canonical_def = _canonicalize_text(def_str)

                for i in range(index, len(file_lines)):
                    if _canonicalize_text(file_lines[i]) == canonical_def:
                        index = i + 1
                        found = True
                        break

                if not found:
                    # 尝试trim匹配
                    for i in range(index, len(file_lines)):
                        if _canonicalize_text(file_lines[i].strip()) == _canonicalize_text(def_str.strip()):
                            index = i + 1
                            self.fuzz += 1
                            found = True
                            break

            # 解析下一个代码段
            next_chunk_context, new_chunks, end_patch_index, eof = self._peek_next_section()

            # 查找上下文
            new_index, fuzz = _find_context(file_lines, next_chunk_context, index, eof)

            if new_index == -1:
                ctx_text = "\n".join(next_chunk_context)
                if eof:
                    raise CodexDiffError(f"无效的EOF上下文 {index}:\n{ctx_text}")
                else:
                    raise CodexDiffError(f"无效的上下文 {index}:\n{ctx_text}")

            self.fuzz += fuzz

            # 调整块的原始索引
            for chunk in new_chunks:
                chunks.append(Chunk(
                    orig_index=chunk.orig_index + new_index,
                    del_lines=chunk.del_lines,
                    ins_lines=chunk.ins_lines
                ))

            index = new_index + len(next_chunk_context)
            self.index = end_patch_index

        return PatchAction(type=ActionType.UPDATE, chunks=chunks)

    def _parse_add_file(self) -> PatchAction:
        """解析添加文件操作"""
        lines = []

        while not self.is_done([
            PATCH_SUFFIX, UPDATE_FILE_PREFIX, DELETE_FILE_PREFIX, ADD_FILE_PREFIX
        ]):
            s = self.read_str()
            if not s.startswith(HUNK_ADD_LINE_PREFIX):
                raise CodexDiffError(f"无效的添加文件行: {s}")

            lines.append(s[1:])  # 移除前缀

        return PatchAction(type=ActionType.ADD, new_file="\n".join(lines))

    def _peek_next_section(self) -> Tuple[List[str], List[Chunk], int, bool]:
        """预览下一个代码段"""
        index = self.index
        old_lines = []
        del_lines = []
        ins_lines = []
        chunks = []
        mode = "keep"  # keep, add, delete

        while index < len(self.lines):
            s = self.lines[index]

            # 检查结束条件
            if any(s.startswith(p.strip()) for p in [
                "@@", PATCH_SUFFIX, UPDATE_FILE_PREFIX, DELETE_FILE_PREFIX,
                ADD_FILE_PREFIX, END_OF_FILE_PREFIX
            ]):
                break

            if s == "***":
                break

            if s.startswith("***"):
                raise CodexDiffError(f"无效的行: {s}")

            index += 1
            last_mode = mode
            line = s

            # 确定行类型
            if line.startswith(HUNK_ADD_LINE_PREFIX):
                mode = "add"
            elif line.startswith("-"):
                mode = "delete"
            elif line.startswith(" "):
                mode = "keep"
            else:
                # 容错处理：缺少前导空格的上下文行
                mode = "keep"
                line = " " + line

            line = line[1:]  # 移除前缀

            # 处理模式切换
            if mode == "keep" and last_mode != mode:
                if ins_lines or del_lines:
                    chunks.append(Chunk(
                        orig_index=len(old_lines) - len(del_lines),
                        del_lines=del_lines.copy(),
                        ins_lines=ins_lines.copy()
                    ))
                del_lines.clear()
                ins_lines.clear()

            # 添加行到相应列表
            if mode == "delete":
                del_lines.append(line)
                old_lines.append(line)
            elif mode == "add":
                ins_lines.append(line)
            else:
                old_lines.append(line)

        # 处理最后的块
        if ins_lines or del_lines:
            chunks.append(Chunk(
                orig_index=len(old_lines) - len(del_lines),
                del_lines=del_lines,
                ins_lines=ins_lines
            ))

        # 检查是否为文件结尾
        eof = (index < len(self.lines) and
               self.lines[index] == END_OF_FILE_PREFIX)
        if eof:
            index += 1

        return old_lines, chunks, index, eof


def _canonicalize_text(text: str) -> str:
    """
    标准化文本，处理Unicode标点符号

    基于Codex实现的Unicode标点符号标准化，将视觉上相似的字符
    统一为ASCII版本，提高匹配的鲁棒性。
    """
    # Unicode标点符号等价映射
    PUNCT_EQUIV = {
        # 连字符/破折号变体
        "-": "-",           # U+002D HYPHEN-MINUS
        "\u2010": "-",      # U+2010 HYPHEN
        "\u2011": "-",      # U+2011 NO-BREAK HYPHEN
        "\u2012": "-",      # U+2012 FIGURE DASH
        "\u2013": "-",      # U+2013 EN DASH
        "\u2014": "-",      # U+2014 EM DASH
        "\u2212": "-",      # U+2212 MINUS SIGN

        # 双引号
        "\u0022": '"',      # U+0022 QUOTATION MARK
        "\u201C": '"',      # U+201C LEFT DOUBLE QUOTATION MARK
        "\u201D": '"',      # U+201D RIGHT DOUBLE QUOTATION MARK
        "\u201E": '"',      # U+201E DOUBLE LOW-9 QUOTATION MARK
        "\u00AB": '"',      # U+00AB LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00BB": '"',      # U+00BB RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK

        # 单引号
        "\u0027": "'",      # U+0027 APOSTROPHE
        "\u2018": "'",      # U+2018 LEFT SINGLE QUOTATION MARK
        "\u2019": "'",      # U+2019 RIGHT SINGLE QUOTATION MARK
        "\u201B": "'",      # U+201B SINGLE HIGH-REVERSED-9 QUOTATION MARK

        # 空格
        "\u00A0": " ",      # U+00A0 NO-BREAK SPACE
        "\u202F": " ",      # U+202F NARROW NO-BREAK SPACE
    }

    # 先进行Unicode标准化
    normalized = unicodedata.normalize("NFC", text)

    # 替换标点符号
    result = ""
    for char in normalized:
        result += PUNCT_EQUIV.get(char, char)

    return result


def _find_context_core(lines: List[str], context: List[str], start: int) -> Tuple[int, int]:
    """
    核心上下文查找函数

    Args:
        lines: 文件行列表
        context: 要查找的上下文行列表
        start: 开始搜索的位置

    Returns:
        Tuple[int, int]: (匹配位置, 模糊匹配分数)
    """
    if not context:
        return start, 0

    # 第一轮：标准化后的精确匹配
    canonical_context = _canonicalize_text("\n".join(context))

    for i in range(start, len(lines)):
        if i + len(context) > len(lines):
            break

        segment = _canonicalize_text("\n".join(lines[i:i + len(context)]))
        if segment == canonical_context:
            return i, 0

    # 第二轮：忽略行尾空白符
    for i in range(start, len(lines)):
        if i + len(context) > len(lines):
            break

        segment_lines = [line.rstrip() for line in lines[i:i + len(context)]]
        context_lines = [line.rstrip() for line in context]

        segment = _canonicalize_text("\n".join(segment_lines))
        ctx = _canonicalize_text("\n".join(context_lines))

        if segment == ctx:
            return i, 1

    # 第三轮：忽略所有首尾空白符
    for i in range(start, len(lines)):
        if i + len(context) > len(lines):
            break

        segment_lines = [line.strip() for line in lines[i:i + len(context)]]
        context_lines = [line.strip() for line in context]

        segment = _canonicalize_text("\n".join(segment_lines))
        ctx = _canonicalize_text("\n".join(context_lines))

        if segment == ctx:
            return i, 100

    return -1, 0


def _find_context(lines: List[str], context: List[str], start: int, eof: bool) -> Tuple[int, int]:
    """
    查找上下文位置

    Args:
        lines: 文件行列表
        context: 要查找的上下文行列表
        start: 开始搜索的位置
        eof: 是否为文件结尾

    Returns:
        Tuple[int, int]: (匹配位置, 模糊匹配分数)
    """
    if eof:
        # 文件结尾：从文件末尾开始查找
        new_index, fuzz = _find_context_core(
            lines, context, len(lines) - len(context)
        )
        if new_index != -1:
            return new_index, fuzz

        # 如果末尾查找失败，从start位置查找
        new_index, fuzz = _find_context_core(lines, context, start)
        return new_index, fuzz + 10000

    return _find_context_core(lines, context, start)


def _get_updated_file(text: str, action: PatchAction, path: str) -> str:
    """
    获取更新后的文件内容

    Args:
        text: 原始文件内容
        action: 补丁操作
        path: 文件路径（用于错误信息）

    Returns:
        str: 更新后的文件内容
    """
    if action.type != ActionType.UPDATE:
        raise CodexDiffError("期望UPDATE操作")

    orig_lines = text.split("\n")
    dest_lines = []
    orig_index = 0

    for chunk in action.chunks:
        if chunk.orig_index > len(orig_lines):
            raise CodexDiffError(
                f"{path}: chunk.orig_index {chunk.orig_index} > len(lines) {len(orig_lines)}"
            )

        if orig_index > chunk.orig_index:
            raise CodexDiffError(
                f"{path}: orig_index {orig_index} > chunk.orig_index {chunk.orig_index}"
            )

        # 添加到块开始位置之前的行
        dest_lines.extend(orig_lines[orig_index:chunk.orig_index])
        orig_index = chunk.orig_index

        # 添加插入的行
        dest_lines.extend(chunk.ins_lines)

        # 跳过删除的行
        orig_index += len(chunk.del_lines)

    # 添加剩余的行
    dest_lines.extend(orig_lines[orig_index:])

    return "\n".join(dest_lines)


def simple_codex_update(content: str, search: str, replace: str, context_marker: str = "") -> str:
    """
    简单的Codex格式更新操作

    Args:
        content: 原始内容
        search: 要搜索的文本
        replace: 要替换的文本
        context_marker: 可选的上下文标记（在简化版本中被忽略）

    Returns:
        str: 更新后的内容
    """
    # 使用更完善的_apply_replacement函数，它支持多层次匹配策略
    return _apply_replacement(content, search, replace)


def apply_codex_diff_simple(original_content: str, diff_content: str) -> str:
    """
    简化但功能完整的Codex diff应用

    支持基本的UPDATE操作，包括：
    - 单行和多行替换
    - Unicode标准化
    - 空白符容错
    - 上下文忽略（简化处理）
    """
    lines = diff_content.strip().split('\n')

    if not (lines[0].startswith(PATCH_PREFIX.strip()) and
            lines[-1] == PATCH_SUFFIX.strip()):
        raise CodexDiffError("无效的补丁格式：必须以 '*** Begin Patch' 开始，'*** End Patch' 结束")

    # 查找Update File行
    update_file_line = None
    for line in lines:
        if line.startswith(UPDATE_FILE_PREFIX):
            update_file_line = line
            break

    if not update_file_line:
        return original_content

    # 解析删除和添加的行对
    operations = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 跳过上下文标记和其他非操作行
        if (line.startswith('@@') or
            line.startswith('***') or
            line.startswith(' ') or
            not line.strip()):
            i += 1
            continue

        # 处理删除行
        if line.startswith('- '):
            del_line = line[2:]
            add_line = ""

            # 查找对应的添加行
            if i + 1 < len(lines) and lines[i + 1].startswith('+ '):
                add_line = lines[i + 1][2:]
                i += 2  # 跳过添加行
            else:
                i += 1

            operations.append((del_line, add_line))

        # 处理单独的添加行（插入）
        elif line.startswith('+ '):
            add_line = line[2:]
            operations.append(("", add_line))
            i += 1
        else:
            i += 1

    # 应用操作
    result = original_content

    for del_line, add_line in operations:
        if del_line:  # 替换操作
            result = _apply_replacement(result, del_line, add_line)
        else:  # 插入操作（暂时简化为在末尾添加）
            if add_line.strip():
                result = result.rstrip() + '\n' + add_line + '\n'

    return result


def _apply_replacement(content: str, search: str, replace: str) -> str:
    """
    应用单个替换操作，支持多层次匹配

    Args:
        content: 原始内容
        search: 要搜索的文本
        replace: 要替换的文本

    Returns:
        str: 替换后的内容

    Raises:
        CodexDiffError: 找不到匹配内容时抛出
    """
    # 1. 精确匹配
    if search in content:
        return content.replace(search, replace, 1)  # 只替换第一个匹配

    # 2. 标准化匹配
    canonical_search = _canonicalize_text(search.strip())
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if _canonicalize_text(line.strip()) == canonical_search:
            # 保持原有缩进
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + replace.strip()
            return '\n'.join(lines)

    # 3. 行级trim匹配
    search_stripped = search.strip()
    for i, line in enumerate(lines):
        if line.strip() == search_stripped:
            # 保持原有缩进
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + replace.strip()
            return '\n'.join(lines)

    # 4. 标准化的行级匹配
    for i, line in enumerate(lines):
        if _canonicalize_text(line.strip()) == _canonicalize_text(search_stripped):
            # 保持原有缩进
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + replace.strip()
            return '\n'.join(lines)

    # 所有匹配策略都失败
    raise CodexDiffError(f"无法找到匹配的内容: {search.strip()}")
