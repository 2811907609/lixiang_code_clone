'''
pytest -vv  -s pkg/codebuddy/postprocess -k 'stream_gen'
'''

from .stopwords import (
    StopMatchType,
    get_stop_match_type,
    is_suffix_regex_prefix,
    stream_stop,
)


def gen1(n):
    for i in range(n):
        if i == 5:
            yield ''
        yield str(i)


def test_stream_gen():
    testcases = [
        (['56', '78'], '01234'),
        (['56', '3', '78'], '012'),
        ([], ''.join(list(gen1(10)))),
        ([''], ''.join(list(gen1(10)))),
        (['11'], ''.join(list(gen1(10)))),
    ]
    for testcase in testcases:
        stops = testcase[0]
        last_s = ''
        for i in stream_stop(gen1(10), stops):
            last_s += i
        assert last_s == testcase[1]


def test_is_suffix_regex_prefix():
    testcases = [
        # (text, pattern, expected_result)
        ('', '', StopMatchType.NOT_MATCH),
        ('hello', '', StopMatchType.NOT_MATCH),
        ('', 'world', StopMatchType.NOT_MATCH),
        ('hello world', r'world$', StopMatchType.WHOLE),
        ('hello wor', r'world$', StopMatchType.PREFIX),
        ('hello', r'world$', StopMatchType.NOT_MATCH),
        ('test123', r'\d+$', StopMatchType.WHOLE),
        ('test12', r'\d{3}$', StopMatchType.PREFIX),
        ('test1', r'\d{3}$', StopMatchType.PREFIX),
        ('test', r'\d{3}$', StopMatchType.NOT_MATCH),
        ('prefix hello', r'hello$', StopMatchType.WHOLE),
        ('prefix hell', r'hello$', StopMatchType.PREFIX),
        ('hello prefix', r'hello$', StopMatchType.NOT_MATCH),
        ('invalid[regex', r'[', StopMatchType.NOT_MATCH),
        ('code```', r'```$', StopMatchType.WHOLE),
        ('code``', r'```$', StopMatchType.PREFIX),
        ('code`', r'```$', StopMatchType.PREFIX),
        ('```code```', r'```$', StopMatchType.WHOLE),
    ]

    for text, pattern, expected in testcases:
        result, _ = is_suffix_regex_prefix(text, pattern)
        assert result == expected, f"Failed for text='{text}', pattern='{pattern}': expected {expected}, got {result}"


def test_get_stop_match_type():
    testcases = [
        # (text, stops, expected_match_type, expected_stop)
        # Empty inputs
        ('', [], StopMatchType.NOT_MATCH, ''),
        ('hello', [], StopMatchType.NOT_MATCH, ''),
        ('', ['stop'], StopMatchType.NOT_MATCH, ''),

        # Regular string stop words - WHOLE match
        ('hello', ['hello'], StopMatchType.WHOLE, 'hello'),
        ('stop', ['hello', 'stop', 'world'], StopMatchType.WHOLE, 'stop'),

        # Regular string stop words - PREFIX match
        ('hell', ['hello'], StopMatchType.PREFIX, ''),
        ('st', ['hello', 'stop', 'world'], StopMatchType.PREFIX, ''),

        # Regular string stop words - NOT_MATCH
        ('world', ['hello', 'stop'], StopMatchType.NOT_MATCH, ''),
        ('prefix', ['hello'], StopMatchType.NOT_MATCH, ''),

        # Regex stop words - WHOLE match
        ('code```', ['r/```$/'], StopMatchType.WHOLE, '```'),
        ('test123', ['r/\\d+$/'], StopMatchType.WHOLE, '123'),
        ('hello world', ['r/world$/'], StopMatchType.WHOLE, 'world'),

        # Regex stop words - PREFIX match
        ('code``', ['r/```$/'], StopMatchType.PREFIX, ''),
        ('test12', ['r/\\d{3}$/'], StopMatchType.PREFIX, ''),
        ('hello wor', ['r/world$/'], StopMatchType.PREFIX, ''),

        # Regex stop words - NOT_MATCH
        ('hello', ['r/world$/'], StopMatchType.NOT_MATCH, ''),
        ('test', ['r/\\d{3}$/'], StopMatchType.NOT_MATCH, ''),
        ('world prefix', ['r/world$/'], StopMatchType.NOT_MATCH, ''),

        # Mixed regex and regular stop words
        ('hello', ['r/world$/', 'hello', 'r/\\d+$/'], StopMatchType.WHOLE, 'hello'),
        ('test123', ['hello', 'r/\\d+$/', 'world'], StopMatchType.WHOLE, '123'),
        ('hell', ['r/world$/', 'hello', 'r/\\d+$/'], StopMatchType.PREFIX, ''),
        ('test12', ['hello', 'r/\\d{3}$/', 'world'], StopMatchType.PREFIX, ''),

        # Invalid regex patterns (treated as regular strings)
        ('r/', ['r/'], StopMatchType.WHOLE, 'r/'),
        ('r//', ['r//'], StopMatchType.WHOLE, 'r//'),
        ('r/invalid', ['r/invalid'], StopMatchType.WHOLE, 'r/invalid'),

        # Edge cases with regex-like strings that aren't valid regex patterns
        ('r/test', ['r/test'], StopMatchType.WHOLE, 'r/test'),  # Missing closing /
        ('r/', ['r/'], StopMatchType.WHOLE, 'r/'),  # Too short
    ]

    for text, stops, expected_match_type, expected_stop in testcases:
        match_type, matched_stop = get_stop_match_type(text, stops)
        assert match_type == expected_match_type, f"Failed for text='{text}', stops={stops}: expected match_type {expected_match_type}, got {match_type}"
        assert matched_stop == expected_stop, f"Failed for text='{text}', stops={stops}: expected stop '{expected_stop}', got '{matched_stop}'"
