import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from code_complete import BaseModel


def test_base_model():
    b = BaseModel()
    assert b.gen_prompt_header('python') == '# this is python code\n\n'
    assert b.gen_prompt_header('not_supported_lang') == ''

    class M1(BaseModel):

        def gen_prompt_header(self, lang: str) -> str:
            return f'// this is M1, {lang}'

    m1 = M1()
    assert m1.gen_prompt_header('python') == '// this is M1, python'

    class M2(BaseModel):
        pass

    m2 = M2()
    assert m2.gen_prompt_header('python') == '# this is python code\n\n'
    assert m2.gen_prompt_header('not_supported_lang') == ''
