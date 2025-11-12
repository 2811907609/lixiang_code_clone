import re
from typing import Set

_reg_tokenize = re.compile(r"((?:[a-z][a-z0-9]*)|(?:[A-Z]+[a-z0-9]*))")


def simple_tokenize(s: str, ignored_tokens: Set[str] = None):
    result = set()
    tokens = _reg_tokenize.findall(s)
    for token in tokens:
        if not token:
            continue
        result.add(token.lower())
    return result
