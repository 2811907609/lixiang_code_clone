def drop_last_line(text: str) -> str:
    lines = text.splitlines()
    if lines:
        lines.pop()  # Remove the last line
    return '\n'.join(lines)


def drop_first_line(text: str) -> str:
    lines = text.splitlines()
    if lines:
        lines.pop(0)  # Remove the first line
    return '\n'.join(lines)
