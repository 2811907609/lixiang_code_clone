from inference_server.backend.models.fulledit_utils import extract_draft_from_prompt


def test_extract_draft_from_prompt_with_match():
    """测试能够匹配可编辑区域的情况"""
    input_text = "Some text before <|editable_region_start|>editable content<|editable_region_end|> some text after"
    expected = "<|editable_region_start|>editable content<|editable_region_end|>"
    result = extract_draft_from_prompt(input_text)
    assert result == expected


def test_extract_draft_from_prompt_without_match():
    """测试没有可编辑区域的情况"""
    input_text = "Some text without editable region markers"
    expected = ""
    result = extract_draft_from_prompt(input_text)
    assert result == expected


def test_extract_draft_from_prompt_with_multiple_regions():
    """测试有多个可编辑区域的情况，应该返回第一个匹配"""
    input_text = "Text before <|editable_region_start|>first content<|editable_region_end|> middle <|editable_region_start|>second content<|editable_region_end|> end"
    expected = "<|editable_region_start|>first content<|editable_region_end|>"
    result = extract_draft_from_prompt(input_text)
    assert result == expected


def test_extract_draft_from_prompt_with_empty_content():
    """测试可编辑区域内容为空的情况"""
    input_text = "Before <|editable_region_start|><|editable_region_end|> after"
    expected = "<|editable_region_start|><|editable_region_end|>"
    result = extract_draft_from_prompt(input_text)
    assert result == expected
def test_extract_draft_from_prompt_with_multiline_content():
    """测试多行字符串的情况"""
    input_text = """Some text before
<|editable_region_start|>
def example_function():
    print("This is a multiline string")
    return True
<|editable_region_end|>
Some text after"""
    expected = """<|editable_region_start|>
def example_function():
    print("This is a multiline string")
    return True
<|editable_region_end|>"""
    result = extract_draft_from_prompt(input_text)
    assert result == expected
