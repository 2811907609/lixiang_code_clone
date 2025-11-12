'''
pytest -vv  -s inference_server/codebuddy/postprocess -k 'test_remove_markdown_code_blocks'
'''

from inference_server.types import CompletionItem

from .fix_markdown import remove_markdown_code_blocks
from .test_utils import new_completion_item, not_changed_symbol, run_testcases


def assure_result(fn, item: CompletionItem, completion: str, expected: str):
    item.set_output(completion)
    fn(item)
    assert item.output_text() == expected


def test_remove_markdown_code_blocks_basic():
    # 测试带语言标识的代码块（多行）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```python
    print("Hello, World!")
    return True
```'''
    expected = '''    print("Hello, World!")\n    return True\n'''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_no_language():
    # 测试不带语言标识的代码块（多行）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```
print("Hello, World!")
return True
```'''
    expected = '''print("Hello, World!")\nreturn True\n'''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_no_code_blocks():
    # 测试没有代码块的情况（多行）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''    print("Hello, World!")
    return True'''
    expected = '''    print("Hello, World!")\n    return True'''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_empty_output():
    # 测试空输出的情况
    item = new_completion_item('''
def hello():
    ║
''')
    completion = ''
    expected = ''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_only_opening():
    # 测试只有开头标记没有结尾标记（多行）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```python
print("Hello, World!")
return True'''
    expected = '''print("Hello, World!")\nreturn True'''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_only_closing():
    # 测试只有结尾标记没有开头标记（多行）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''print("Hello, World!")
return True
```'''
    expected = '''print("Hello, World!")\nreturn True\n'''
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_single_line():
    # 测试单行代码（从代码块中提取后仍带有换行符）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```python
return True
```'''
    expected = 'return True\n'
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_whitespace_variations():
    # 测试不同空白字符的情况（从代码块中提取后仍带有换行符）
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```  python
    print("Hello")
```'''
    expected = '    print("Hello")\n'
    assure_result(remove_markdown_code_blocks, item, completion, expected)


def test_remove_markdown_code_blocks_fix_kinds_tracking():
    # 测试 fixed_kinds 跟踪
    item = new_completion_item('''
def hello():
    ║
''')
    completion = '''```python
print("Hello")
```'''

    item.set_output(completion)
    assert len(item.fixed_kinds) == 0

    remove_markdown_code_blocks(item)

    assert len(item.fixed_kinds) == 1
    assert remove_markdown_code_blocks.__name__ in item.fixed_kinds


def test_remove_markdown_code_blocks_multiple_cases():
    # 使用 run_testcases 工具函数测试多个案例
    testcases = [
        ('带语言标识的代码块', '''
def hello():
    ║
''', '''```python
    print("Hello")
    return True
```''', '''    print("Hello")\n    return True\n'''),

        ('不带语言标识的代码块', '''
def hello():
    ║
''', '''```
print("Hello")
return True
```''', '''print("Hello")\nreturn True\n'''),

        ('没有代码块', '''
def hello():
    ║
''', '''    print("Hello")
    return True''', not_changed_symbol),

        ('空输出', '''
def hello():
    ║
''', '', ''),

        ('单行代码', '''
def hello():
    ║
''', '''```js
console.log("Hello");
```''', 'console.log("Hello");\n'),
    ]

    run_testcases(testcases, remove_markdown_code_blocks)
