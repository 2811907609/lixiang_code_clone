import os
import subprocess
import shutil
from pathlib import Path
from ai_agents.supervisor_agents.haloos_unit_test.function_extractor_tool import analyze_function_internal_macro_combinations,conditional_macros,convert_macros_to_gcc_flags,analyze_function_macro_nesting_and_config
from ai_agents.supervisor_agents.haloos_unit_test.dependency_file_validator import check_dependency_file_by_two_stage
from ai_agents.supervisor_agents.haloos_unit_test.parse_c_file_get_function_info import CFunctionLocator
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config

def get_function_conditional_micro(function_name:str)->str:
    """
    分析指定函数内部的条件编译宏组合，生成测试所需的宏配置组合列表。

    该工具通过分析函数内部的条件编译指令（如 #if、#ifdef、#ifndef、#elif、#else 等），
    生成所有可能的宏配置组合，用于生成单元测试的条件编译组合。

    Args:
        function_name (str): 要分析的函数名称

    Returns:
        str: 格式化的条件编译组合信息，包含以下几种情况：
             - 如果存在条件编译组合：返回格式化的组合列表，每行包含一个组合
             - 如果没有条件编译：返回提示信息表明函数不需要考虑条件编译
             - 如果解析失败：返回错误提示信息

    Raises:
        无显式异常抛出，所有异常都被捕获并返回错误信息字符串

    Examples:
        >>> # 分析函数的条件编译组合
        >>> result = get_function_conditional_micro('GetCoreID')
        >>> print(result)
        GetCoreID内需要测试的条件编译组合如下:
          组合 1: ['PLATFORM_ARM=1', 'DEBUG_MODE=1']
          组合 2: ['PLATFORM_ARM=1', 'DEBUG_MODE=0']
          组合 3: ['PLATFORM_ARM=0', 'DEBUG_MODE=1']

        >>> # 没有条件编译的函数
        >>> result = get_function_conditional_micro('SimpleFunction')
        >>> print(result)
        SimpleFunction函数不需要考虑条件编译，直接测试即可

    Note:
        - 函数内部会自动处理嵌套的条件编译指令和复合条件表达式
        - 支持 &&、|| 等逻辑操作符以及各种比较操作符（==、!=、>、<、>=、<=）
    """

    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file = haloos_global_env_config.SOURCE_FILE_NAME

    user_test_file = os.path.join(working_directory, 'src', source_file)

    # 一个文件多个函数同名的定义，都展示
    use_multi_definition_function_show = True
    special_macro_conditional = '0=1'

    locator = CFunctionLocator(user_test_file,use_clang=True)
    functions_info_original = locator.get_function_info(function_name)

    function_info_list = [functions_info_original]
    if use_multi_definition_function_show:
        for function_info_multi in functions_info_original.other_function_definitions:
            for func_key, func_info_item in function_info_multi.items():
                function_info_list.append(func_info_item)
        # 排序
        function_info_list.sort(key=lambda func_info: func_info.start_line)

    try:
        final_return_info = []
        for functions_info in function_info_list:
            analysis_micro_result = []

            function_name_original = functions_info.name
            function_start_line = functions_info.start_line
            function_end_line = functions_info.end_line

            if not functions_info:
                final_return_info.append(f"{function_name_original}:{function_start_line}-{function_end_line}函数未找到，请自己确定函数是否存在以及其对应的条件编译组合")
                continue

            line_range = [functions_info.start_line, functions_info.end_line]
            # 特殊条件编译宏处理
            external_condition = analyze_function_macro_nesting_and_config(user_test_file, line_range, remove_comment=True)

            # 基于clang函数没找到，暂时不测试
            if not external_condition and not isinstance(external_condition, list):
                final_return_info.append(f"{function_name_original}:{function_start_line}-{function_end_line}被 #if 0裹或其他原因,不需要测试该函数。")
                continue

            if special_macro_conditional in external_condition:
                final_return_info.append(f"{function_name_original}:{function_start_line}-{function_end_line}被 #if 0裹或其他原因,不需要测试该函数。")
                continue

            result = analyze_function_internal_macro_combinations(user_test_file, line_range,remove_comment=True, repair_macro_order=True)
            for i, combination in enumerate(result):
                # 避免 组合 1: []
                if len(combination) > 0:
                    analysis_micro_result.append(f"  组合 {i+1}: {combination}")

            if len(analysis_micro_result) > 0:
                introduce = f'{function_name_original}:{function_start_line}-{function_end_line}内需要测试的条件编译组合如下:'
                return_info = introduce + '\n' + "\n".join(analysis_micro_result)
                final_return_info.append(return_info)
                continue
            else:
                return_info = f"{function_name_original}:{function_start_line}-{function_end_line}函数内没有需要考虑的条件编译宏，该函数生成测试用例时不需要考虑条件编译宏，直接测试即可"
                final_return_info.append(return_info)
                continue
        return '\n'.join(final_return_info)
    except Exception:
        return f"工具解析失败，请自行判断{function_name}内的条件编译组合"

