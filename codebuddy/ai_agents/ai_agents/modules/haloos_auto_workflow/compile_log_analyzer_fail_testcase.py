#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试失败分析器
用于解析测试错误报告，提取失败测试用例的文件和行数信息
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TestFailure:
    """测试失败信息数据类"""
    file_path: str
    test_name: str
    line_number: int
    error_message: str


class TestFailureAnalyzer:
    """测试失败分析器"""

    def __init__(self):
        # 匹配文件块开始的正则表达式
        self.file_block_pattern = re.compile(
            r'\[([^\]]+)\]',
            re.MULTILINE
        )

        # 匹配测试项的正则表达式
        self.test_pattern = re.compile(
            r'Test:\s*(\S+)\s*\n\s*At line \((\d+)\):\s*"([^"]*)"',
            re.MULTILINE
        )

        # 匹配崩溃测试的正则表达式
        self.crash_pattern = re.compile(
            r'ERROR: Test executable `([^`]+)` seems to have crashed',
            re.MULTILINE
        )

        # 匹配测试摘要的正则表达式
        self.summary_pattern = re.compile(
            r'TESTED:\s*(\d+)\s*\n\s*PASSED:\s*(\d+)\s*\n\s*FAILED:\s*(\d+)',
            re.MULTILINE
        )

    def parse_test_failures(self, error_text: str) -> Dict[str, Any]:
        """
        解析测试失败信息

        Args:
            error_text: 错误文本内容

        Returns:
            包含失败信息的字典
        """
        result = {
            "has_failures": False,
            "crashed_tests": [],
            "failed_tests": [],
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0
            }
        }

        # 解析崩溃的测试
        crashed_tests = self._parse_crashed_tests(error_text)
        if crashed_tests:
            result["crashed_tests"] = crashed_tests
            result["has_failures"] = True

        # 解析GCOV失败测试
        failed_tests = self._parse_gcov_failures(error_text)
        if failed_tests:
            result["failed_tests"] = failed_tests
            result["has_failures"] = True

        # 解析测试摘要
        summary = self._parse_test_summary(error_text)
        if summary:
            result["summary"] = summary
            if summary["failed_tests"] > 0:
                result["has_failures"] = True

        return result

    def _parse_crashed_tests(self, error_text: str) -> List[Dict[str, str]]:
        """解析崩溃的测试"""
        crashed_tests = []
        matches = self.crash_pattern.findall(error_text)

        for match in matches:
            test_executable = match
            crashed_tests.append({
                "test_executable": test_executable,
                "error_message": "Test executable crashed"
            })

        return crashed_tests

    def _parse_gcov_failures(self, error_text: str) -> List[TestFailure]:
        """解析GCOV失败测试"""
        failed_tests = []

        # 按照文件块分割
        file_blocks = re.split(r'\n(?=\[)', error_text)

        for block in file_blocks:
            if not block.strip():
                continue

            # 提取文件路径
            file_match = self.file_block_pattern.search(block)
            if not file_match:
                continue

            file_path = file_match.group(1).strip()

            # 在这个块中查找所有测试
            test_matches = self.test_pattern.findall(block)

            for test_match in test_matches:
                test_name, line_number, error_message = test_match

                failure = TestFailure(
                    file_path=file_path,
                    test_name=test_name.strip(),
                    line_number=int(line_number),
                    error_message=error_message.strip()
                )
                failed_tests.append(failure)

        return failed_tests

    def _parse_test_summary(self, error_text: str) -> Optional[Dict[str, int]]:
        """解析测试摘要"""
        match = self.summary_pattern.search(error_text)
        if match:
            total, passed, failed = match.groups()
            return {
                "total_tests": int(total),
                "passed_tests": int(passed),
                "failed_tests": int(failed)
            }
        return None

    def _extract_function_name(self, error_message: str) -> str:
        """从错误信息中提取函数名"""
        # 匹配 "Function 函数名." 模式
        func_pattern = r'Function\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        match = re.search(func_pattern, error_message)
        if match:
            return match.group(1)

        # 匹配崩溃信息中的函数名，如 "in Os_StartScheduleTableSynchron"
        crash_pattern = r'in\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        match = re.search(crash_pattern, error_message)
        if match:
            return match.group(1)

        return "UNKNOWN"

    def generate_failure_report(self, error_text: str) -> str:
        """
        生成失败报告

        Args:
            error_text: 错误文本内容

        Returns:
            格式化的失败报告
        """
        analysis = self.parse_test_failures(error_text)

        if not analysis["has_failures"]:
            return "✅ 没有检测到测试失败"

        report = []
        report.append("❌ 测试失败分析报告")
        report.append("=" * 50)

        # 崩溃测试
        if analysis["crashed_tests"]:
            report.append("\n🔥 崩溃的测试:")
            for crash in analysis["crashed_tests"]:
                report.append(f"  - {crash['test_executable']}")
                report.append(f"    错误: {crash['error_message']}")

        # 失败测试详情
        if analysis["failed_tests"]:
            report.append("\n📋 失败测试详情:")

            # 按文件分组
            files = {}
            for failure in analysis["failed_tests"]:
                if failure.file_path not in files:
                    files[failure.file_path] = []
                files[failure.file_path].append(failure)

            for file_path, failures in files.items():
                report.append(f"\n📁 文件: {file_path}")
                for failure in failures:
                    func_name = self._extract_function_name(failure.error_message)
                    report.append(f"  🔸 测试函数: {failure.test_name}")
                    report.append(f"     行号: {failure.line_number}")
                    report.append(f"     涉及函数: {func_name}")
                    report.append(f"     错误: {failure.error_message}")

        # 测试摘要
        summary = analysis["summary"]
        if summary["total_tests"] > 0:
            report.append("\n📊 测试摘要:")
            report.append(f"  总计: {summary['total_tests']}")
            report.append(f"  通过: {summary['passed_tests']}")
            report.append(f"  失败: {summary['failed_tests']}")
            report.append(f"  成功率: {summary['passed_tests']/summary['total_tests']*100:.1f}%")

        return "\n".join(report)

    def get_failure_files_and_lines(self, error_text: str) -> List[Dict[str, Any]]:
        """
        获取失败测试的文件和行数信息

        Args:
            error_text: 错误文本内容

        Returns:
            包含文件路径和行数的列表
        """
        analysis = self.parse_test_failures(error_text)

        failure_info = []

        # 添加GCOV失败测试信息
        for failure in analysis["failed_tests"]:
            func_name = self._extract_function_name(failure.error_message)
            failure_info.append({
                "file": failure.file_path,
                "line": failure.line_number,
                "test_function": failure.test_name,
                "related_function": func_name,
                "error_message": failure.error_message
            })

        return failure_info


