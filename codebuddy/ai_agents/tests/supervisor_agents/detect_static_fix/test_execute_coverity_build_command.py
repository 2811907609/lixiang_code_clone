"""
测试 execute_coverity_build_command 函数的测试用例

本测试文件包含对 execute_coverity_build_command 函数的全面测试，
包括正常用例、边界情况和错误处理。
"""

import pytest
import unittest
from unittest.mock import Mock, patch
import tempfile
import sys
from pathlib import Path

# 添加项目路径到 sys.path 以便导入模块
sys.path.insert(0, str(Path(__file__).parent / 'codebuddy' / 'ai_agents'))

from ai_agents.supervisor_agents.detected_static_repair.build_runner import execute_coverity_build_command


class TestExecuteCoverityBuildCommand(unittest.TestCase):
    """execute_coverity_build_command 函数的测试类"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_command = "echo 'Testing Coverity build command'"
        self.mock_result = {
            "编译是否成功": True,
            "编译后信息": "=== COMPILATION SUCCESS ===\n=== STATISTICS ===\nTotal lines processed: 5",
            "编译耗时": 1.23
        }

    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_success(self, mock_executor_class):
        """测试成功执行 Coverity 构建命令的情况"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = self.mock_result
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result["编译是否成功"])
        self.assertIn("编译后信息", result)
        self.assertIn("编译耗时", result)
        self.assertIsInstance(result["编译耗时"], float)

        # 验证 BuildVerifyExecutor 的调用
        mock_executor_class.assert_called_once()
        mock_executor._execute_command_internal.assert_called_once_with(self.test_command)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_with_parameters(self, mock_executor_class):
        """测试带有完整参数的 Coverity 构建命令执行"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = self.mock_result
        mock_executor_class.return_value = mock_executor

        # 设置测试参数
        working_dir = self.temp_dir
        timeout = 600.0
        env_vars = {"COVERITY_HOME": "/opt/coverity", "PATH": "/usr/bin"}
        validate_project = False

        # 执行测试
        result = execute_coverity_build_command(
            command=self.test_command,
            working_directory=working_dir,
            timeout_seconds=timeout,
            environment_vars=env_vars,
            validate_project=validate_project
        )

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result["编译是否成功"])

        # 验证 BuildVerifyExecutor 的初始化参数
        mock_executor_class.assert_called_once_with(
            working_directory=working_dir,
            timeout_seconds=timeout,
            environment_vars=env_vars,
            max_output_size_kb=2048.0,
            validate_commands=validate_project,
            allow_dangerous_commands=False
        )

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_compilation_failure(self, mock_executor_class):
        """测试编译失败的情况"""
        # 配置 mock 返回失败结果
        failed_result = {
            "编译是否成功": False,
            "编译后信息": "=== COMPILATION FAILED ===\n=== UNIQUE COMPILATION ERRORS ===\nerror: undefined reference to 'main'",
            "编译耗时": 2.45
        }

        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = failed_result
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertFalse(result["编译是否成功"])
        self.assertIn("COMPILATION FAILED", result["编译后信息"])
        self.assertIn("编译耗时", result)

    def test_execute_coverity_build_command_empty_command(self):
        """测试空命令参数的错误处理"""
        with self.assertRaises(ValueError) as cm:
            execute_coverity_build_command("")

        self.assertIn("command is required and cannot be empty", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            execute_coverity_build_command("   ")

        self.assertIn("command is required and cannot be empty", str(cm.exception))

    def test_execute_coverity_build_command_invalid_timeout(self):
        """测试无效超时参数的错误处理"""
        with self.assertRaises(ValueError) as cm:
            execute_coverity_build_command(self.test_command, timeout_seconds=0)

        self.assertIn("timeout_seconds must be positive", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            execute_coverity_build_command(self.test_command, timeout_seconds=-10.0)

        self.assertIn("timeout_seconds must be positive", str(cm.exception))

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_executor_exception(self, mock_executor_class):
        """测试执行器抛出异常的情况"""
        # 配置 mock 抛出异常
        mock_executor = Mock()
        mock_executor._execute_command_internal.side_effect = RuntimeError("Execution failed")
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证结果是错误字符串
        self.assertIsInstance(result, str)
        self.assertIn("执行Coverity扫描编译命令", result)
        self.assertIn("Execution failed", result)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_timeout_error(self, mock_executor_class):
        """测试超时错误的情况"""
        # 配置 mock 抛出超时异常
        mock_executor = Mock()
        mock_executor._execute_command_internal.side_effect = TimeoutError("Command timed out")
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证结果是错误字符串
        self.assertIsInstance(result, str)
        self.assertIn("执行Coverity扫描编译命令", result)
        self.assertIn("Command timed out", result)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_permission_error(self, mock_executor_class):
        """测试权限错误的情况"""
        # 配置 mock 抛出权限异常
        mock_executor = Mock()
        mock_executor._execute_command_internal.side_effect = PermissionError("Permission denied")
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证结果是错误字符串
        self.assertIsInstance(result, str)
        self.assertIn("执行Coverity扫描编译命令", result)
        self.assertIn("Permission denied", result)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_complex_build_script(self, mock_executor_class):
        """测试复杂构建脚本的执行"""
        # 配置 mock
        complex_result = {
            "编译是否成功": True,
            "编译后信息": """=== COMPILATION SUCCESS ===
