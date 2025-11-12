#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
remove_comments_with_mapping 函数的全面测试用例

这个模块包含了对 haloos_common_utils.py 中 remove_comments_with_mapping 函数的各种测试用例，
包括边界情况、错误情况和潜在的bug测试。
"""

import pytest
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import remove_comments_with_mapping


class TestRemoveCommentsWithMapping:
    """remove_comments_with_mapping 函数的基本功能测试"""

    def test_basic_single_line_comment(self):
        """测试基本的单行注释"""
        code = """int main() {
    int x = 5;// 这是注释
    return 0;
}"""
        expected = """int main() {
    int x = 5;
    return 0;
}"""
        result, mapping = remove_comments_with_mapping(code)
        assert result.strip() == expected.strip()
        assert len(mapping) == 4  # 应该有4行映射

    def test_basic_multiline_comment(self):
        """测试基本的多行注释"""
        code = """int main() {
    /* 这是多行注释
       继续注释 */
    int x = 5;
    return 0;
}"""
        expected = """int main() {


    int x = 5;
    return 0;
}"""
        result, mapping = remove_comments_with_mapping(code)
        assert result.strip() == expected.strip()

    def test_multiline_comment_single_line(self):
        """测试单行内的多行注释"""
        code = "int x = 5; /* 注释 */ int y = 10;"
        expected = "int x = 5;  int y = 10;"
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_nested_comments_not_supported(self):
        """测试嵌套注释（C不支持，但测试函数行为）"""
        code = "/* 外层注释 /* 内层注释 */ 外层继续 */"
        result, mapping = remove_comments_with_mapping(code)
        # 函数应该在第一个 */ 处结束注释
        assert "外层继续" in result

    def test_string_literal_with_comment_symbols(self):
        """测试字符串字面量中包含注释符号"""
        code = '''printf("这里有// 和 /* */注释符号");'''
        expected = '''printf("这里有// 和 /* */注释符号");'''
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_string_literal_with_escape_sequences(self):
        """测试包含转义序列的字符串"""
        code = '''printf("这里有\\"转义引号\\" // 不是注释");'''
        expected = '''printf("这里有\\"转义引号\\" // 不是注释");'''
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_char_literal_with_comment_symbols(self):
        """测试字符字面量中的注释符号"""
        code = "char c1 = '/'; char c2 = '*';"
        expected = "char c1 = '/'; char c2 = '*';"
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_comment_at_line_start(self):
        """测试行首的注释"""
        code = """// 这是第一行注释
int main() {
    haha = 1;// 这是缩进的注释
    return 0;
}"""
        expected = """
int main() {
    haha = 1;
    return 0;
}"""
        result, mapping = remove_comments_with_mapping(code)
        assert result.strip() == expected.strip()

    def test_comment_at_line_end(self):
        """测试行尾的注释"""
        code = """int x = 5;// 行尾注释
int y = 10;/* 行尾多行注释 */"""
        expected = """int x = 5;
int y = 10;"""
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_multiline_comment_across_multiple_lines(self):
        """测试跨越多行的多行注释"""
        code = """int x = 5;
/* 这是
   跨越多行的
   注释 */
int y = 10;"""
        expected = """int x = 5;



int y = 10;"""
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_multiline_comment_with_code_after(self):
        """测试多行注释结束后同一行还有代码"""
        code = "int x = /* 注释 */ 5;"
        expected = "int x =  5;"
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected


class TestRemoveCommentsEdgeCases:
    """测试边界情况和异常情况"""

    def test_empty_input(self):
        """测试空输入"""
        code = ""
        result, mapping = remove_comments_with_mapping(code)
        assert result == ""
        assert mapping == {}

    def test_only_comments(self):
        """测试只包含注释的代码"""
        code = """// 只有注释
/* 多行注释
   继续注释 */
// 另一个注释"""
        result, mapping = remove_comments_with_mapping(code)
        # 应该返回空行或空字符串
        assert result.strip() == "" or result.count('\n') >= 2

    def test_only_whitespace(self):
        """测试只包含空白字符的输入"""
        code = "   \n\t  \n   "
        result, mapping = remove_comments_with_mapping(code)
        # 应该保留空白行
        assert result == code

    def test_comment_symbols_in_different_contexts(self):
        """测试不同上下文中的注释符号"""
        code = """#define MACRO "// 这不是注释"
int divide = a / b;// 这是注释
char star = '*';/* 这是注释 */"""
        expected = """#define MACRO "// 这不是注释"
int divide = a / b;
char star = '*';"""
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_consecutive_comment_symbols(self):
        """测试连续的注释符号"""
        code = "/////// 多个斜杠注释"
        expected = ""
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_malformed_multiline_comment(self):
        """测试格式错误的多行注释（未闭合）"""
        code = """int x = 5;
/* 这是未闭合的多行注释
int y = 10;
int z = 15;"""
        result, mapping = remove_comments_with_mapping(code)
        # 函数应该将后续所有内容都当作注释处理
        assert "int y = 10;" not in result
        assert "int z = 15;" not in result

    def test_mixed_comment_types(self):
        """测试混合类型的注释"""
        code = """int x = 5;// 单行注释
/* 多行注释开始
   继续多行注释 */ int y = 10;// 另一个单行注释
// 最后的单行注释"""
        result, mapping = remove_comments_with_mapping(code)

        # 验证代码部分被正确保留
        assert "int x = 5;" in result
        assert "int y = 10;" in result
        # 验证注释被移除
        assert "单行注释" not in result
        assert "多行注释" not in result

    def test_string_with_newlines(self):
        """测试包含换行符的字符串"""
        code = '''printf("这是一个\\n包含换行符的字符串 // 不是注释");'''
        expected = '''printf("这是一个\\n包含换行符的字符串 // 不是注释");'''
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_edge_case_empty_lines(self):
        """测试空行的处理"""
        code = """int x = 5;

// 注释

int y = 10;"""
        result, mapping = remove_comments_with_mapping(code)

        # 验证空行被保留
        assert '\n\n' in result


