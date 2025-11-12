"""
基于HostExecutor的Ceedling测试运行工具函数

提供针对Ceedling测试框架的专用执行工具，特别优化了ceedling test all命令的执行。
"""


import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict
from ai_agents.tools.execution.host.host_executor import HostExecutor
from ai_agents.supervisor_agents.haloos_unit_test.testcase_file_validator_tool import validate_all_testcase_file,validate_c_test_file,extract_tested_function_from_filename
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import get_all_functions_info_list
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from commonlibs.encoding.detect_content_encoding import safe_decode_byte_data

class CeedlingTestExecutor(HostExecutor):
    """
    Ceedling测试执行器

    继承自HostExecutor，重写_execute_command_internal方法以针对Ceedling命令进行优化。
    """

    def _execute_command_internal(self, command: str) -> str:
        """
        重写的命令执行方法，针对Ceedling命令进行优化

        Args:
            command: 要执行的命令

        Returns:
            str: 命令执行结果
        """
        start_time = time.time()

        # 验证输入
        if not command or not command.strip():
            raise ValueError("command is required and cannot be empty")

        command = command.strip()

        # 如果是ceedling命令，验证项目结构
        if command.startswith('ceedling') and not command.startswith('ceedling -T'):
            project_yml = Path(self.working_directory) / "project.yml"
            if not project_yml.exists():
                error_msg = f"错误: 目录 '{self.working_directory}' 不是有效的Ceedling项目（缺少project.yml文件）"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # 验证命令安全性
        if self.validate_commands:
            validation_result = self.command_validator.validate_command(command)
            if not validation_result.is_safe:
                error_msg = f"Command blocked for security reasons: {'; '.join(validation_result.violations)}"
                if validation_result.warnings:
                    error_msg += f" (Warnings: {'; '.join(validation_result.warnings)})"
                raise ValueError(error_msg)
            elif validation_result.warnings:
                for warning in validation_result.warnings:
                    self.logger.warning(f"Command security warning: {warning}")

        # 日志记录
        if command.startswith('ceedling'):
            self.logger.info(f"执行Ceedling命令: {command} (工作目录: {self.working_directory}, 超时: {self.timeout_seconds}s)")
        else:
            self.logger.info(f"执行命令: {command} (工作目录: {self.working_directory}, 超时: {self.timeout_seconds}s)")

        try:
            # 执行命令
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=False,  # 使用字节模式避免编码问题
                env=self.env,
                shell=True
            )

            stdout = safe_decode_byte_data(result.stdout) if result.stdout else ""
            stderr = safe_decode_byte_data(result.stderr) if result.stderr else ""


            # 截断过大的输出
            max_output_bytes = int(self.max_output_size_kb * 1024)

            if len(stdout.encode('utf-8')) > max_output_bytes:
                stdout = stdout[:max_output_bytes // 2] + f"\n\n... [输出截断 - 超过{self.max_output_size_kb}KB限制] ...\n\n"

            if stderr and len(stderr.encode('utf-8')) > max_output_bytes:
                stderr = stderr[:max_output_bytes // 2] + f"\n\n... [错误输出截断 - 超过{self.max_output_size_kb}KB限制] ...\n\n"

            # 计算执行时间
            execution_time = time.time() - start_time

            # 格式化结果
            result_lines = [
                f"命令: {command}",
                f"工作目录: {self.working_directory}",
                f"退出代码: {result.returncode}",
                f"执行状态: {'成功' if result.returncode == 0 else '失败'}",
                f"执行时间: {execution_time:.2f}秒"
            ]

            # 针对ceedling命令优化输出显示
            if ('ceedling test' in command or 'ceedling gcov' in command) and 'verbosity=4' not in command:
                # 对于测试和覆盖率命令，提取关键信息
                if stdout:
                    pass
            else:
                # 对于其他命令，正常显示输出
                if stdout:
                    result_lines.extend([
                        "",
                        "=== STDOUT ===",
                        stdout.rstrip()
                    ])

            if stderr:
                result_lines.extend([
                    "",
                    "=== ERRORS ===",
                    stderr.rstrip()
                ])

            if not stdout and not stderr:
                result_lines.append("(无输出)")

            # 记录完成日志
            self.logger.info(f"命令执行完成，退出代码: {result.returncode}，耗时: {execution_time:.2f}秒")

            return "\n".join(result_lines)

        except subprocess.TimeoutExpired as e:
            error_msg = f"命令 '{command}' 在 {self.timeout_seconds} 秒后超时"

            if 'ceedling test' in command or 'ceedling gcov' in command:
                error_msg += '\n！！！ERROR: 严重报错，测试超时！！代码可能存在无限循环、死锁或其他导致测试卡住的问题。可能原因：测试用例内mock函数或其他设置出错，导致出现死循环，请立即修复！！若修复不成功请函数可能存在问题的测试用例。'

            self.logger.error(error_msg)
            raise TimeoutError(error_msg) from e

        except PermissionError as e:
            error_msg = f"执行命令 '{command}' 时权限不足: {e}"
            self.logger.error(error_msg)
            raise PermissionError(error_msg) from e

        except OSError as e:
            error_msg = f"执行命令 '{command}' 失败: {e}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e

        except Exception as e:
            error_msg = f"执行命令 '{command}' 时发生意外错误: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def validate_ceedling_project(working_directory: str) -> bool:
    """
    验证指定目录是否为有效的Ceedling项目

    Args:
        working_directory: 要检查的目录路径

    Returns:
        bool: 如果是有效的Ceedling项目返回True
    """
    project_yml = Path(working_directory) / "project.yml"
    return project_yml.exists() and project_yml.is_file()


def execute_ceedling_command(
    command: str,
    working_directory: Optional[str] = None,
    timeout_seconds: float = 300.0,
    environment_vars: Optional[Dict[str, str]] = None,
    validate_project: bool = True
) -> str:
    """
    执行Ceedling命令的通用函数

    Args:
        command: 要执行的Ceedling命令
        working_directory: 工作目录路径，如果为None则使用当前目录
        timeout_seconds: 命令执行超时时间，默认5分钟
        environment_vars: 额外的环境变量
        validate_project: 是否验证Ceedling项目结构

    Returns:
        str: 命令执行结果
    """
    # CeedlingTestExecutor
    host_executor = CeedlingTestExecutor(
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        environment_vars=environment_vars,
        max_output_size_kb=2048.0,  # 更大的输出缓冲区适合ceedling输出
        validate_commands=True,
        allow_dangerous_commands=False
    )

    # 验证Ceedling项目结构
    if validate_project and not validate_ceedling_project(host_executor.working_directory):
        error_msg = f"错误: 目录 '{host_executor.working_directory}' 不是有效的Ceedling项目（缺少project.yml文件）"
        return error_msg

    try:
        return host_executor._execute_command_internal(command)
    except Exception as e:
        error_msg = f"执行Ceedling命令 '{command}' 时发生错误: {e}"
        return error_msg


def run_ceedling_test_all(
    run_cmd,
    working_directory: Optional[str] = None,
    timeout_seconds: float = 600.0,
    environment_vars: Optional[Dict[str, str]] = None
) -> str:
    """
    执行ceedling test:all命令

    这是最常用的Ceedling测试命令，会运行所有测试用例。

    Args:
        working_directory: 工作目录路径
        timeout_seconds: 命令执行超时时间
        environment_vars: 额外的环境变量

    Returns:
        str: 测试执行结果
    """
    # 保证清空
    execute_ceedling_command(
            'ceedling clobber',
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            environment_vars=environment_vars
        )


    return execute_ceedling_command(
        run_cmd,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        environment_vars=environment_vars
    )

# 规范性检测

def compile_ceedling_repo(test_file_name: str=None) -> str:
    """
    规范性检测、编译、运行、测试Ceedling项目的检测工具。

    该函数执行两个主要步骤:
    1. 测试文件规范性检测 - 验证所有测试用例文件格式是否正确
    2. Ceedling编译、运行、测试 -
        - 若传入test_file_name，则对该测试文件进行编译和运行测试，并生成覆盖率报告: ceedling gcov:test_file_name
        - 若不传入，则对对当前整个ceedling项目进行编译和运行测试: ceedling gcov:all

    Args:
        test_file_name: 可选，传入则检测、编译、运行、测试传入的测试文件，不传入则测试整个工程

    Returns:
        str: 测试执行结果，可能的返回值包括:
            - 规范性检测失败时: 具体的错误信息，如:
                * "环境变量 TEST_REPO_PATH 未设置"
                * "目录 {path} 不存在"
                * 测试文件格式验证失败的具体信息
                * Ceedling编译或测试执行错误信息
            - 规范性检测成功时: Ceedling编译运行的结果
    Raises:
        无异常抛出。所有错误情况都通过返回字符串形式的错误消息处理，
        确保调用方能够获得明确的错误信息而不会因为异常导致程序崩溃。

    Examples:
        >>> result = compile_ceedling_repo(test_ChainTask.c) # 编译、运行、测试传入的测试用例文件
        >>> print(result)  # 显示详细的测试结果或错误信息
        >>> result = compile_ceedling_repo() # 编译、运行、测试整个ceedling工程
        >>> print(result)  # 显示详细的测试结果或错误信息
    """
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file_name = haloos_global_env_config.SOURCE_FILE_NAME

    # 大文件全部编译很慢
    # timeout_seconds = 300
    timeout_seconds = 600 #默认设置一个大的值

    if not working_directory or not source_file_name:
        return "环境变量 TEST_REPO_PATH 未设置"
    if not os.path.exists(working_directory):
        return f"目录 {working_directory} 不存在"

    source_file_path = os.path.join(working_directory,'src',source_file_name)

    # 编译逻辑：
    try:
        if not test_file_name:

            run_cmd = "ceedling gcov:all"
            timeout_seconds = 600

            # 1. 先规范性检测
            format_file_flag, format_file_msg = validate_all_testcase_file()
        else:
            test_file_name = test_file_name.strip()
            timeout_seconds = 90 #编译单个文件如果超过90秒，认为有死循环
            if test_file_name.startswith("test/"):
                test_file_name = test_file_name.replace('test/','')

            try:
                assert test_file_name.endswith('.c')
            except Exception:
                return "传入测试用例文件不以.c结尾"

            # 单文件检测，避免后期编译速度受影响
            all_functions = get_all_functions_info_list(source_file_path,use_clang=True)
            tested_function_name = extract_tested_function_from_filename(test_file_name, all_functions)

            format_file_flag, format_file_msg = validate_c_test_file(test_file_name,tested_function_name, check_all_file_name=True, all_functions_list=all_functions)

            test_file_name = test_file_name.replace(".c",'')

            # run_cmd = f"ceedling test:{test_file_name}"
            run_cmd = f"ceedling gcov:{test_file_name}"

        # 如果规范性存在问题直接返回
        if not format_file_flag:
            return format_file_msg

    except Exception:
        run_cmd = "ceedling gcov:all"

    try:

        use_verbosity = False # 暂不打开，一种信息更多的编译

        # 2. 再编译检测
        compile_msg = run_ceedling_test_all(
                                        run_cmd,
                                        working_directory=working_directory
                                        ,timeout_seconds=timeout_seconds)
        # 2.1 编译debug: 如果编译单个文件发现，带着verbose再编译一次
        error_special_msg = 'use_backtrace to use the :gdb option to find the cause'
        if error_special_msg in compile_msg and test_file_name and use_verbosity:
            run_cmd += ' --verbosity=4'
            compile_msg = run_ceedling_test_all(
                                            run_cmd,
                                            working_directory=working_directory
                                        ,timeout_seconds=timeout_seconds)

        # 2.2 覆盖率修复：___开头文件被过滤，project.yaml文件配置gcovr依然过滤，目前暂时解法
        # merge-use-line-min：使用最小的行号
        execute_ceedling_command(
                'gcovr -r . --html-details --include-internal-functions --merge-mode-functions=merge-use-line-min -o build/artifacts/gcov/gcovr/include_internal_functions_coverage.html',
                working_directory=working_directory,
                timeout_seconds=10,
        )

        return compile_msg

    except Exception as e:
        return f"执行ceedling test时发生错误: {e}"

if __name__ == '__main__':
    msg = compile_ceedling_repo()
    print(msg)
