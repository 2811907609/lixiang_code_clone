#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_analyze_merge_key.py

测试coverity_analysis_tool.py中的analyze_merge_key函数的测试用例
"""

import json
import unittest
from unittest.mock import patch, mock_open, MagicMock

from coverity_analysis_tool import analyze_merge_key


class TestAnalyzeMergeKey(unittest.TestCase):
    """测试analyze_merge_key函数的测试类"""

    def setUp(self):
        """测试前的准备工作"""
        self.test_merge_key = "930e496283b52c15b1da88b50ab4f225"
        self.sample_raw_errors = {
            "issues": [
                {
                    "mergeKey": "930e496283b52c15b1da88b50ab4f225",
                    "checkerName": "NULL_POINTER_DEREFERENCE",
                    "strippedMainEventFilePathname": "src/test.c",
                    "mainEventLineNumber": 10,
                    "functionDisplayName": "test_function"
                }
            ]
        }
        self.sample_analysis_result = {
            "bool_cur_issue_fixed": True,
            "new_issue_list": ["new_issue_123"],
            "missing_issue_list": ["old_issue_456"],
            "execution_time": 10.5,
            "coverity_output_path": "/path/to/output.json",
            "error_message": ""
        }

    def test_analyze_merge_key_valid_input(self):
        """测试analyze_merge_key函数的正常输入情况"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', mock_open()):
                with patch('json.dump'):
                    mock_execute.return_value = self.sample_analysis_result

                    result = analyze_merge_key(self.test_merge_key)

                    # 验证execute_analyse_command被调用
                    mock_execute.assert_called_once_with(self.test_merge_key)

                    # 验证返回结果正确
                    self.assertEqual(result, self.sample_analysis_result)

    def test_analyze_merge_key_empty_merge_key(self):
        """测试analyze_merge_key函数的空mergeKey输入"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            mock_execute.return_value = {
                "bool_cur_issue_fixed": False,
                "new_issue_list": [],
                "missing_issue_list": [],
                "execution_time": 0.0,
                "coverity_output_path": "",
                "error_message": "Invalid mergeKey"
            }

            result = analyze_merge_key("")

            # 验证空mergeKey也能正常处理
            mock_execute.assert_called_once_with("")
            self.assertFalse(result["bool_cur_issue_fixed"])

    def test_analyze_merge_key_invalid_merge_key(self):
        """测试analyze_merge_key函数的无效mergeKey输入"""
        invalid_merge_key = "invalid_merge_key_123"

        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            mock_execute.return_value = {
                "bool_cur_issue_fixed": False,
                "new_issue_list": [],
                "missing_issue_list": [],
                "execution_time": 5.0,
                "coverity_output_path": "",
                "error_message": "mergeKey not found"
            }

            result = analyze_merge_key(invalid_merge_key)

            # 验证无效mergeKey的处理
            mock_execute.assert_called_once_with(invalid_merge_key)
            self.assertFalse(result["bool_cur_issue_fixed"])
            self.assertEqual(result["error_message"], "mergeKey not found")

    def test_analyze_merge_key_with_execution_error(self):
        """测试analyze_merge_key函数在执行过程中发生错误的情况"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            mock_execute.side_effect = Exception("Execution failed")

            # 在这种情况下，analyze_merge_key应该让异常传播或处理异常
            with self.assertRaises(Exception):
                analyze_merge_key(self.test_merge_key)

    def test_analyze_merge_key_file_save_error(self):
        """测试analyze_merge_key函数在保存文件时发生错误的情况"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with patch('builtins.print') as mock_print:
                    mock_execute.return_value = self.sample_analysis_result

                    result = analyze_merge_key(self.test_merge_key)

                    # 验证即使文件保存失败，函数也能正常返回结果
                    self.assertEqual(result, self.sample_analysis_result)

                    # 验证打印了警告信息
                    mock_print.assert_any_call("Warning: Could not save result to file: Permission denied")

    def test_analyze_merge_key_output_file_format(self):
        """测试analyze_merge_key函数输出文件名格式"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('json.dump'):
                    mock_execute.return_value = self.sample_analysis_result

                    # result = analyze_merge_key(self.test_merge_key)

                    # 验证文件路径格式正确
                    expected_file_path = f"/home/chehejia/programs/lixiang/agent_create_code/apr_project/output/tool_cov_analyse/analysis_result_{self.test_merge_key[:16]}.json"
                    mock_file.assert_called_with(expected_file_path, 'w', encoding='utf-8')

    def test_analyze_merge_key_long_merge_key(self):
        """测试analyze_merge_key函数处理长mergeKey的情况"""
        long_merge_key = "a" * 50  # 50个字符的长mergeKey

        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('json.dump'):
                    mock_execute.return_value = self.sample_analysis_result

                    # result = analyze_merge_key(long_merge_key)

                    # 验证文件名只使用前16个字符
                    expected_file_path = f"/home/chehejia/programs/lixiang/agent_create_code/apr_project/output/tool_cov_analyse/analysis_result_{long_merge_key[:16]}.json"
                    mock_file.assert_called_with(expected_file_path, 'w', encoding='utf-8')

    def test_analyze_merge_key_special_characters(self):
        """测试analyze_merge_key函数处理特殊字符mergeKey的情况"""
        special_merge_key = "test!@#$%^&*()_+"

        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', mock_open()):
                with patch('json.dump'):
                    mock_execute.return_value = self.sample_analysis_result

                    result = analyze_merge_key(special_merge_key)

                    # 验证特殊字符也能正常处理
                    mock_execute.assert_called_once_with(special_merge_key)
                    self.assertEqual(result, self.sample_analysis_result)

    def test_analyze_merge_key_result_structure(self):
        """测试analyze_merge_key函数返回结果的结构"""
        with patch('coverity_analysis_tool.execute_analyse_command') as mock_execute:
            with patch('builtins.open', mock_open()):
                with patch('json.dump'):
                    mock_execute.return_value = self.sample_analysis_result

                    result = analyze_merge_key(self.test_merge_key)

                    # 验证返回结果包含所有必要的字段
                    required_fields = [
                        "bool_cur_issue_fixed",
                        "new_issue_list",
                        "missing_issue_list",
                        "execution_time",
                        "coverity_output_path",
                        "error_message"
                    ]

                    for field in required_fields:
                        self.assertIn(field, result)

                    # 验证字段类型
                    self.assertIsInstance(result["bool_cur_issue_fixed"], bool)
                    self.assertIsInstance(result["new_issue_list"], list)
                    self.assertIsInstance(result["missing_issue_list"], list)
                    self.assertIsInstance(result["execution_time"], (int, float))
                    self.assertIsInstance(result["coverity_output_path"], str)
                    self.assertIsInstance(result["error_message"], str)