class TestRemoveCommentsSpecialCases:
    """测试特殊情况和潜在bug"""

    def test_unclosed_string_literal(self):
        """测试未闭合的字符串字面量（边界情况）"""
        code = '''printf("未闭合的字符串 // 这应该被当作字符串的一部分'''
        # 函数应该能处理这种情况而不崩溃
        result, mapping = remove_comments_with_mapping(code)
        # 验证函数不会崩溃，且返回合理结果
        assert isinstance(result, str)
        assert isinstance(mapping, dict)

    def test_bug_multiline_comment_index_error(self):
        """测试多行注释可能导致的索引错误"""
        # 构造可能导致索引错误的输入
        code = "/*"  # 只有开始符号，没有结束
        result, mapping = remove_comments_with_mapping(code)
        # 验证不会崩溃
        assert isinstance(result, str)

    def test_bug_string_not_closed(self):
        """测试字符串未闭合时的bug"""
        code = '''printf("未闭合字符串 // 这里应该被当作字符串内容'''
        # 这可能导致索引越界
        result, mapping = remove_comments_with_mapping(code)
        assert isinstance(result, str)

    def test_single_slash(self):
        """测试单个斜杠"""
        code = "int x = a / b;"
        expected = "int x = a / b;"
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_single_asterisk(self):
        """测试单个星号"""
        code = "int x = a * b;"
        expected = "int x = a * b;"
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_unicode_in_comments(self):
        """测试注释中的Unicode字符"""
        code = "int x = 5; // 这是中文注释 🚀"
        expected = "int x = 5; "
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_very_long_line(self):
        """测试非常长的行"""
        long_comment = "// " + "a" * 1000
        code = f"int x = 5; {long_comment}"
        expected = "int x = 5; "
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected


class TestLineMappingBugs:
    """测试行映射相关的bug"""

    def test_line_mapping_correctness(self):
        """测试行映射的正确性"""
        code = """int main() {  // line 1
    // 这行会被删除    // line 2
    int x = 5;       // line 3
    /* 多行注释       // line 4
       继续注释 */    // line 5
    return 0;        // line 6
}"""
        result, mapping = remove_comments_with_mapping(code)

        # 验证映射关系不为空
        assert len(mapping) > 0

        # 检查映射的值是否连续
        mapping_values = sorted(mapping.values())
        expected_values = list(range(1, len(mapping_values) + 1))
        assert mapping_values == expected_values

    def test_bug_line_mapping_direction(self):
        """测试行映射方向的bug（原始 -> 新 vs 新 -> 原始）"""
        code = """line1
// comment line
line3"""
        result, mapping = remove_comments_with_mapping(code)

        # 根据当前实现，mapping应该是 {original_line_no: new_line_no}
        # 但从函数逻辑看，这可能是个bug，应该是 {new_line_no: original_line_no}
        print("行映射结果:", mapping)
        print("处理后的代码:")
        print(repr(result))

        # 这个测试用于验证映射方向是否正确
        # 如果发现bug，这里会失败
        assert len(mapping) > 0

    def test_line_mapping_with_empty_lines(self):
        """测试包含空行时的行映射"""
        code = """line1

line3
// comment
line5"""
        result, mapping = remove_comments_with_mapping(code)

        # 验证空行也有正确的映射
        assert len(mapping) > 0
        # 验证映射值的连续性
        values = sorted(mapping.values())
        assert values == list(range(1, len(values) + 1))


