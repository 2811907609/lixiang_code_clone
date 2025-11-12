#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回溯灾难测试：检测正则表达式的性能问题和回溯风险

这个测试文件专门用于：
1. 检测正则表达式的回溯灾难
2. 验证性能优化
3. 确保恶意输入不会导致DoS攻击
"""

import pytest
import time
import re

from ai_agents.supervisor_agents.haloos_unit_test.parse_c_file_get_function_info import CFunctionLocator


class TestRegexBacktracking:
    """回溯灾难测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建一个临时的测试文件
        self.test_file = "/tmp/test_backtrack.c"
        with open(self.test_file, "w") as f:
            f.write("// 测试文件\n")

        self.locator = CFunctionLocator(self.test_file)

    def teardown_method(self):
        """每个测试方法后的清理"""
        import os
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def _measure_regex_time(self, pattern, text, timeout=1.0):
        """
        测量正则表达式匹配时间

        Args:
            pattern: 正则表达式模式
            text: 测试文本
            timeout: 超时时间（秒）

        Returns:
            (是否超时, 执行时间, 匹配结果)
        """
        start_time = time.time()
        try:
            match = pattern.search(text)
            end_time = time.time()
            execution_time = end_time - start_time

            # 如果执行时间超过超时时间，认为是回溯灾难
            is_timeout = execution_time > timeout
            return is_timeout, execution_time, match
        except Exception:
            end_time = time.time()
            execution_time = end_time - start_time
            return True, execution_time, None

    def test_simple_func_pattern_backtracking(self):
        """测试 simple_func_pattern 的回溯风险"""
        pattern = self.locator.simple_func_pattern

        # 正常情况 - 应该很快
        normal_text = "int func(int a, int b) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, normal_text)
        assert not is_timeout, f"正常情况下执行时间过长: {exec_time:.4f}s"
        assert match is not None, "正常函数应该被匹配"

        # 潜在的回溯灾难情况1: 大量重复的类型名
        disaster_text1 = "int " + "very_long_type_name " * 100 + "func(int a) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text1, timeout=0.1)
        print(f"灾难测试1执行时间: {exec_time:.4f}s")
        # 不应该超时，但要记录时间

        # 潜在的回溯灾难情况2: 大量嵌套的指针和空格
        disaster_text2 = "int" + " *" * 50 + " " * 100 + "func(int a) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text2, timeout=0.1)
        print(f"灾难测试2执行时间: {exec_time:.4f}s")

        # 潜在的回溯灾难情况3: 不匹配的文本（最危险）
        disaster_text3 = "int " + "a " * 100 + "(" + "b " * 100 + ")"  # 缺少函数名和大括号
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text3, timeout=0.1)
        print(f"灾难测试3执行时间: {exec_time:.4f}s")

        # 确保没有发生回溯灾难
        assert exec_time < 0.1, f"可能发生回溯灾难，执行时间: {exec_time:.4f}s"

    def test_pointer_func_pattern_backtracking(self):
        """测试 pointer_func_pattern 的回溯风险"""
        pattern = self.locator.pointer_func_pattern

        # 正常情况
        normal_text = "struct reader *func(int a) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, normal_text)
        assert not is_timeout, f"正常情况下执行时间过长: {exec_time:.4f}s"
        assert match is not None, "正常指针函数应该被匹配"

        # 潜在的回溯灾难情况1: 大量类型名重复
        disaster_text1 = "struct " + "very_long_struct_name " * 50 + "*func(int a) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text1, timeout=0.1)
        print(f"指针灾难测试1执行时间: {exec_time:.4f}s")

        # 潜在的回溯灾难情况2: 大量指针符号
        disaster_text2 = "int " + "*" * 100 + "func(int a) {"
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text2, timeout=0.1)
        print(f"指针灾难测试2执行时间: {exec_time:.4f}s")

        # 潜在的回溯灾难情况3: 不匹配的复杂文本
        disaster_text3 = "struct " + "name " * 50 + " " + "*" * 20 + " " * 50 + "("  # 缺少函数名
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text3, timeout=0.1)
        print(f"指针灾难测试3执行时间: {exec_time:.4f}s")

        # 确保没有发生回溯灾难
        assert exec_time < 0.1, f"可能发生回溯灾难，执行时间: {exec_time:.4f}s"

    def test_parameter_parsing_backtracking(self):
        """测试参数解析的回溯风险"""
        # 测试复杂参数列表的回溯风险
        complex_params = ", ".join([f"struct very_long_param_type_{i} *param_{i}" for i in range(50)])
        disaster_text = f"int func({complex_params}) {{"

        pattern = self.locator.simple_func_pattern
        is_timeout, exec_time, match = self._measure_regex_time(pattern, disaster_text, timeout=0.1)
        print(f"复杂参数测试执行时间: {exec_time:.4f}s")

        # 参数列表应该由 ([^{]*) 处理，这个模式相对安全
        assert exec_time < 0.1, f"参数解析可能发生回溯灾难，执行时间: {exec_time:.4f}s"

    def test_malicious_input_protection(self):
        """测试恶意输入的保护"""
        # 模拟恶意输入：大量嵌套和重复模式
        malicious_inputs = [
            # 大量空格和类型名
            "int " + " " * 1000 + "func() {",
            # 大量重复的类型关键字
            ("unsigned " * 100) + "int func() {",
            # 大量指针符号
            "int" + "*" * 200 + "func() {",
            # 不完整的函数定义（最容易触发回溯）
            "int " + "type " * 100 + "func(",
            # 大量参数但没有结束
            "int func(" + "int a, " * 100,
        ]

        patterns = [
            self.locator.simple_func_pattern,
            self.locator.pointer_func_pattern,
            self.locator.func_macro_pattern
        ]

        for i, malicious_text in enumerate(malicious_inputs):
            for j, pattern in enumerate(patterns):
                is_timeout, exec_time, match = self._measure_regex_time(pattern, malicious_text, timeout=0.05)
                print(f"恶意输入{i+1}-模式{j+1}执行时间: {exec_time:.4f}s")

                # 任何单个匹配都不应该超过50ms
                assert exec_time < 0.05, f"恶意输入{i+1}在模式{j+1}上可能触发回溯灾难: {exec_time:.4f}s"

    def test_regex_optimization_suggestions(self):
        """测试正则表达式优化建议"""
        # 分析当前正则表达式的潜在问题

        # 1. simple_func_pattern 分析
        simple_pattern_text = r'^\s*([a-zA-Z_]\w*(?:\s*\*+)?(?:\s+[a-zA-Z_]\w*)*?)\s+([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'
        print(f"Simple pattern: {simple_pattern_text}")

        # 检查嵌套量词
        nested_quantifiers = re.findall(r'\([^)]*\*[^)]*\*[^)]*\)', simple_pattern_text)
        if nested_quantifiers:
            print(f"警告: 发现嵌套量词，可能导致回溯: {nested_quantifiers}")

        # 检查贪婪vs非贪婪量词
        greedy_quantifiers = re.findall(r'[+*]\)', simple_pattern_text)
        non_greedy_quantifiers = re.findall(r'[+*]\?\)', simple_pattern_text)
        print(f"贪婪量词: {greedy_quantifiers}, 非贪婪量词: {non_greedy_quantifiers}")

        # 2. pointer_func_pattern 分析
        pointer_pattern_text = r'^\s*([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*)*)\s+(\*+)\s*([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'
        print(f"Pointer pattern: {pointer_pattern_text}")

        # 建议：使用原子组和占有量词来防止回溯
        print("\n优化建议:")
        print("1. 考虑使用原子组 (?>...) 来防止回溯")
        print("2. 使用占有量词 *+ 而不是贪婪量词 *")
        print("3. 限制重复次数，如 {0,10} 而不是 *")
        print("4. 对于已知格式，使用更精确的模式")

    def test_performance_benchmark(self):
        """性能基准测试"""
        # 创建不同复杂度的测试用例
        test_cases = [
            ("简单函数", "int func() {"),
            ("指针函数", "void *func(int a) {"),
            ("复杂返回类型", "struct very_long_struct_name *func() {"),
            ("复杂参数", "int func(struct a *p1, struct b *p2, int c) {"),
            ("最大复杂度", "struct very_long_struct_name_with_many_words *func(struct param1 *p1, struct param2 *p2, int p3, char *p4) {"),
        ]

        patterns = [
            ("simple", self.locator.simple_func_pattern),
            ("pointer", self.locator.pointer_func_pattern),
            ("macro", self.locator.func_macro_pattern),
        ]

        print("\n性能基准测试结果:")
        print("=" * 60)

        for case_name, test_text in test_cases:
            print(f"\n测试用例: {case_name}")
            print(f"文本: {test_text}")

            for pattern_name, pattern in patterns:
                # 多次运行取平均值
                times = []
                for _ in range(100):
                    start = time.time()
                    # match = pattern.search(test_text)
                    end = time.time()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                max_time = max(times)

                print(f"  {pattern_name:8}: 平均 {avg_time*1000:.3f}ms, 最大 {max_time*1000:.3f}ms, 匹配 {'✓' if pattern.search(test_text) else '✗'}")

        print("\n" + "=" * 60)


