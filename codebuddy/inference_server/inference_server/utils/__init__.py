import uuid
from typing import List

from .strings import parse_kv_pairs  # noqa
from .log import getLogger, setup_logging  # noqa
from .number import xfloat  # noqa


def random_uuid() -> str:
    return str(uuid.uuid4().hex)


def find_min_index(text: str, stop: List[str]) -> int:
    if not stop:
        return -1
    min_index = -1

    for s in stop:
        index = text.find(s)
        if index < 0:
            continue
        if min_index == -1:
            min_index = index
            continue
        if index < min_index:
            min_index = index

    return min_index