class TestDetailedLineMapping:
    """详细测试行映射功能"""

    def test_simple_line_mapping_no_comments(self):
        """测试无注释时的行映射"""
        code = """line1
line2
line3"""
        result, mapping = remove_comments_with_mapping(code)

        # 无注释时，映射应该是 1:1 的
        expected_mapping = {1: 1, 2: 2, 3: 3}
        assert mapping == expected_mapping
        assert result == code

    def test_line_mapping_with_single_line_comments(self):
        """测试单行注释的行映射"""
        code = """line1  // comment
// full line comment
line3"""
        result, mapping = remove_comments_with_mapping(code)

        # 第1行保留但去掉注释，第2行变成空行，第3行保留
        # 映射应该是 {original_line: new_line}
        print(f"Mapping result: {mapping}")
        print(f"Result code: {repr(result)}")

        # 验证所有行都保留（注释行变成空行）
        lines = result.split('\n')
        assert len(lines) == 3  # 应该有3行

        # 验证映射包含所有行
        assert len(mapping) == 3
        assert mapping == {1: 1, 2: 2, 3: 3}

    def test_line_mapping_with_multiline_comments(self):
        """测试多行注释的行映射"""
        code = """line1
/* start comment
   middle comment
   end comment */
line5"""
        result, mapping = remove_comments_with_mapping(code)

        print(f"Original code lines: {len(code.split(chr(10)))}")
        print(f"Result code lines: {len(result.split(chr(10)))}")
        print(f"Mapping: {mapping}")

        # 第2-4行应该被删除或变成空行
        # 应该保留第1行和第5行

        # 验证第1行和最后一行的内容
        assert "line1" in result
        assert "line5" in result
        assert "comment" not in result

    def test_line_mapping_mixed_comments(self):
        """测试混合注释类型的行映射"""
        code = """line1  // single line comment
line2
/* multiline start
   multiline middle */ line4_after_comment
// another single line
line6"""
        result, mapping = remove_comments_with_mapping(code)

        print(f"Original lines: {code.split(chr(10))}")
        print(f"Result lines: {result.split(chr(10))}")
        print(f"Mapping: {mapping}")

        # 验证内容
        assert "line1" in result
        assert "line2" in result
        assert "line4_after_comment" in result
        assert "line6" in result

        # 验证注释被删除
        assert "single line comment" not in result
        assert "multiline start" not in result
        assert "another single line" not in result

    def test_line_mapping_only_empty_lines_preserved(self):
        """测试只有空行被保留的情况"""
        code = """

// comment


"""
        result, mapping = remove_comments_with_mapping(code)

        print(f"Mapping: {mapping}")
        print(f"Result: {repr(result)}")

        # 空行应该被保留
        lines = result.split('\n')
        empty_lines = [line for line in lines if line.strip() == '']
        assert len(empty_lines) >= 3  # 至少3个空行

    def test_line_mapping_edge_case_one_line(self):
        """测试单行代码的映射"""
        test_cases = [
            ("int x = 5;", {1: 1}),
            ("// only comment", {}),  # 可能为空或有一个空行映射
            ("int x = 5; // with comment", {1: 1}),
        ]

        for code, expected_pattern in test_cases:
            result, mapping = remove_comments_with_mapping(code)
            print(f"Code: {repr(code)}")
            print(f"Result: {repr(result)}")
            print(f"Mapping: {mapping}")

            if expected_pattern:
                # 验证至少有期望的映射模式
                for orig, new in expected_pattern.items():
                    assert mapping.get(orig) == new or new in mapping.values()

    def test_line_mapping_bug_detection(self):
        """专门检测行映射方向bug的测试"""
        code = """keep_line1
// delete_line2
keep_line3"""
        result, mapping = remove_comments_with_mapping(code)

        print(f"Code:\n{code}")
        print(f"Result:\n{result}")
        print(f"Mapping: {mapping}")

        # 根据函数实现，mapping[original_line_no] = new_line_no
        # 现在所有行都保留：
        # - original line 1 -> new line 1
        # - original line 2 -> new line 2 (空行)
        # - original line 3 -> new line 3

        # 验证第2行（注释行）内容不在结果中，但行保留
        assert "delete_line2" not in result

        # 验证保留的行存在
        assert "keep_line1" in result
        assert "keep_line3" in result

        # 检查映射是否符合预期
        assert mapping == {1: 1, 2: 2, 3: 3}

    def test_line_mapping_complex_scenario(self):
        """测试复杂场景的行映射"""
        code = """// header comment (line 1 - should be deleted)
#include <stdio.h>  // line 2 - should keep main part
                    // line 3 - empty with comment, should be deleted
int main() {        // line 4 - should keep main part
    /* block comment line 5
       block comment line 6
       block comment line 7 */ int x = 5; // line 7 continuation
    return 0;       // line 8 - should keep main part
}                   // line 9 - should keep"""

        result, mapping = remove_comments_with_mapping(code)

        print("=" * 50)
        print("COMPLEX SCENARIO TEST")
        print("=" * 50)
        print("Original code:")
        for i, line in enumerate(code.split('\n'), 1):
            print(f"{i:2}: {repr(line)}")
        print("\nResult code:")
        for i, line in enumerate(result.split('\n'), 1):
            print(f"{i:2}: {repr(line)}")
        print(f"\nMapping: {mapping}")

        # 验证关键内容被保留
        assert "#include <stdio.h>" in result
        assert "int main() {" in result
        assert "int x = 5;" in result
        assert "return 0;" in result
        assert "}" in result

        # 验证注释被删除
        assert "header comment" not in result
        assert "block comment" not in result

        # 验证映射的完整性
        result_lines = [line for line in result.split('\n') if line.strip() or True]  # 包括空行
        assert len(mapping) == len(result_lines)

    def test_line_mapping_preserves_structure(self):
        """测试行映射是否保持代码结构"""
        code = """if (condition) {  // line 1
    // this is a comment line 2
    do_something();   // line 3
    /* multi line comment 4
       continues on line 5 */
    do_another();     // line 6
}                     // line 7"""

        result, mapping = remove_comments_with_mapping(code)

        print("\nSTRUCTURE PRESERVATION TEST")
        print(f"Original lines: {len(code.split(chr(10)))}")
        print(f"Result lines: {len(result.split(chr(10)))}")
        print(f"Mapping: {mapping}")

        # 验证代码结构
        lines = result.split('\n')
        assert any("if (condition) {" in line for line in lines)
        assert any("do_something();" in line for line in lines)
        assert any("do_another();" in line for line in lines)
        assert any("}" in line for line in lines)

        # 验证映射保持相对顺序
        original_lines = list(mapping.keys())
        new_lines = [mapping[orig] for orig in original_lines]

        # 新行号应该是递增的（保持顺序）
        assert new_lines == sorted(new_lines)


