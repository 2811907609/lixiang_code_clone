"""
C函数定位器 - 用于在C源文件中查找函数的完整实现
可以处理FUNC宏、标准C函数、条件编译等复杂情况
"""


import os
from typing import Dict, List
from ai_agents.supervisor_agents.haloos_unit_test.parse_c_file_get_function_info import CFunctionLocator
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import FunctionInfo
def get_function_line_range(file_path, function_name,use_clang=True):
    locator = CFunctionLocator(file_path,use_clang)
    try:
        function_info = locator.get_function_info(function_name)
        return (function_info.start_line, function_info.end_line)
    except Exception:
        return None

# 基于函数名返回函数体
def get_function_body_by_name(function_name: str) -> str:
    """
    根据函数名获取函数的完整代码内容，包含上下文信息

    此函数为源文件的专用函数查找工具，能够获取源文件内指定函数的完整代码，
    包括函数前的注释、条件编译宏等上下文信息。适用于代码分析、测试生成等场景。

    Args:
        function_name (str): 要查询的函数名，必须是源文件中存在的函数

    Returns:
        str: 返回包含完整上下文的函数代码字符串，各行之间用换行符分隔
             如果函数不存在，返回错误信息字符串

    Examples:
        >>> # 获取ActivateTask函数的完整代码
        >>> code = get_function_line_by_name("ActivateTask")
        >>> print(code)
        /*
         * Activate a task
         */
        #if defined(CFG_TASK_ACTIVATION)
        FUNC(StatusType, OS_CODE) ActivateTask(TaskType TaskID) {
            // 函数实现...
        }
        #endif

        >>> # 查询不存在的函数
        >>> result = get_function_line_by_name("NonExistentFunction")
        >>> print(result)
        函数 'NonExistentFunction' 未找到

    Note:
        - 自动包含函数前的注释和预处理指令（如#if、#define等）
        - 返回的代码保持原始格式，包括缩进和空行
        - 此函数是对CFunctionLocator类功能的便捷封装

    Raises:
        FileNotFoundError: 当Os_Syscall.c文件不存在时可能抛出
        Exception: 当文件读取或解析失败时可能抛出
    """

    add_micro_introduce_begin = False #初版写法：在函数开始前拼接其外部包裹宏
    add_internal_function_info = True
    use_clang=True
    multi_definition_function_show = True

    # 源文件名
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file_name = haloos_global_env_config.SOURCE_FILE_NAME

    # 大文件全部编译很慢
    if not working_directory or not source_file_name:
        return "环境变量 TEST_REPO_PATH 或 SOURCE_FILE_NAME未设置"
    if not os.path.exists(working_directory):
        return f"目录 {working_directory} 不存在"

    file_path = os.path.join(working_directory,'src',source_file_name)

    locator = CFunctionLocator(file_path,use_clang)
    functions_info = locator.functions_info

    if function_name not in functions_info:
        return f"函数 '{function_name}' 未找到"

    function_info_list = []
    content_list = []

    if multi_definition_function_show:
        function_info_list = [functions_info[function_name]]
        for function_other_item in functions_info[function_name].other_function_definitions:
            for _, function_other_item_info in function_other_item.items():
                function_info_list.append(function_other_item_info)
        # 排序，加一个基于function_info的start_line的排序
        function_info_list.sort(key=lambda func_info: func_info.start_line)
    else:
        function_info_list = [functions_info[function_name]]
    for function_info_item in function_info_list:

        function_name_item = function_info_item.name
        function_start_line = function_info_item.start_line
        function_end_line = function_info_item.end_line

        # 获取包含上下文的代码行
        lines_with_context = locator.get_function_lines_with_context(function_info=function_info_item, include_comments=False, include_preprocessor=False)

        # 是否添加条件编译宏包裹
        if add_micro_introduce_begin:
            # 获取验证函数是否被条件编译宏包裹
            # recall_micro = get_function_wrapper_compile_micro(file_path,function_name)
            pass
        else:
            recall_micro = []

        if len(recall_micro) == 0:
            micro_msg = ''
        else:
            micro_msg = f'注意: 该函数被下面主控制宏包裹:{','.join(recall_micro)}，想要编译需要设置对应的主控制宏'

        # 追加额外读取信息
        if add_internal_function_info:
            internal_calls = extract_function_internal_calls(file_path, function_info_item, locator)
        else:
            internal_calls = ''

        if lines_with_context:
            content = '#' + function_name_item + f':{function_start_line}-{function_end_line}\n' + '\n'.join(lines_with_context)
            content = micro_msg + '\n' + content + '\n' + internal_calls
            content_list.append(content)

    return '\n\n'.join(content_list)