class TestAnalyzeMergeKeyIntegration(unittest.TestCase):
    """analyze_merge_key函数的集成测试"""

    def setUp(self):
        """集成测试准备"""
        self.test_merge_key = "test_integration_key"

    @patch('coverity_analysis_tool.BuildVerifyExecutor')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_analyze_merge_key_integration_success(self, mock_exists, mock_open_func, mock_executor_class):
        """测试analyze_merge_key函数的成功集成场景"""
        # Mock文件存在
        mock_exists.return_value = True

        # Mock文件读取
        raw_data = {
            "issues": [{
                "mergeKey": self.test_merge_key,
                "checkerName": "TEST_CHECKER",
                "strippedMainEventFilePathname": "test.c",
                "mainEventLineNumber": 5
            }]
        }

        current_data = {"issues": []}  # 没有问题，表示已修复

        mock_file_contents = [
            json.dumps(raw_data),  # raw_all_errors.json
            "test code line\n",    # 源代码文件
            json.dumps(current_data),  # 当前分析结果
            json.dumps(raw_data),  # 再次读取raw文件
        ]

        mock_open_func.side_effect = [
            mock_open(read_data=content).return_value
            for content in mock_file_contents
        ]

        # Mock BuildVerifyExecutor
        mock_executor = MagicMock()
        mock_executor.execute_command_internal.return_value = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Mock judge_issues_existed和diff_issues
        with patch('coverity_analysis_tool.judge_issues_existed', return_value=False):
            with patch('coverity_analysis_tool.diff_issues', return_value=([], [raw_data["issues"][0]])):
                result = analyze_merge_key(self.test_merge_key)

                # 验证结果
                self.assertTrue(result["bool_cur_issue_fixed"])
                self.assertIsInstance(result["execution_time"], (int, float))


if __name__ == "__main__":
    unittest.main(verbosity=2)
