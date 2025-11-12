from typing import List

from inference_server.types import (
    CompletionResponseChoice,)


def dedup_multi_choices(choices: List[CompletionResponseChoice]):
    if not choices:
        return choices
    # I got a case that there is only one choice but index is 2
    if len(choices) == 1:
        choices[0].index = 0
        return choices
    m = {c.text: c for c in choices}
    choices = list(m.values())
    # sort by index and set index begin from 0
    choices.sort(key=lambda c: c.index)
    for i, c in enumerate(choices):
        c.index = i
    return choices
