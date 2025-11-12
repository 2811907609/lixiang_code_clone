from typing import Any, Set


def jacard(s1: Set[Any], s2: Set[Any]) -> int:
    if not (s1 and s2):
        return 0.0
    i = len(s1.intersection(s2))
    u = len(s1.union(s2))
    return i / u