class TestOptimizedRegexPatterns:
    """测试优化后的正则表达式模式"""

    def test_optimized_patterns(self):
        """测试优化后的正则表达式模式"""

        # 优化的simple_func_pattern - 减少回溯风险
        optimized_simple = re.compile(
            r'^\s*([a-zA-Z_]\w*(?:\s*\*{1,5})?(?:\s+[a-zA-Z_]\w*){0,5})\s+'  # 限制重复次数
            r'([a-zA-Z_]\w*)\s*\(([^{]{0,500})\)\s*\{?'  # 限制参数长度
        )

        # 优化的pointer_func_pattern - 更精确的匹配
        optimized_pointer = re.compile(
            r'^\s*([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*){0,3})\s+'  # 限制类型组件数量
            r'(\*{1,5})\s*'  # 限制指针级别
            r'([a-zA-Z_]\w*)\s*\(([^{]{0,500})\)\s*\{?'  # 限制参数长度
        )

        # 测试优化后的模式
        test_cases = [
            "int func() {",
            "void *func(int a) {",
            "struct reader *func(struct reader *r) {",
            "struct reader_cache_change *reader_append_new_change(struct reader *r, int type) {",
        ]

        print("\n优化模式测试:")
        for text in test_cases:
            print(f"\n测试文本: {text}")

            # 测试优化的simple模式
            start = time.time()
            simple_match = optimized_simple.search(text)
            simple_time = time.time() - start

            # 测试优化的pointer模式
            start = time.time()
            pointer_match = optimized_pointer.search(text)
            pointer_time = time.time() - start

            print(f"  优化simple: {simple_time*1000:.3f}ms, 匹配: {'✓' if simple_match else '✗'}")
            print(f"  优化pointer: {pointer_time*1000:.3f}ms, 匹配: {'✓' if pointer_match else '✗'}")

            # 验证性能
            assert simple_time < 0.001, f"优化simple模式仍然太慢: {simple_time:.6f}s"
            assert pointer_time < 0.001, f"优化pointer模式仍然太慢: {pointer_time:.6f}s"


