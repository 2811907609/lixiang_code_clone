from typing import List

from inference_server.lang import get_language_comment_mark
from inference_server.utils.strings import is_blank


def replace_spectial_tokens(s, tokens: List[str]):
    """replace special token to <FIM_TOKEN_XX>"""
    if not tokens:
        return s
    tokens = [t for t in tokens if t]
    if not tokens:
        return s
    for i, t in enumerate(tokens):
        if (t in s) and t:
            s = s.replace(t, f'<FIM_TOKEN_{i}>')
    return s


def trim_fim_tokens(prefix, suffix, special_tokens: List[str]):
    # replace special tokens in prefix and suffix, avoid nested FIM
    prefix = replace_spectial_tokens(prefix, special_tokens)
    suffix = replace_spectial_tokens(suffix, special_tokens)
    return [prefix, suffix]


def split_rag_prefix_lines(lang: str, prefix: str):
    lines = prefix.split('\n')
    if not lang:
        return [], lines
    comment_mark = get_language_comment_mark(lang)
    if not comment_mark:
        return [], lines
    i = 0
    while (i < len(lines) and
           (is_blank(lines[i]) or lines[i].startswith(comment_mark))):
        i += 1
    return lines[:i], lines[i:]


def trim_head_lines(lines: List[str], max_length: int):
    """trim from leading lines so that left lines max max_length"""
    length = 0
    result = []
    for line in lines[::-1]:
        if length + len(line) + 1 > max_length:
            break
        result.append(line)
        length += 1 + len(line)
    result = result[::-1]
    return '\n'.join(result)


def trim_tail_lines(lines: List[str], max_length: int):
    """trim from tailing lines so that left lines match max_length"""
    length = 0
    result = []

    for line in lines:
        if length + len(line) + 1 > max_length:
            break
        result.append(line)
        length += 1 + len(line)
    return '\n'.join(result)
