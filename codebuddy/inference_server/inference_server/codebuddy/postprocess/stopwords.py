from dataclasses import dataclass
from typing import List

import regex

from inference_server.utils import find_min_index


def trim_last_stop(text: str, stop: List[str]) -> str:
    min_index = find_min_index(text, stop)
    if min_index != -1:
        text = text[:min_index]
    return text


def is_regex_stop_word(stop: str) -> tuple[bool, str]:
    """Check if stop word is regex pattern (r/<regex>/) and extract the regex."""
    if stop.startswith('r/') and stop.endswith('/') and len(stop) > 3:
        return True, stop[2:-1]  # Extract regex from r/<regex>/
    return False, ''


@dataclass
class StopMatchType:
    '''dataclass is preferred over Enum because Enum did not support hot reload'''
    PREFIX = 1
    WHOLE = 2
    NOT_MATCH = 3


def get_stop_match_type(text: str, stops: List[str]) -> tuple[StopMatchType, str]:
    if not text:
        return StopMatchType.NOT_MATCH, ''
    if not stops:
        return StopMatchType.NOT_MATCH, ''

    for stop in stops:
        is_regex, regex_pattern = is_regex_stop_word(stop)

        if is_regex:
            # Handle regex stop words
            match_type, matched = is_suffix_regex_prefix(text, regex_pattern)
            if match_type != StopMatchType.NOT_MATCH:
                return match_type, matched
        else:
            # Handle regular string stop words
            if text == stop:
                return StopMatchType.WHOLE, stop
            elif stop.startswith(text):
                return StopMatchType.PREFIX, ""

    return StopMatchType.NOT_MATCH, ''


def is_suffix_regex_prefix(text: str, pattern: str) -> tuple[StopMatchType, str]:
    if not text or not pattern:
        return StopMatchType.NOT_MATCH, ""

    try:
        compiled = regex.compile(pattern)
        match = compiled.search(text, partial=True)
        if not match:
            return StopMatchType.NOT_MATCH, ""
        match_part = match.group()
        if not match_part:
            return StopMatchType.NOT_MATCH, ""
        suffix_match = text.endswith(match_part)
        if not suffix_match:
            return StopMatchType.NOT_MATCH, ""
        if match.partial:
            return StopMatchType.PREFIX, ""
        return StopMatchType.WHOLE, match_part
    except Exception as e:
        print('got repex error', e)
        return StopMatchType.NOT_MATCH, ""


def stream_stop(stream_gen, stops: List[str]):
    '''stream_gen is a generate that will generate a token each iteration.
You need to aggregate multiple tokens so that you can compare with multiple
 tokens stop words.'''
    aggregated_str = ''
    stops = [s for s in stops if s]
    for s in stream_gen:
        for ch in s:
            aggregated_str += ch
            stop_type, _ = get_stop_match_type(aggregated_str, stops)
            # 比如stops里面有`hello word`, 输出hello时还无法确定是否要stop，那么继续累积
            if stop_type == StopMatchType.PREFIX:
                continue
            if stop_type == StopMatchType.WHOLE:
                yield ''
                return
            yield aggregated_str
            aggregated_str = ''
    # 有可能最后会剩下一些prefix match的stream结果，后面没有新的char，因此不会匹配stop，需要返回
    yield aggregated_str