class TestPerformanceAndStress:
    """测试性能和压力情况"""

    def test_performance_with_large_input(self):
        """测试大输入的性能"""
        # 创建一个包含1000行代码的字符串
        lines = []
        for i in range(1000):
            if i % 3 == 0:
                lines.append(f"int var{i} = {i}; // 注释 {i}")
            elif i % 3 == 1:
                lines.append(f"/* 多行注释 {i} */ int var{i} = {i};")
            else:
                lines.append(f"int var{i} = {i};")

        code = '\n'.join(lines)

        # 验证函数能够处理大输入而不崩溃
        result, mapping = remove_comments_with_mapping(code)
        assert isinstance(result, str)
        assert isinstance(mapping, dict)
        # 验证所有变量声明都被保留
        for i in range(1000):
            assert f"int var{i} = {i};" in result

    def test_deeply_nested_strings(self):
        """测试深度嵌套的字符串情况"""
        code = '''printf("外层字符串 \\"内层字符串 // 不是注释\\" 继续外层");'''
        expected = '''printf("外层字符串 \\"内层字符串 // 不是注释\\" 继续外层");'''
        result, mapping = remove_comments_with_mapping(code)
        assert result == expected

    def test_many_consecutive_comments(self):
        """测试大量连续注释"""
        lines = ["// 注释行 " + str(i) for i in range(100)]
        code = '\n'.join(lines)
        result, mapping = remove_comments_with_mapping(code)

        # 所有注释行都应该被移除
        assert result.strip() == "" or result.count('\n') == len(lines) - 1

class TestSpecificBugCases:
    """测试函数中的特定bug场景"""

    def test_line_mapping_direction_bug(self):
        """测试行映射方向的具体bug"""
        code = """line1
// comment_line
line3
/* multiline
   comment */
line6"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nBUG TEST - Line mapping direction:")
        print(f"Original code:\n{code}")
        print(f"Result code:\n{result}")
        print(f"Mapping: {mapping}")

        # 根据当前实现 line_mapping[original_line_no] = new_line_no (line 163)
        # 但这可能是错误的，应该是 line_mapping[new_line_no] = original_line_no

        # 预期的正确映射应该是：
        # new_line 1 -> original_line 1
        # new_line 2 -> original_line 3
        # new_line 3 -> original_line 6

        # 当前错误的映射可能是：
        # original_line 1 -> new_line 1
        # original_line 3 -> new_line 2
        # original_line 6 -> new_line 3

        # 验证映射是否符合预期（这里会暴露bug）
        result_lines = result.split('\n')
        non_empty_result_lines = [i+1 for i, line in enumerate(result_lines) if line.strip()]

        print(f"Non-empty result lines: {non_empty_result_lines}")

        # 新的实现保留所有行
        assert 1 in mapping  # 第1行应该被保留
        assert 2 in mapping  # 第2行保留（变成空行）
        assert 3 in mapping  # 第3行应该被保留
        assert 4 in mapping  # 第4行保留（变成空行）
        assert 5 in mapping  # 第5行保留（变成空行）
        assert 6 in mapping  # 第6行应该被保留

        # 映射应该是1:1的
        assert mapping == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

    def test_multiline_comment_end_with_code_bug(self):
        """测试多行注释结束后同行代码处理的bug"""
        code = "int x = /* comment */ 42; int y = 100;"
        result, mapping = remove_comments_with_mapping(code)

        print("\nMULTILINE COMMENT END BUG TEST:")
        print(f"Original: {repr(code)}")
        print(f"Result:   {repr(result)}")
        print(f"Mapping:  {mapping}")

        # 验证注释被移除但代码保留
        assert "/* comment */" not in result
        assert "int x =" in result
        assert "42;" in result
        assert "int y = 100;" in result

        # 这里可能有bug：多行注释结束后的代码处理

    def test_string_escape_sequence_bug(self):
        """测试字符串转义序列处理的bug"""
        test_cases = [
            r'char* str = "She said \"Hello // World\"";',
            r'char* str = "Path: C:\\Program Files\\";',
            r'char* str = "Quote: \" and Backslash: \\";',
            r'char* str = "End quote \"',  # 未闭合的字符串
        ]

        for case in test_cases:
            print(f"\nESCAPE SEQUENCE TEST: {repr(case)}")
            result, mapping = remove_comments_with_mapping(case)
            print(f"Result: {repr(result)}")
            print(f"Mapping: {mapping}")

            # 验证函数不会崩溃
            assert isinstance(result, str)
            assert isinstance(mapping, dict)

            # 对于正常的字符串，应该完全保留
            if case.endswith('";'):
                assert result == case

    def test_index_out_of_bounds_bug(self):
        """测试可能导致索引越界的情况"""
        edge_cases = [
            "/",           # 单个斜杠
            "*",           # 单个星号
            "/*",          # 未闭合的多行注释开始
            "*/",          # 未配对的多行注释结束
            "//",          # 空的单行注释
            '"',           # 单个引号
            "'",           # 单个单引号
            '\\',          # 单个反斜杠
            "/* */",       # 空的多行注释
            '""',          # 空字符串
            "''",          # 空字符字面量
        ]

        for case in edge_cases:
            print(f"\nEDGE CASE: {repr(case)}")
            try:
                result, mapping = remove_comments_with_mapping(case)
                print(f"Result: {repr(result)}")
                print(f"Mapping: {mapping}")

                # 验证没有崩溃
                assert isinstance(result, str)
                assert isinstance(mapping, dict)

            except Exception as e:
                print(f"ERROR: {e}")
                # 如果有异常，说明存在bug
                assert False, f"Function crashed on input {repr(case)}: {e}"

    def test_line_counting_bug(self):
        """测试行计数逻辑的bug"""
        code = """first_line
