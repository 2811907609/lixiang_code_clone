from .prompt_fim import (
    split_rag_prefix_lines,
    trim_head_lines,
    trim_tail_lines,
)


def test_split_rag_prefix():
    testcases = [
        # lang, whole_prefix, rag_lines, prefix_lines
        ('', '', [], ['']),
        ('python', '# rag1', ['# rag1'], []),
        ('python', '# rag1\n', ['# rag1'], ['']),
        ('python', '# rag1\n# rag2\np1\np2', ['# rag1', '# rag2'], ['p1',
                                                                    'p2']),
        (
            'python',
            '# rag1\n# rag2\np1\np2\n',
            ['# rag1', '# rag2'],
            ['p1', 'p2', ''],
        ),
        ('go', 'func init', [], ['func init']),
    ]
    for i, c in enumerate(testcases):
        lang = c[0]
        prefix = c[1]
        rag_lines, prefix_lines = split_rag_prefix_lines(lang, prefix)
        assert (rag_lines == c[2]
               ), f'testcase {i} failed: {c} != {rag_lines, prefix_lines}'
        assert (prefix_lines == c[3]
               ), f'testcase {i} failed: {c} != {rag_lines, prefix_lines}'


def test_trim_head_lines():
    testcases = [
        # lines, max_length, expected
        ([], 2, ''),
        (['a', 'b', 'c'], 2, 'c'),
        (['a', 'b', 'c'], 20, 'a\nb\nc'),
        (['a', 'bb', 'cc'], 4, 'cc'),
        (['aaa', 'bb', 'cc'], 6, 'bb\ncc'),
        (['aaa', 'bb', 'cccccc'], 4, ''),
    ]
    for i, c in enumerate(testcases):
        lines, max_length, expected = c
        result = trim_head_lines(lines, max_length)
        assert result == expected, f'testcase {i} failed: {c} != {result}'


def test_trim_tail_lines():
    testcases = [
        # lines, max_length, expected
        ([], 2, ''),
        (['a', 'b', 'c'], 2, 'a'),
        (['a', 'b', 'c'], 20, 'a\nb\nc'),
        (['a', 'bb', 'cc'], 5, 'a\nbb'),
        (['aaa', 'bb', 'cc'], 4, 'aaa'),
        (['aaa', 'bb', 'cc'], 7, 'aaa\nbb'),
        (['aaaaaaa', 'bb', 'c'], 4, ''),
    ]
    for i, c in enumerate(testcases):
        lines, max_length, expected = c
        result = trim_tail_lines(lines, max_length)
        assert result == expected, f'testcase {i} failed: {c} != {result}'
