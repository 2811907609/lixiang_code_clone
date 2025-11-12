"""
测试用例：C文件宏指令去除工具

测试 remove_c_macro_directives 函数的各种场景
"""

import unittest
from ai_agents.supervisor_agents.haloos_unit_test.remove_c_file_macro_if_endif import remove_c_macro_directives


class TestRemoveCMacroDirectives(unittest.TestCase):
    """测试 remove_c_macro_directives 函数"""

    def test_empty_string(self):
        """测试空字符串输入"""
        result = remove_c_macro_directives("")
        self.assertEqual(result, "")

    def test_none_input(self):
        """测试 None 输入"""
        result = remove_c_macro_directives(None)
        self.assertIsNone(result)

    def test_no_macros(self):
        """测试不包含宏指令的代码"""
        code = """void function() {
    int a = 1;
    return a;
}"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, code)

    def test_basic_if_endif(self):
        """测试基本的 #if #endif 块"""
        code = """#if (CONDITION)
void function() {
    // some code
}
#endif"""
        expected = """
void function() {
    // some code
}
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_ifdef_ifndef(self):
        """测试 #ifdef 和 #ifndef"""
        code = """#ifdef DEBUG
    printf("Debug mode");
#endif
#ifndef RELEASE
    printf("Not release");
#endif"""
        expected = """
    printf("Debug mode");


    printf("Not release");
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_if_else_endif(self):
        """测试 #if #else #endif 结构"""
        code = """#if defined(WINDOWS)
    windows_function();
#else
    unix_function();
#endif"""
        expected = """
    windows_function();

    unix_function();
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_elif_chain(self):
        """测试 #elif 链"""
        code = """#if defined(PLATFORM_A)
    platform_a_code();
#elif defined(PLATFORM_B)
    platform_b_code();
#elif defined(PLATFORM_C)
    platform_c_code();
#else
    default_code();
#endif"""
        expected = """
    platform_a_code();

    platform_b_code();

    platform_c_code();

    default_code();
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_error_directive(self):
        """测试 #error 指令"""
        code = """#if !defined(REQUIRED_MACRO)
#error "REQUIRED_MACRO must be defined"
#endif"""
        expected = """

"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_warning_directive(self):
        """测试 #warning 指令"""
        code = """#warning "This feature is deprecated"
void old_function() {
    // legacy code
}"""
        expected = """
void old_function() {
    // legacy code
}"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_pragma_directive(self):
        """测试 #pragma 指令"""
        code = """#pragma once
#pragma pack(push, 1)
struct data {
    int value;
};
#pragma pack(pop)"""
        expected = """

struct data {
    int value;
};
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_nested_macros(self):
        """测试嵌套的宏指令"""
        code = """#ifdef OUTER_CONDITION
    #if INNER_CONDITION
        nested_code();
    #endif
#endif"""
        expected = """

        nested_code();

"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)


        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_complex_conditions(self):
        """测试复杂条件的宏指令"""
        code = """#if (Dem_GetSizeOfDTCStaChgCbkList() > 0)
void Dem_DtcStatusChangeCallBack(uint32 DTC, uint8 DTCStatusOld, uint8 DTCStatusNew)
{
    Dem_CallDtcStatusChangeCallback(DTC, DTCStatusOld, DTCStatusNew);
}
#endif

#elif defined(DEM_AGING_COUNTER_CLEAR_ON_ALL_FAIL)
    Dem_ClearAgingCounter();
#endif"""
        expected = """
void Dem_DtcStatusChangeCallBack(uint32 DTC, uint8 DTCStatusOld, uint8 DTCStatusNew)
{
    Dem_CallDtcStatusChangeCallback(DTC, DTCStatusOld, DTCStatusNew);
}



    Dem_ClearAgingCounter();
"""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_multiline_error_message(self):
        """测试带引号字符串的 #error 指令"""
        code = '''#error "Dem: Unknown aging counter clear behavior"
#warning "This is a multi-line \\
warning message"'''
        expected = """

warning message\""""
        result = remove_c_macro_directives(code)
        self.assertEqual(result, expected)

    def test_line_count_preservation(self):
        """测试行数保持不变"""
        code = """line 1
#if CONDITION
line 3
#else
line 5
#endif
line 7"""
        result = remove_c_macro_directives(code)
        original_lines = code.split('\n')
        result_lines = result.split('\n')

        # 验证行数相同
        self.assertEqual(len(original_lines), len(result_lines))

        # 验证非宏指令行保持不变
        self.assertEqual(result_lines[0], "line 1")
        self.assertEqual(result_lines[1], "")  # #if 被替换为空行
        self.assertEqual(result_lines[2], "line 3")
        self.assertEqual(result_lines[3], "")  # #else 被替换为空行
        self.assertEqual(result_lines[4], "line 5")
        self.assertEqual(result_lines[5], "")  # #endif 被替换为空行
        self.assertEqual(result_lines[6], "line 7")

    def test_mixed_content(self):
        """测试混合内容（宏指令和普通代码）"""
        code = """#include <stdio.h>  // 这行不会被移除，因为不是条件编译指令

#if DEBUG
    #define LOG(x) printf(x)
#else
    #define LOG(x)
#endif

int main() {
    #ifdef VERBOSE
        LOG("Starting program");
    #endif

    return 0;
}

#pragma pack(1)"""

        result = remove_c_macro_directives(code)
        lines = result.split('\n')

        # 验证 #include 行保持不变
        self.assertEqual(lines[0], "#include <stdio.h>  // 这行不会被移除，因为不是条件编译指令")

        # 验证宏指令被替换为空行
        self.assertEqual(lines[2], "")  # #if DEBUG
        self.assertEqual(lines[4], "")  # #else
        self.assertEqual(lines[6], "")  # #endif

    def test_single_line_macros(self):
        """测试单行的各种宏指令"""
        macros = [
            "#if CONDITION",
            "#ifdef MACRO",
            "#ifndef MACRO",
            "#elif defined(OTHER)",
            "#else",
            "#endif",
            "#error \"Error message\"",
            "#warning \"Warning message\"",
            "#pragma once"
        ]

        for macro in macros:
            with self.subTest(macro=macro):
                result = remove_c_macro_directives(macro)
                self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