=== WARNING SUMMARY ===
unused variable 'temp' (occurred 3 times)
=== STATISTICS ===
Total lines processed: 150
Unique errors found: 0
Make errors found: 0
Warning types found: 1""",
            "编译耗时": 15.67
        }

        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = complex_result
        mock_executor_class.return_value = mock_executor

        # 测试复杂的构建命令
        complex_command = ". ./build.sh && make clean && make all"

        # 执行测试
        result = execute_coverity_build_command(
            command=complex_command,
            working_directory=self.temp_dir,
            timeout_seconds=1200.0
        )

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result["编译是否成功"])
        self.assertIn("WARNING SUMMARY", result["编译后信息"])
        self.assertGreater(result["编译耗时"], 10.0)

        # 验证调用参数
        mock_executor._execute_command_internal.assert_called_once_with(complex_command)

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_default_parameters(self, mock_executor_class):
        """测试默认参数的使用"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = self.mock_result
        mock_executor_class.return_value = mock_executor

        # 只使用必需参数执行测试
        result = execute_coverity_build_command(self.test_command)

        # 验证 BuildVerifyExecutor 使用了正确的默认参数
        mock_executor_class.assert_called_once_with(
            working_directory=None,
            timeout_seconds=300.0,
            environment_vars=None,
            max_output_size_kb=2048.0,
            validate_commands=True,
            allow_dangerous_commands=False
        )

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result["编译是否成功"])

    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_execute_coverity_build_command_with_environment_variables(self, mock_executor_class):
        """测试带环境变量的执行"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = self.mock_result
        mock_executor_class.return_value = mock_executor

        # 设置环境变量
        env_vars = {
            "COVERITY_HOME": "/opt/coverity",
            "LD_LIBRARY_PATH": "/opt/coverity/lib",
            "CC": "gcc",
            "CXX": "g++"
        }

        # 执行测试
        result = execute_coverity_build_command(
            command=self.test_command,
            environment_vars=env_vars
        )

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result["编译是否成功"])

        # 验证环境变量传递
        call_args = mock_executor_class.call_args
        self.assertEqual(call_args[1]['environment_vars'], env_vars)


class TestExecuteCoverityBuildCommandIntegration:
    """集成测试类（使用 pytest 语法）"""

    @pytest.mark.parametrize("command,expected_type", [
        ("echo 'Test command'", dict),
        ("ls -la", dict),
        ("echo 'Multiple'; echo 'commands'", dict),
    ])
    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_various_commands(self, mock_executor_class, command, expected_type):
        """测试各种不同的命令"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = {
            "编译是否成功": True,
            "编译后信息": "Success",
            "编译耗时": 1.0
        }
        mock_executor_class.return_value = mock_executor

        # 执行测试
        result = execute_coverity_build_command(command)

        # 验证结果类型
        assert isinstance(result, expected_type)

    @pytest.mark.parametrize("timeout", [1.0, 60.0, 300.0, 1800.0])
    @patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor')
    def test_various_timeouts(self, mock_executor_class, timeout):
        """测试各种超时设置"""
        # 配置 mock
        mock_executor = Mock()
        mock_executor._execute_command_internal.return_value = {
            "编译是否成功": True,
            "编译后信息": "Success",
            "编译耗时": timeout / 10
        }
        mock_executor_class.return_value = mock_executor

        # # 执行测试
        # result = execute_coverity_build_command(
        #     "echo 'test'",
        #     timeout_seconds=timeout
        # )

        # 验证超时参数传递
        call_args = mock_executor_class.call_args
        assert call_args[1]['timeout_seconds'] == timeout


def run_example_test():
    """运行示例测试用例"""
    print("运行 execute_coverity_build_command 示例测试:")
    print("=" * 60)

    # 示例 1: 基本用法
    print("\n1. 基本用法测试:")
    try:
        with patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor._execute_command_internal.return_value = {
                "编译是否成功": True,
                "编译后信息": "=== COMPILATION SUCCESS ===\n=== STATISTICS ===\nTotal lines processed: 10",
                "编译耗时": 2.34
            }
            mock_executor_class.return_value = mock_executor

            result = execute_coverity_build_command("echo 'Testing Coverity build command'")
            print(f"✓ 执行成功: {result}")
    except Exception as e:
        print(f"✗ 执行失败: {e}")

    # 示例 2: 带参数的用法
    print("\n2. 带参数用法测试:")
    try:
        with patch('ai_agents.supervisor_agents.detected_static_repair.build_runner.BuildVerifyExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor._execute_command_internal.return_value = {
                "编译是否成功": False,
                "编译后信息": "=== COMPILATION FAILED ===\n=== UNIQUE COMPILATION ERRORS ===\nerror: main.c:10: undefined reference",
                "编译耗时": 5.67
            }
            mock_executor_class.return_value = mock_executor

            result = execute_coverity_build_command(
                command="make all",
                working_directory="/tmp/test_project",
                timeout_seconds=600.0,
                environment_vars={"CC": "gcc", "CFLAGS": "-Wall"},
                validate_project=False
            )
            print(f"✓ 带参数执行: {result}")
    except Exception as e:
        print(f"✗ 带参数执行失败: {e}")

    # 示例 3: 错误处理测试
    print("\n3. 错误处理测试:")
    try:
        execute_coverity_build_command("")
        print("✗ 空命令应该抛出异常")
    except ValueError as e:
        print(f"✓ 正确处理空命令错误: {e}")

    print("\n=" * 60)
    print("示例测试完成!")


if __name__ == "__main__":
    # 运行示例测试
    run_example_test()

    # 运行单元测试
    print("\n运行完整单元测试套件:")
    unittest.main(argv=[''], exit=False, verbosity=2)