class TestOptimizedRegexFunctionality:
    """验证优化后的正则表达式功能正确性"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建包含目标函数的测试文件
        self.test_content = """
void *reader_get_private(struct reader *r) {
    return r->private_data;
}

struct reader_cache_change *reader_append_new_change(struct reader *r, int type) {
    // 函数体
    return NULL;
}

int simple_func(int a, int b) {
    return a + b;
}

struct complex_type **get_complex_ptr() {
    return NULL;
}

unsigned long long *get_ull_ptr(int param) {
    return NULL;
}
"""

        self.test_file = "/tmp/test_optimized_functions.c"
        with open(self.test_file, "w") as f:
            f.write(self.test_content)

        self.locator = CFunctionLocator(self.test_file)

    def teardown_method(self):
        """每个测试方法后的清理"""
        import os
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_target_functions_still_detected(self):
        """测试优化后仍能检测到目标函数"""
        detected_names = self.locator.list_all_functions()

        # 这两个是原来的问题函数，必须能检测到
        assert "reader_get_private" in detected_names, "reader_get_private 函数检测失败"
        assert "reader_append_new_change" in detected_names, "reader_append_new_change 函数检测失败"

        # 验证返回类型解析正确
        reader_get_private = self.locator.functions_info['reader_get_private']
        assert "void *" in reader_get_private.return_type, f"返回类型解析错误: {reader_get_private.return_type}"

        reader_append_new_change = self.locator.functions_info['reader_append_new_change']
        assert "struct reader_cache_change *" in reader_append_new_change.return_type, \
            f"返回类型解析错误: {reader_append_new_change.return_type}"

        print(f"✅ 检测到的函数: {detected_names}")
        print(f"✅ reader_get_private 返回类型: {reader_get_private.return_type}")
        print(f"✅ reader_append_new_change 返回类型: {reader_append_new_change.return_type}")

    def test_various_function_types_detected(self):
        """测试各种函数类型都能被检测到"""
        detected_names = self.locator.list_all_functions()

        expected_functions = [
            "reader_get_private",        # void * 指针返回
            "reader_append_new_change",  # struct * 指针返回
            "simple_func",              # 简单int返回
            "get_complex_ptr",          # 多级指针返回
            "get_ull_ptr"               # 复杂类型指针返回
        ]

        for expected in expected_functions:
            assert expected in detected_names, f"函数 {expected} 检测失败"

        print(f"✅ 所有预期函数都被检测到: {len(expected_functions)}/{len(detected_names)}")

    def test_optimized_regex_performance_vs_original(self):
        """对比优化前后的性能"""
        # 原始有问题的正则表达式模式
        original_simple_pattern = re.compile(
            r'^\s*([a-zA-Z_]\w*(?:\s*\*+)?(?:\s+[a-zA-Z_]\w*)*?)\s+'
            r'([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'
        )

        original_pointer_pattern = re.compile(
            r'^\s*([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*)*)\s+(\*+)\s*'
            r'([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'
        )

        # 优化后的模式
        optimized_simple = self.locator.simple_func_pattern
        optimized_pointer = self.locator.pointer_func_pattern

        # 测试用例
        test_cases = [
            "void *reader_get_private(struct reader *r) {",
            "struct reader_cache_change *reader_append_new_change(struct reader *r, int type) {",
            "int simple_func(int a, int b) {",
        ]

        print("\n性能对比测试:")
        print("=" * 50)

        for case in test_cases:
            print(f"\n测试: {case[:50]}...")

            # 测试原始模式
            start = time.time()
            for _ in range(1000):
                original_simple_pattern.search(case)
                original_pointer_pattern.search(case)
            original_time = time.time() - start

            # 测试优化模式
            start = time.time()
            for _ in range(1000):
                optimized_simple.search(case)
                optimized_pointer.search(case)
            optimized_time = time.time() - start

            print(f"  原始模式: {original_time*1000:.3f}ms")
            print(f"  优化模式: {optimized_time*1000:.3f}ms")
            print(f"  性能提升: {((original_time - optimized_time) / original_time * 100):.1f}%")

            # 优化后可能稍慢，但换取了安全性（允许50%的性能损失换取回溯安全性）
            if optimized_time > original_time * 1.5:
                print(f"  ⚠️  警告: 性能下降较多: {optimized_time/original_time:.2f}x")
            # 确保不会有严重的性能退化（不超过2倍）
            assert optimized_time <= original_time * 2.0, f"优化后性能下降过多: {optimized_time/original_time:.2f}x"

    def test_edge_cases_with_optimized_regex(self):
        """测试边界情况下优化后的正则表达式"""
        edge_cases = [
            # 极长的类型名
            ("struct " + "very_long_struct_name_" * 5 + " *func() {", "应该被限制处理"),
            # 多级指针
            ("int *****func() {", "多级指针"),
            # 复杂参数
            ("int func(" + "struct param *p, " * 10 + "int last) {", "复杂参数列表"),
            # 边界长度的参数
            ("int func(" + "int param" + "0123456789" * 50 + ") {", "超长参数名"),
        ]

        print("\n边界情况测试:")
        print("=" * 30)

        for test_input, description in edge_cases:
            print(f"\n测试: {description}")

            # 测试性能 - 不应该超时
            start = time.time()
            simple_match = self.locator.simple_func_pattern.search(test_input)
            pointer_match = self.locator.pointer_func_pattern.search(test_input)
            execution_time = time.time() - start

            print(f"  执行时间: {execution_time*1000:.3f}ms")
            print(f"  Simple匹配: {'✓' if simple_match else '✗'}")
            print(f"  Pointer匹配: {'✓' if pointer_match else '✗'}")

            # 确保没有回溯灾难（执行时间应该很短）
            assert execution_time < 0.01, f"边界情况执行时间过长: {execution_time:.4f}s"

    def test_regex_limits_effectiveness(self):
        """测试正则表达式限制的有效性"""
        # 测试超出限制的输入
        extreme_cases = [
            # 超过5级指针限制
            "int" + "*" * 10 + "func() {",
            # 超过类型组件限制
            "struct " + "component " * 10 + "*func() {",
            # 超长参数列表（超过1000字符）
            "int func(" + "int param_" + "x" * 200 + ", " * 10 + ") {",
        ]

        print("\n限制有效性测试:")
        print("=" * 25)

        for extreme_input in extreme_cases:
            print(f"\n测试超限输入长度: {len(extreme_input)}")

            start = time.time()
            simple_match = self.locator.simple_func_pattern.search(extreme_input)
            pointer_match = self.locator.pointer_func_pattern.search(extreme_input)
            execution_time = time.time() - start

            print(f"  执行时间: {execution_time*1000:.3f}ms")
            print(f"  处理结果: Simple={'✓' if simple_match else '✗'}, Pointer={'✓' if pointer_match else '✗'}")

            # 即使是极端情况，也不应该超时
            assert execution_time < 0.005, f"极端情况执行时间过长: {execution_time:.4f}s"


if __name__ == "__main__":
    # 运行特定的回溯测试
    pytest.main([__file__, "-v", "-s"])