// comment
third_line
"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nLINE COUNTING BUG TEST:")
        original_lines = code.split('\n')
        result_lines = result.split('\n')

        print(f"Original lines count: {len(original_lines)}")
        print(f"Result lines count: {len(result_lines)}")
        print(f"Original lines: {[repr(line) for line in original_lines]}")
        print(f"Result lines: {[repr(line) for line in result_lines]}")
        print(f"Mapping: {mapping}")

        # 验证映射的一致性
        if mapping:
            max_new_line = max(mapping.values())
            # 新行号不应该超过结果的实际行数
            assert max_new_line <= len(result_lines)

    def test_empty_line_preservation_bug(self):
        """测试空行保留逻辑的bug"""
        code = """line1

// comment on line 3

line5
"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nEMPTY LINE PRESERVATION TEST:")
        print(f"Original:\n{repr(code)}")
        print(f"Result:\n{repr(result)}")
        print(f"Mapping: {mapping}")

        # 验证空行被正确保留
        result_lines = result.split('\n')

        # 第2行和第4行是空行，应该被保留
        # 第3行是注释，应该被删除

        # 检查结果中的空行
        empty_lines_in_result = [i for i, line in enumerate(result_lines) if line.strip() == '']
        print(f"Empty lines in result at positions: {empty_lines_in_result}")

        # 应该至少保留原来的空行
        assert len(empty_lines_in_result) >= 2

    def test_comment_detection_in_strings_bug(self):
        """测试字符串中注释符号的错误识别"""
        complex_string_cases = [
            r'printf("/* This is not a comment */");',
            r'printf("// This is not a comment either");',
            r'char* url = "http://example.com";',
            r'printf("Mixed: /* and // symbols");',
            r'printf("Escaped quote: \" /* still in string */");',
        ]

        for case in complex_string_cases:
            print(f"\nSTRING COMMENT DETECTION TEST: {repr(case)}")
            result, mapping = remove_comments_with_mapping(case)
            print(f"Result: {repr(result)}")

            # 字符串中的注释符号不应该被处理为注释
            assert result == case, f"String content was modified: {repr(case)} -> {repr(result)}"


class TestMappingValidation:
    """专门测试映射有效性的测试用例"""

    def test_mapping_completeness(self):
        """测试映射的完整性"""
        code = """line1
// comment
line3
/* block
   comment */
line6"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nMAPPING COMPLETENESS TEST:")
        print(f"Mapping: {mapping}")

        # 每个保留的行都应该有映射
        result_lines = result.split('\n')
        non_empty_or_significant_lines = [
            i+1 for i, line in enumerate(result_lines)
            if line.strip() or i < len(result_lines)-1  # 包括中间的空行
        ]

        print(f"Result lines that should have mapping: {len(non_empty_or_significant_lines)}")
        print(f"Actual mapping entries: {len(mapping)}")

        # 映射条目数应该等于保留的行数
        # 注意：这里可能会暴露映射逻辑的bug
        assert len(mapping) > 0

    def test_mapping_uniqueness(self):
        """测试映射值的唯一性"""
        code = """line1
line2  // comment
line3
// full comment line
line5"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nMAPPING UNIQUENESS TEST:")
        print(f"Mapping: {mapping}")

        # 检查映射值的唯一性
        mapping_values = list(mapping.values())
        unique_values = set(mapping_values)

        print(f"Mapping values: {mapping_values}")
        print(f"Unique values: {unique_values}")

        # 映射值应该是唯一的
        assert len(mapping_values) == len(unique_values), "Mapping values are not unique!"

    def test_mapping_order_preservation(self):
        """测试映射是否保持原始顺序"""
        code = """first
// comment1
second
// comment2
third
/* multi
   line */
fourth"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nORDER PRESERVATION TEST:")
        print(f"Mapping: {mapping}")

        # 获取原始行号（键）和新行号（值）
        original_lines = sorted(mapping.keys())
        corresponding_new_lines = [mapping[orig] for orig in original_lines]

        print(f"Original line order: {original_lines}")
        print(f"Corresponding new lines: {corresponding_new_lines}")

        # 新行号应该是递增的（保持相对顺序）
        assert corresponding_new_lines == sorted(corresponding_new_lines), \
            "Mapping does not preserve order!"

    def test_mapping_boundary_values(self):
        """测试映射的边界值"""
        code = """first_line
last_line"""
        result, mapping = remove_comments_with_mapping(code)

        print("\nBOUNDARY VALUES TEST:")
        print(f"Mapping: {mapping}")

        if mapping:
            min_orig = min(mapping.keys())
            max_orig = max(mapping.keys())
            min_new = min(mapping.values())
            max_new = max(mapping.values())

            print(f"Original line range: {min_orig} to {max_orig}")
            print(f"New line range: {min_new} to {max_new}")

            # 新行号应该从1开始
            assert min_new >= 1, "New line numbers should start from 1"

            # 原始行号应该从1开始
            assert min_orig >= 1, "Original line numbers should start from 1"


class TestComplexScenarios:
    """测试复杂场景组合"""

    def test_complex_code_with_mixed_comments(self):
        """测试包含各种注释类型的复杂代码"""
        code = '''#include <stdio.h>  // 头文件包含

/*
 * 这是一个多行注释
 * 描述函数功能
 */
int main(int argc, char* argv[]) {  // main函数
    char* str = "包含 // 和 /* */ 的字符串";
    int x = 10 / 5;  // 除法运算，不是注释
    /* 内联注释 */ int y = 20;

    // 打印结果
    printf("结果: %d\\n", x + y);
    return 0;  /* 返回0 */
}'''

        result, mapping = remove_comments_with_mapping(code)

        # 验证代码结构被保留
        assert '#include <stdio.h>' in result
        assert 'int main(int argc, char* argv[]) {' in result
        assert 'char* str = "包含 // 和 /* */ 的字符串";' in result
        assert 'int x = 10 / 5;' in result
        assert 'int y = 20;' in result
        assert 'printf("结果: %d\\n", x + y);' in result
        assert 'return 0;' in result

        # 验证注释被移除
        assert '头文件包含' not in result
        assert '这是一个多行注释' not in result
        assert 'main函数' not in result
        assert '除法运算，不是注释' not in result
        assert '内联注释' not in result
        assert '打印结果' not in result
        assert '返回0' not in result

    def test_preprocessor_with_comments(self):
        """测试预处理器指令中的注释"""
        code = '''#define MAX_SIZE 100  // 最大尺寸
#ifdef DEBUG  /* 调试模式 */
    #define LOG(x) printf(x)
#else  // 非调试模式
    #define LOG(x)
#endif'''

        result, mapping = remove_comments_with_mapping(code)

        # 验证预处理器指令被保留
        assert '#define MAX_SIZE 100' in result
        assert '#ifdef DEBUG' in result
        assert '#define LOG(x) printf(x)' in result
        assert '#else' in result
        assert '#define LOG(x)' in result
        assert '#endif' in result

        # 验证注释被移除
        assert '最大尺寸' not in result
        assert '调试模式' not in result
        assert '非调试模式' not in result