# 返回文件内所有函数信息
def get_all_functions_info(file_path: str) -> str:
    """
    获取指定C源文件中所有函数的详细信息

    此函数用于解析C源文件并提取其中所有函数的详细信息，包括函数名、
    返回类型、参数等。支持标准C函数和FUNC宏定义的函数。适用于代码分析、
    函数清单生成、测试覆盖率分析等场景。

    Args:
        file_path (str): 要分析的C源文件的完整路径

    Returns:
        str: 返回所有函数信息的字符串，每个函数一行，格式为：
             "返回类型 函数名(参数列表)"
             如果文件中没有函数，返回空字符串
             如果文件不存在或解析失败，可能抛出异常

    Examples:
        >>> # 获取Os_Syscall.c文件中所有函数信息
        >>> info = get_all_functions_info("/path/to/Os_Syscall.c")
        >>> print(info)
        StatusType ActivateTask(TaskType TaskID)
        StatusType TerminateTask(void)
        StatusType ChainTask(TaskType TaskID)
        StatusType Schedule(void)
        ...

        >>> # 分析空文件或无函数的文件
        >>> info = get_all_functions_info("/path/to/empty.c")
        >>> print(info)
        # 输出空字符串

    Note:
        - 自动识别FUNC宏和标准C函数定义
        - 支持跨行函数签名解析
        - 会跳过函数声明，只返回函数定义
        - 返回的函数信息按照在文件中出现的顺序排列
    Raises:
        FileNotFoundError: 当指定的源文件不存在时
        Exception: 当文件读取或解析失败时
    """
    # 只使用clang，避免if 0等特殊条件宏问题


    locator = CFunctionLocator(file_path,use_clang=True,only_use_clang=True)
    functions_infos = locator.functions_info
    return_info = [f'一共{len(functions_infos)}个函数']
    for _, func_info in functions_infos.items():
        return_info.append(str(func_info))
    return '\n'.join(return_info)

# 获取所有函数名
def get_all_functions_info_list(file_path: str,use_clang=False, only_use_clang=False):
    locator = CFunctionLocator(file_path,use_clang,only_use_clang)
    functions_infos = locator.functions_info
    return_info = []
    for _, func_info in functions_infos.items():
        return_info.append(str(func_info))
    return return_info


def extract_function_internal_calls(file_path: str, function_info: FunctionInfo, locator, add_extra_function_body_info=True) -> str:

    all_function_set = set()

    function_name = function_info.name
    function_start_line = function_info.start_line
    function_end_line = function_info.end_line
    # 检查函数是否存在
    if function_name not in locator.functions_info:
        return f"函数 '{function_name}:{function_start_line}-{function_end_line}' 在文件 {file_path} 中未找到"

    # 获取直接调用的函数
    direct_calls = locator.extract_function_calls(function_info)
    if not direct_calls:
        return f"函数 '{function_name}:{function_start_line}-{function_end_line}' 没有调用源文件内定义的其他函数"
    else:
        for direct_call_item in direct_calls:
            all_function_set.add(direct_call_item)

    # 获取嵌套调用关系
    nested_calls = locator.extract_nested_function_calls(function_info)

    # 格式化输出
    result = [f"##函数 '{function_name}:{function_start_line}-{function_end_line}' 内部调用分析:\n"]

    # 直接调用列表
    result.append(f"**{function_name}:{function_start_line}-{function_end_line}直接调用的源文件内函数**:")
    for func in sorted(direct_calls):
        result.append(f"- {func}")

    # 嵌套调用关系
    if nested_calls:
        result.append(f"\n**{function_name}:{function_start_line}-{function_end_line}的嵌套调用关系:**")
        for caller, callees in nested_calls.items():
            if callees:  # 只显示有调用其他函数的函数
                callees_str = ", ".join(sorted(callees))
                result.append(f"{caller} -> {callees_str}")

            for call_item in callees:
                all_function_set.add(call_item)
    function_extral_body_list = []
    if add_extra_function_body_info:
        for add_extra_function_item in all_function_set:
            # todo:不同条件编译不同实现
            add_extra_function_info = locator.get_function_info(add_extra_function_item)
            if add_extra_function_info:
                function_extral_body = locator.get_function_lines_with_context(function_info=add_extra_function_info,include_comments=False,include_preprocessor=False)
            else:
                function_extral_body = []
            function_extral_body = '\n'.join(function_extral_body)

            function_extral_body_list.append(function_extral_body)

    result.append(f"\n**{function_name}:{function_start_line}-{function_end_line}依赖内部函数的具体实现**:")
    result.extend(function_extral_body_list)

    return "\n".join(result)


def get_function_calls_simple(file_path: str, function_name: str,use_clang=False) -> List[str]:
    """
    简单版本：获取指定函数直接调用的本文件内函数列表

    Args:
        file_path (str): C源文件路径
        function_name (str): 函数名

    Returns:
        List[str]: 被调用的函数名列表，如果函数不存在返回空列表
    """
    locator = CFunctionLocator(file_path,use_clang)
    function_info = locator.get_function_info(function_name)
    if function_info:
        calls = locator.extract_function_calls(function_info)
        return calls if calls is not None else []
    else:
        return []


def get_function_calls_nested(file_path: str, function_name: str, max_depth: int = 5,use_clang=False) -> Dict[str, List[str]]:
    """
    获取指定函数的嵌套调用关系字典

    Args:
        file_path (str): C源文件路径
        function_name (str): 函数名
        max_depth (int): 最大递归深度，默认5层

    Returns:
        Dict[str, List[str]]: 嵌套调用关系字典，如果函数不存在返回空字典
    """
    locator = CFunctionLocator(file_path,use_clang)
    function_info = locator.get_function_info(function_name)
    if function_info:
        return locator.extract_nested_function_calls(function_info, max_depth)
    else:
        return {}
