'''
pytest -vv  -s pkg/testhelper/ -k 'test_gen'
'''

from .random_words import generate_random_text


def test_generate_random_text():
    testcases = [
        [1, 1],
        [1000, 1],
        [1007, 100],
        [1007, 13],
    ]

    for tc in testcases:
        s = generate_random_text(tc[0], tc[1])
        assert len(s) == tc[0]
        assert len(s.split('\n')) == tc[1]