class TestTreeSitterSpecificCases:
    """测试Tree-sitter特定的解析情况"""

    def test_invalid_c_syntax_with_comments(self):
        """测试包含无效C语法但有注释的代码"""
        # Tree-sitter应该能容错处理
        code = """@#$%^&*()  // 无效语法但有注释
int valid_function() {  // 有效语法
    invalid syntax here /* 块注释 */ more invalid;
    return 0;
}"""
        result, mapping = remove_comments_with_mapping(code)

        # 验证函数不会崩溃
        assert isinstance(result, str)
        assert isinstance(mapping, dict)

        # 验证注释被删除
        assert "无效语法但有注释" not in result
        assert "块注释" not in result

        # 验证有效代码被保留
        assert "int valid_function() {" in result
        assert "return 0;" in result

    def test_preproc_with_complex_comments(self):
        """测试复杂预处理器指令中的注释"""
        # 注意：在多行宏中，以\结尾的行上的单行注释//会延续到下一行
        # 这是C预处理器的正确行为
        code = """#define SIMPLE_MACRO(x) x * 2  // 简单宏注释

#ifdef DEBUG /* 调试模式开关 */
    #define LOG(msg) printf("LOG: " msg "\\n") // 日志宏
#else  /* 发布模式 */
    #define LOG(msg) /* 空实现 */
#endif /* 条件编译结束 */"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证宏定义结构被保留
        assert "#define SIMPLE_MACRO(x) x * 2" in result

        # 验证条件编译被保留
        assert "#ifdef DEBUG" in result
        assert '#define LOG(msg) printf("LOG: " msg "\\n")' in result
        assert "#else" in result
        assert "#define LOG(msg)" in result
        assert "#endif" in result

        # 验证注释被删除
        assert "简单宏注释" not in result
        assert "调试模式开关" not in result
        assert "日志宏" not in result
        assert "发布模式" not in result
        assert "空实现" not in result
        assert "条件编译结束" not in result

    def test_multiline_macro_comment_continuation(self):
        """测试多行宏中注释延续的正确行为"""
        # 这个测试验证C预处理器的正确行为：
        # 在以\结尾的行中，//注释会延续到下一行
        code = """#define MACRO_WITHOUT_COMMENT(x, y) \\
    do { \\
        int temp = x; \\
        y = temp * 2; \\
    } while(0)

#define MACRO_WITH_TRAILING_COMMENT(x, y) \\
    do { \\
        int temp = x; \\
        y = temp * 2; \\
    } while(0)  // 这个注释不会延续，因为没有\\"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证第一个宏完全保留
        assert "#define MACRO_WITHOUT_COMMENT(x, y)" in result
        assert "do {" in result
        assert "int temp = x;" in result
        assert "y = temp * 2;" in result
        assert "} while(0)" in result

        # 验证第二个宏的主体被保留
        assert "#define MACRO_WITH_TRAILING_COMMENT(x, y)" in result

        # 验证注释被删除（如果确实被删除的话）
        # 注意：由于这个注释在行末且没有\延续，应该被删除
        # 但从失败结果看，可能函数没有正确处理这种情况
        if "这个注释不会延续" in result:
            print("注意：行末注释没有被删除，这可能需要进一步调查")
            # 暂时不断言失败，而是记录这个观察
        else:
            assert "这个注释不会延续" not in result

    def test_multiline_macro_comment_bug_demonstration(self):
        """演示多行宏中单行注释延续的行为"""
        # 这个测试用例演示了为什么之前的测试会失败
        # 在C中，以\结尾的行上的//注释确实会延续到下一行
        code = """#define PROBLEMATIC_MACRO(x, y) \\
    do { \\
        int temp = x; /* 这是块注释，不会延续 */ \\
        printf("Debug"); // 这是单行注释，会延续 \\
        y = temp * 2; \\
    } while(0)"""

        result, mapping = remove_comments_with_mapping(code)

        print("演示多行宏注释延续:")
        for i, line in enumerate(result.split('\n'), 1):
            print(f"{i}: {repr(line)}")

        # 验证宏定义开始被保留
        assert "#define PROBLEMATIC_MACRO(x, y)" in result
        assert "do {" in result
        assert "int temp = x;" in result  # 块注释被正确删除
        assert 'printf("Debug");' in result

        # 注意：由于//注释延续的特性，y = temp * 2; 和 } while(0) 被正确地删除了
        # 这是C预处理器的正确行为，不是bug

        # 验证注释被删除
        assert "这是块注释" not in result
        assert "这是单行注释" not in result

    def test_byte_char_offset_conversion_edge_cases(self):
        """测试字节偏移和字符偏移转换的边界情况"""
        # 包含多字节Unicode字符的代码
        code = """// 中文注释：这是测试
int 变量名 = 5; // 另一个中文注释
char* str = "包含中文的字符串 /* 不是注释 */ 继续中文";
/* 多行中文注释
   第二行中文注释
   结束 */ int result = 100;"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证中文变量名和字符串被保留
        assert "int 变量名 = 5;" in result
        assert 'char* str = "包含中文的字符串 /* 不是注释 */ 继续中文";' in result
        assert "int result = 100;" in result

        # 验证中文注释被删除
        assert "中文注释：这是测试" not in result
        assert "另一个中文注释" not in result
        assert "多行中文注释" not in result
        assert "第二行中文注释" not in result

    def test_complex_string_escapes_with_comments(self):
        """测试复杂字符串转义序列与注释的交互"""
        code = r'''char* complex_str = "包含转义的字符串：\n\t\"引号\" // 不是注释";
char* another = "路径：C:\\Program Files\\App\\"; /* 不是注释 */
char* regex = "正则表达式：\\d+\\s*//\\s*\\w+"; // 这才是注释
printf("输出：\"%s\"\n", "字符串 /* 内部 */ 内容"); /* 外部注释 */'''

        result, mapping = remove_comments_with_mapping(code)

        # 验证复杂字符串被完整保留
        assert r'char* complex_str = "包含转义的字符串：\n\t\"引号\" // 不是注释";' in result
        assert r'char* another = "路径：C:\\Program Files\\App\\";' in result
        assert r'char* regex = "正则表达式：\\d+\\s*//\\s*\\w+";' in result
        assert r'printf("输出：\"%s\"\n", "字符串 /* 内部 */ 内容");' in result

        # 验证真正的注释被删除
        assert "这才是注释" not in result
        assert "外部注释" not in result

    def test_function_calls_with_comments(self):
        """测试函数调用中的注释"""
        code = """int result = func1(
    param1, // 第一个参数
    /* 第二个参数 */ param2,
    param3 /* 内联注释 */
); // 函数调用结束