def analyze_test_failures(error_text: str) -> Dict[str, Any]:
    """
    分析测试失败的便捷函数

    Args:
        error_text: 测试错误输出文本

    Returns:
        分析结果字典，包含:
        - has_failures: 是否存在失败
        - failure_count: 失败数量
        - files_and_lines: 失败文件和行数列表
        - report: 详细报告
    """
    analyzer = TestFailureAnalyzer()

    # 解析失败信息
    analysis = analyzer.parse_test_failures(error_text)

    # 获取文件和行数信息
    files_and_lines = analyzer.get_failure_files_and_lines(error_text)

    # 生成报告
    report = analyzer.generate_failure_report(error_text)

    return {
        "has_failures": analysis["has_failures"],
        "failure_count": len(analysis["failed_tests"]) + len(analysis["crashed_tests"]),
        "failed_tests_count": len(analysis["failed_tests"]),
        "crashed_tests_count": len(analysis["crashed_tests"]),
        "files_and_lines": files_and_lines,
        "summary": analysis["summary"],
        "report": report,
        "raw_analysis": analysis
    }


def has_test_failures(error_text: str) -> bool:
    """
    简单判断是否存在测试失败

    Args:
        error_text: 测试错误输出文本

    Returns:
        True如果存在失败，False否则
    """
    analyzer = TestFailureAnalyzer()
    analysis = analyzer.parse_test_failures(error_text)
    return analysis["has_failures"]


def get_failed_files_and_functions(error_text: str) -> List[Dict[str, str]]:
    """
    获取失败测试的文件和函数信息

    Args:
        error_text: 测试错误输出文本

    Returns:
        包含文件、测试函数、相关函数的列表
    """
    analyzer = TestFailureAnalyzer()
    return analyzer.get_failure_files_and_lines(error_text)


def get_failure_summary(error_text: str) -> Dict[str, Any]:
    """
    获取失败测试的摘要信息

    Args:
        error_text: 测试错误输出文本

    Returns:
        包含失败摘要的字典
    """
    result = analyze_test_failures(error_text)

    # 提取唯一的文件和函数
    failed_files = list(set(item['file'] for item in result['files_and_lines']))
    related_functions = list(set(item['related_function'] for item in result['files_and_lines']
                                if item['related_function'] != 'UNKNOWN'))

    return {
        'has_failures': result['has_failures'],
        'total_failed_tests': result['failure_count'],
        'failed_files': failed_files,
        'related_functions': related_functions,
        'failed_file_count': len(failed_files),
        'related_function_count': len(related_functions)
    }
