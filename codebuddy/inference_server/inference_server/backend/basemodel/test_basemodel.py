
import random
from dataclasses import dataclass

from inference_server.backend.basemodel import BaseModel

words_list = [
    '\t', '.', 'a', 'apple', 'banana', 'cherry', 'date', 'elderberry', 'fig',
    'grape', 'honeydew'
]


def generate_random_words(n, m):
    result = []

    for _ in range(m):  # Generating M lines
        line = ' '.join(random.choice(words_list)
                        for _ in range(n))  # Generating N words per line
        result.append(line)

    return '\n'.join(result)


def test_gen_prompt():

    @dataclass
    class TestCase:
        lang: str
        prompt: str
        suffix: str

        expected_prompt: str
        expected_rag: str
        expected_prefix: str
        expected_suffix: str

    class MyModel(BaseModel):

        def fim_prompt(self, prefix, suffix, lang=None):
            if not suffix:
                return prefix
            return f'{prefix}<FILL_ME>{suffix}'

    testcases = [
        TestCase('', '', '', '', '', '', ''),
        TestCase('', 'package', '', 'package', '', 'package', ''),
        TestCase('', 'package\n\t\n', '', 'package\n\t\n', '', 'package\n\t\n',
                 ''),
        TestCase('', 'package\n\t\n', 'suffix', 'package\n\t\n<FILL_ME>suffix',
                 '', 'package\n\t\n', 'suffix'),
    ]

    m = MyModel()
    for tc in testcases:
        prompt, stat = m.gen_prompt(tc.lang, tc.prompt, tc.suffix)
        assert prompt == tc.expected_prompt, 'prompt wrong'
        assert stat.used_rag == tc.expected_rag, 'rag wrong'
        assert stat.used_prefix == tc.expected_prefix, 'prefix wrong'
        assert stat.used_suffix == tc.expected_suffix, 'suffix wrong'