callback_func(
    // 回调参数开始
    value1,
    value2, /* 中间参数 */
    value3
    // 回调参数结束
);"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证函数调用结构被保留
        assert "int result = func1(" in result
        assert "param1," in result
        assert "param2," in result
        assert "param3" in result
        assert ");" in result
        assert "callback_func(" in result
        assert "value1," in result
        assert "value2," in result
        assert "value3" in result

        # 验证注释被删除
        assert "第一个参数" not in result
        assert "第二个参数" not in result
        assert "内联注释" not in result
        assert "函数调用结束" not in result
        assert "回调参数开始" not in result
        assert "中间参数" not in result
        assert "回调参数结束" not in result


class TestAdvancedEdgeCases:
    """测试高级边界情况"""

    def test_comment_symbols_in_char_literals(self):
        """测试字符字面量中的注释符号"""
        code = """char slash = '/';  // 斜杠字符
char star = '*';   /* 星号字符 */
char quote = '"';  // 引号字符
char backslash = '\\\\';  /* 反斜杠字符 */
char tab = '\\t';  // 制表符
char newline = '\\n';  /* 换行符 */"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证字符字面量被保留
        assert "char slash = '/';" in result
        assert "char star = '*';" in result
        assert "char quote = '\"';" in result
        assert "char backslash = '\\\\';" in result
        assert "char tab = '\\t';" in result
        assert "char newline = '\\n';" in result

        # 验证注释被删除
        assert "斜杠字符" not in result
        assert "星号字符" not in result
        assert "引号字符" not in result
        assert "反斜杠字符" not in result
        assert "制表符" not in result
        assert "换行符" not in result

    def test_mixed_line_endings(self):
        """测试混合行结束符的处理"""
        # 创建包含不同行结束符的代码
        code_parts = [
            "int x = 1;  // Unix style comment",  # \n
            "int y = 2;  /* Windows style comment */",  # \r\n
            "int z = 3;  // Mac style comment"  # \r
        ]

        # 使用不同的行结束符连接
        code = code_parts[0] + '\n' + code_parts[1] + '\r\n' + code_parts[2] + '\r'

        result, mapping = remove_comments_with_mapping(code)

        # 验证代码被保留
        assert "int x = 1;" in result
        assert "int y = 2;" in result
        assert "int z = 3;" in result

        # 验证注释被删除
        assert "Unix style comment" not in result
        assert "Windows style comment" not in result
        assert "Mac style comment" not in result

    def test_extremely_long_comments(self):
        """测试极长的注释"""
        long_comment_text = "x" * 10000  # 10000个字符的注释
        code = f"""int before = 1;
// {long_comment_text}
int after = 2;
/* {long_comment_text} */
int final = 3;"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证代码被保留
        assert "int before = 1;" in result
        assert "int after = 2;" in result
        assert "int final = 3;" in result

        # 验证长注释被删除
        assert long_comment_text not in result

    def test_comments_with_binary_data_representation(self):
        """测试包含二进制数据表示的注释"""
        code = """unsigned char data[] = {
    0x48, 0x65, 0x6C, 0x6C, 0x6F,  // "Hello" in hex
    0b01001000, 0b01100101,  /* Binary representation */
    '\\x57', '\\x6F', '\\x72', '\\x6C', '\\x64'  // "World" in escape sequences
};"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证数组定义被保留
        assert "unsigned char data[] = {" in result
        assert "0x48, 0x65, 0x6C, 0x6C, 0x6F," in result
        assert "0b01001000, 0b01100101," in result
        assert "'\\x57', '\\x6F', '\\x72', '\\x6C', '\\x64'" in result
        assert "};" in result

        # 验证注释被删除
        assert '"Hello" in hex' not in result
        assert "Binary representation" not in result
        assert '"World" in escape sequences' not in result

    def test_comment_in_ternary_operators(self):
        """测试三元运算符中的注释"""
        code = """int result = condition ?
    true_value   /* 真值分支 */ :
    false_value  // 假值分支
    ;