def compile_with_configs(main_source: str) -> str:
    """
    使用多种宏配置对C语言源文件进行批量编译验证，检测编译兼容性。

    该工具专门用于验证C语言代码在不同宏配置下的编译兼容性，采用GCC编译器
    对源文件进行多轮编译测试。自动管理构建目录，收集编译错误信息，
    为条件编译代码的质量保证提供完整的编译验证解决方案。

    核心功能特性：
    - 自动获取编译条件宏的信息：多种宏配置逐一进行编译测试
    - 批量编译验证：对多种宏配置逐一进行编译测试
    - 自动构建管理：自动创建和清理build目录，避免文件冲突
    - 编译参数优化：使用适合C语言项目的GCC编译参数组合
      * 标准：C99 (-std=c99)
      * 调试：启用调试信息 (-g) 和关闭优化 (-O0)
      * 警告控制：抑制警告但保留错误 (-w)
      * 兼容性：处理static、inline等关键字重定义
    - 错误信息收集：详细记录每个配置的编译失败原因
    - 超时保护：防止编译过程无限等待
    - 包含路径配置：自动设置test/support、src、mock等标准路径

    Args:
        main_source (str): 主源文件路径，要编译的C语言源文件
                          支持相对路径和绝对路径

    Returns:
        str: 编译结果描述字符串
        - "编译成功": 所有配置都编译成功
        - 详细错误信息: 包含失败配置的宏定义和具体错误原因
          格式包含配置编号、宏定义、错误信息等

    Raises:
        无异常抛出：所有错误都会被捕获并作为返回字符串的一部分

    Examples:
        # 完整的C语言项目验证流程
        >>> source_file = "src/Os_Syscall.c"
        >>> compile_result = compile_with_configs(source_file)
        >>> if compile_result == "编译成功":
        ...     print("所有宏配置编译通过，代码质量良好")
        ... else:
        ...     print(f"发现编译问题：\n{compile_result}")
    """
    # 1，规范性检测

    # 规范性检测
    check_info = check_dependency_file_by_two_stage()
    if len(check_info) > 0:
        return '\n'.join(check_info)
    else:
        print("依赖文件规范性检测通过")

    # 编译
    configs = conditional_macros(main_source)
    # 转换为gcc编译标志格式
    gcc_configs = convert_macros_to_gcc_flags(configs)


    # 项目路径
    project_dir = Path(".")
    build_dir = project_dir / "build_gcc"

    def clean_build():
        """清理构建目录"""
        if build_dir.exists():
            shutil.rmtree(build_dir)

    # 编译前清理构建目录
    clean_build()

    # 创建构建目录
    build_dir.mkdir(exist_ok=True)

    # GCC 编译参数 - 将特定警告当作错误处理
    gcc_flags = [
        "-fno-common",
        "-Wno-attributes",
        "-Wno-unknown-pragmas",
        "-Wstrict-prototypes",
        "-std=c99",
        "-g",
        "-O0",
        # "-Werror=implicit-function-declaration",  # 将隐式函数声明当作错误
        "-Werror=return-type"                     # 将返回类型不匹配当作错误
    ]

    # 包含路径 - 基于main_source所在目录计算相对路径
    source_dir = Path(main_source).parent.parent  # 从src目录回到项目根目录
    support_dir = source_dir / "test" / "support"
    include_paths = [f"-I{support_dir}"]

    success_count = 0
    error_messages = []

    # 如果没有宏配置，至少进行一次基础编译
    if not gcc_configs:
        gcc_configs = [[]]  # 空的宏配置列表，进行基础编译

    # for 循环编译所有配置
    for i, config_flags in enumerate(gcc_configs):
        output_file = build_dir / f"Os_Syscall_config_{i+1}.o"

        # 构建编译命令
        cmd = (["gcc", "-c"] + gcc_flags + include_paths + config_flags +
               ["-Dstatic=", "-Dinline=", "-Dinline_function="] +
               [str(main_source), "-o", str(output_file)])

        try:
            # 静默编译，只捕获错误输出
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"Sus cmpile in conditional : {cmd}")
                success_count += 1
            else:
                # 收集错误信息
                stderr_output = result.stderr.strip()
                if stderr_output:
                    error_msg = f"编译配置 {i+1} 失败:\n宏定义: {' '.join(config_flags)}\n错误信息:\n{stderr_output}\n{'-' * 40}"
                    error_messages.append(error_msg)
                    break
        except subprocess.TimeoutExpired:
            error_msg = f"编译配置 {i+1} 超时:\n宏定义: {' '.join(config_flags)}\n{'-' * 40}"
            error_messages.append(error_msg)
        except Exception as e:
            error_msg = f"编译配置 {i+1} 异常:\n宏定义: {' '.join(config_flags)}\n异常信息: {e}\n{'-' * 40}"
            error_messages.append(error_msg)
            break

    # 编译后清理构建目录
    clean_build()

    total_count = len(gcc_configs)

    if success_count == total_count and not error_messages:
        return "编译成功"
    else:
        return "\n".join(error_messages) if error_messages else "编译失败"
