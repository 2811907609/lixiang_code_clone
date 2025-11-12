def indent_len(line: str) -> int:
    return len(line) - len(line.lstrip())


def is_block_closing_line(lines: list[str], index: int) -> bool:
    if index <= 0 or (index > len(lines) - 1):
        return False
    # 如果前一行缩进更多，则当前行是代码块的闭合行
    return indent_len(lines[index - 1]) > indent_len(lines[index])