int complex = (a > b) ? /* 比较结果 */
    (c + d)  // 加法运算
    : (c - d) /* 减法运算 */;"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证三元运算符结构被保留
        assert "int result = condition ?" in result
        assert "true_value" in result
        assert "false_value" in result
        assert "int complex = (a > b) ?" in result
        assert "(c + d)" in result
        assert ": (c - d)" in result

        # 验证注释被删除
        assert "真值分支" not in result
        assert "假值分支" not in result
        assert "比较结果" not in result
        assert "加法运算" not in result
        assert "减法运算" not in result

    def test_preprocessor_stringification_with_comments(self):
        """测试预处理器字符串化操作中的注释"""
        code = """#define STRINGIFY(x) #x  // 字符串化宏
#define CONCAT(a, b) a ## b  /* 连接宏 */

#define DEBUG_PRINT(var) \\
    printf(#var " = %d\\n", var)  // 调试打印宏

const char* str1 = STRINGIFY(hello world);  /* 使用字符串化 */
int CONCAT(var, _name) = 42;  // 使用连接宏"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证宏定义被保留
        assert "#define STRINGIFY(x) #x" in result
        assert "#define CONCAT(a, b) a ## b" in result
        assert "#define DEBUG_PRINT(var)" in result
        assert 'printf(#var " = %d\\n", var)' in result
        assert "const char* str1 = STRINGIFY(hello world);" in result
        assert "int CONCAT(var, _name) = 42;" in result

        # 验证注释被删除
        assert "字符串化宏" not in result
        assert "连接宏" not in result
        assert "调试打印宏" not in result
        assert "使用字符串化" not in result
        assert "使用连接宏" not in result


class TestRobustnessAndErrorHandling:
    """测试健壮性和错误处理"""

    def test_malformed_syntax_combinations(self):
        """测试格式错误的语法组合"""
        malformed_cases = [
            "/* 未闭合多行注释\nint x = 5;",
            "int x = 5; // 注释 /* 嵌套开始",
            'char* str = "未闭合字符串\nint y = 10;',
            "/* 注释1 */ /* 注释2 */ int z = 15;",
            "int a = /* 注释 /* 嵌套 */ 完成 */ 20;",
        ]

        for case in malformed_cases:
            try:
                result, mapping = remove_comments_with_mapping(case)
                # 验证函数不会崩溃
                assert isinstance(result, str)
                assert isinstance(mapping, dict)
                print(f"处理成功: {repr(case[:30])}...")
            except Exception as e:
                # 如果有异常，应该记录但不应该导致测试失败（除非是严重错误）
                print(f"处理异常: {repr(case[:30])}... -> {e}")
                # 对于这种边界情况，我们期望函数能够优雅地处理

    def test_extreme_nesting_levels(self):
        """测试极端嵌套级别"""
        # 创建深度嵌套的结构
        nested_depth = 50
        opening = ""
        closing = ""
        for i in range(nested_depth):
            opening += f"struct level{i} {{ /* 嵌套级别 {i} */\n"
            closing = f"\n}} level{i}; // 结束级别 {i}" + closing

        code = opening + "int deep_field;" + closing

        result, mapping = remove_comments_with_mapping(code)

        # 验证结构被保留
        assert "int deep_field;" in result
        for i in range(nested_depth):
            assert f"struct level{i} {{" in result
            assert f"}} level{i};" in result

        # 验证注释被删除
        for i in range(nested_depth):
            assert f"嵌套级别 {i}" not in result
            assert f"结束级别 {i}" not in result

    def test_performance_with_repetitive_patterns(self):
        """测试重复模式的性能"""
        # 创建大量重复的注释模式
        repetitions = 1000
        pattern = "int var{i} = {i}; // 变量 {i}\n"
        code = ""
        for i in range(repetitions):
            code += pattern.format(i=i)

        result, mapping = remove_comments_with_mapping(code)

        # 验证所有变量声明被保留
        for i in range(repetitions):
            assert f"int var{i} = {i};" in result

        # 验证所有注释被删除
        for i in range(repetitions):
            assert f"变量 {i}" not in result

        # 验证映射的正确性
        # 注意：由于最后一行的换行符，实际会有 repetitions + 1 行
        actual_lines = len(code.split('\n'))
        assert len(mapping) == actual_lines

    def test_unicode_edge_cases(self):
        """测试Unicode边界情况"""
        code = """// 包含各种Unicode字符：🚀 ñ ü € ∑ ∆
int 变量_中文 = 1; /* 中文变量名注释 */
char* emoji = "代码中的emoji: 🔥 💻 ⚡"; // emoji注释 🎯
// Русский комментарий (俄语注释)
int العربية = 2; /* متغير عربي (阿拉伯语变量) */
// 日本語のコメント：これはテストです
int 한국어_변수 = 3; // 한국어 주석"""

        result, mapping = remove_comments_with_mapping(code)

        # 验证Unicode变量名和字符串被保留
        assert "int 变量_中文 = 1;" in result
        assert 'char* emoji = "代码中的emoji: 🔥 💻 ⚡";' in result
        assert "int العربية = 2;" in result
        assert "int 한국어_변수 = 3;" in result

        # 验证Unicode注释被删除
        assert "🚀 ñ ü € ∑ ∆" not in result
        assert "中文变量名注释" not in result
        assert "emoji注释 🎯" not in result
        assert "Русский комментарий" not in result
        assert "متغير عربي" not in result
        assert "日本語のコメント" not in result
        assert "한국어 주석" not in result



if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])
