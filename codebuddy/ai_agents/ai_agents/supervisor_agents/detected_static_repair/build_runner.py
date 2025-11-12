import subprocess
import time
import os
from typing import Optional, Dict, Any
from ai_agents.supervisor_agents.detected_static_repair.host_executor import AprHostExecutor
from ai_agents.supervisor_agents.detected_static_repair.coverity_compile_log_extractor_test import extract_coverity_compile_info

"""
基于HostExecutor的Ceedling测试运行工具函数

提供针对Ceedling测试框架的专用执行工具，特别优化了ceedling test all命令的执行。
"""
"""
Optimized Coverity build command execution tool.

Provides specialized execution tools for Coverity static analysis build commands,
with proper error handling and comprehensive logging.
"""



class BuildVerifyExecutor(AprHostExecutor):
    """
    Build verification executor for Coverity static analysis build commands.

    This specialized executor extends HostExecutor to provide enhanced functionality
    for executing Coverity build commands with comprehensive error handling,
    build result extraction, and structured output formatting.
    """
    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout_seconds: float = 240.0,
        environment_vars: Optional[Dict[str, str]] = None,
        max_output_size_kb: float = 1024.0,
        validate_commands: bool = True,
        allow_dangerous_commands: bool = False
    ):
        super().__init__(
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            environment_vars=environment_vars,
            max_output_size_kb=max_output_size_kb,
            validate_commands=validate_commands,
            allow_dangerous_commands=allow_dangerous_commands
        )
        print(f'工作目录={self.working_directory}')

    def execute_command_internal(self, command: str) -> str:
        """Internal method to execute commands with full error handling."""
        start_time = time.time()

        # Validate inputs
        if not command or not command.strip():
            raise ValueError("command is required and cannot be empty")

        command = command.strip()

        # Validate command safety if requested
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

        # Log the operation
        self.logger.info(f"Executing host command: {command} (cwd: {self.working_directory}, timeout: {self.timeout_seconds}s)")

        try:
            # Execute the command using shell to support complex commands
            result = subprocess.run(
                command,
                cwd=self.working_directory,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True,
                env=self.env,
                shell=True
            )

            # Process output
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            returncode = result.returncode
            std_full = stdout + stderr

            # Calculate execution time
            execution_time = time.time() - start_time
            if ('build' in command or 'cov' in command ) and 'cp' not in command:
                    # 解析编译信息
                info_txt, bool_compile_ok = extract_coverity_compile_info(compile_info_txtpath=std_full)
                return_dict = {
                    "编译是否成功": bool_compile_ok,
                    "编译后信息": info_txt,
                    "编译耗时": execution_time
                }

            else:
                return_dict={
                    'stdout':stdout,
                    'stderr':stderr,
                    'returncode':returncode,
                    'execution_time':execution_time
                }
            # Log the completion
            self.logger.info(f"Host command completed with exit code {result.returncode} in {execution_time:.2f}s")
            return return_dict

        except subprocess.TimeoutExpired as e:
            error_msg = f"Command '{command}' timed out after {self.timeout_seconds} seconds"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg) from e

        except PermissionError as e:
            error_msg = f"Permission denied when executing command '{command}': {e}"
            self.logger.error(error_msg)
            raise PermissionError(error_msg) from e

        except OSError as e:
            error_msg = f"Failed to execute command '{command}': {e}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error executing command '{command}': {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def execute_coverity_build_command(
    # command: str='. ./rebuild.sh',
    # # working_directory: Optional[str] = None,
    # working_directory: Optional[str] = '/home/chehejia/programs/lixiang/cov-evalution/mvbs',
    timeout_seconds: float = 300.0,
    environment_vars: Optional[Dict[str, str]] = None,
    validate_project: bool = True
) -> Dict[str, Any]:
    """执行 Coverity 静态分析构建命令。

    该函数封装了 Coverity 构建流程的执行逻辑，使用 BuildVerifyExecutor 提供
    安全的命令执行环境，并返回结构化的构建结果信息。主要用于静态缺陷修复
    工作流中的代码编译和分析准备阶段。

    工作机制：
        1. 验证输入参数的有效性
        2. 从环境变量 WORK_DIR 获取工作目录
        3. 执行固定的构建脚本 './rebuild.sh'
        4. 收集并返回构建结果和执行时间

    Args:
        timeout_seconds (float, optional):
            命令执行超时时间（秒）。超时后将强制终止执行。默认值：300.0
        environment_vars (Optional[Dict[str, str]], optional):
            构建过程中的额外环境变量。这些变量将传递给构建脚本。默认值：None
        validate_project (bool, optional):
            是否在执行前验证项目结构和命令安全性。建议保持启用。默认值：True

    Returns:
        Dict[str, Any]: 构建结果字典，包含以下键值：
            - "编译是否成功" (bool): 构建是否成功完成
            - "编译后信息" (str): 构建过程的详细日志和输出信息
            - "编译耗时" (float): 实际执行时间（秒）

    Raises:
        ValueError: 当 timeout_seconds 小于等于 0 时抛出
        RuntimeError: 当构建过程中发生意外错误时抛出

    Note:
        - 构建命令和工作目录都是预配置的，无法通过参数修改
        - 函数依赖环境变量 WORK_DIR，请确保正确设置
        - 构建失败时不会抛出异常，而是在返回字典中标记失败状态
        - 建议在调用前检查 './rebuild.sh' 脚本的存在和可执行权限

    Examples:
        >>> # 基础用法
        >>> result = execute_coverity_build_command()
        >>> if result["编译是否成功"]:
        ...     print(f"构建成功，耗时: {result['编译耗时']:.1f}秒")
        ...     print(f"构建日志: {result['编译后信息']}")

        >>> # 使用自定义超时和环境变量
        >>> result = execute_coverity_build_command(
        ...     timeout_seconds=600.0,
        ...     environment_vars={"BUILD_TYPE": "Debug", "VERBOSE": "1"}
        ... )
    """
    # command_rm='rm -rf ./out'
    # rebuild_sh_path=f"{os.environ['FILES_DIRPATH']}/rebuild.sh"
    # command_cp=f"cp {rebuild_sh_path} ./ "
    command='./rebuild.sh'
    # working_directory: Optional[str] = None,
    # work_dir = '/home/chehejia/programs/lixiang/cov-evalution/mvbs'
    work_dir=os.environ['WORK_DIR']
    print(f"Executing Coverity build command: {command},work_dir={work_dir}")
    # Validate inputs
    if not command or not command.strip():
        raise ValueError("command is required and cannot be empty")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    # Create BuildVerifyExecutor instance
    host_executor = BuildVerifyExecutor(
        working_directory=work_dir,
        timeout_seconds=timeout_seconds,
        environment_vars=environment_vars,
        max_output_size_kb=2048.0,  # Larger output buffer suitable for Coverity output
        validate_commands=validate_project,
        allow_dangerous_commands=False
    )

    try:
        # return host_executor._execute_command_internal(command)
        # host_executor.execute_command_internal(command_rm)
        # host_executor.execute_command_internal(command_cp)
        return host_executor.execute_command_internal(command)
    except Exception as e:
        error_msg = f"执行Coverity扫描编译命令 '{command}' 时发生错误: {e}"
        return error_msg
