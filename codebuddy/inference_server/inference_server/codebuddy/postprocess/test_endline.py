from .endline import trim_last_word, trim_last_line
'''
pytest -vv  -s pkg/codebuddy/postprocess -k 'trim'
'''


def test_trim_last_word():
    testcases = [
        ('hello wor', ''),
        ('hello\n wor', 'wor'),
        ('hello\n aaa.wo', 'wo'),
        ('hello\n addaa.', ''),
    ]
    for tc in testcases:
        result = trim_last_word(tc[0], 10, 10)
        assert result + tc[1] == tc[0]


def test_trim_last_line():
    testcases = [
        ('hello wor', ''),
        ('hello\n wor', ' wor'),
        ('hello\n aaa.wo', ' aaa.wo'),
        ('hello\n addaa.', ' addaa.'),
        ('hello\n addaa.\n', ''),
    ]
    for tc in testcases:
        result = trim_last_line(tc[0], 10, 10)
        assert result + tc[1] == tc[0]
