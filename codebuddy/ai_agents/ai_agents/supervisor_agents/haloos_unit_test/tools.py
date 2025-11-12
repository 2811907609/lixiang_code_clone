"""
HaloOS单元测试工具模块
提供覆盖率分析和函数调用统计功能
"""

import os
import re
import glob
from typing import Optional, Dict
from pathlib import Path
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import CFunctionLocator
from ai_agents.supervisor_agents.haloos_unit_test.gcov_line_coverage_parser import get_formatted_code_with_coverage_improved
def _read_coverage_html(html_file_path) -> str:
    """
    读取覆盖率报告HTML文件内容

    Returns:
        str: HTML文件内容

    Raises:
        FileNotFoundError: 如果覆盖率报告文件不存在
        IOError: 如果读取文件失败
    """
    if not os.path.exists(html_file_path):
        raise FileNotFoundError(f"覆盖率报告文件不存在: {html_file_path}")

    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except IOError as e:
        raise IOError(f"读取覆盖率报告文件失败: {e}") from e


def get_coverage_data(html_file_path) -> Dict[str, Dict]:
    """
    获取覆盖率数据 - 统一的覆盖率获取函数
    兼容新格式(GCovr)和老格式(Ceedling)的覆盖率报告
    """
    source_file_name = haloos_global_env_config.SOURCE_FILE_NAME

    # 老格式正则 - 3列表格
    old_pattern = r'<tr><td><a[^>]*>([^<\s]+)\s+\([^)]*\)</a></td><td>([^<]+)</td><td>([^<]+)</td></tr>'

    # 新格式正则 - 5列表格 (GCovr格式)
    new_pattern = r'<tr><td><a[^>]*>([^<\s]+)\s+\([^)]*\)</a></td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td></tr>'

    # 文件名提取正则，兼容两种格式
    file_pattern = r'<tr><td><a[^>]*>[^<\s]+\s+\(([^):]+):\d+\)</a></td>'

    try:
        content = _read_coverage_html(html_file_path)

        # 检测报告格式
        is_new_format = _detect_report_format(content)

        # 加入文件名检测，模型输入的文件名可能不规范
        file_matches = re.findall(file_pattern, content)
        unique_files = list(set(file_matches))

        if source_file_name is not None:
            # 检测文件名列表长度是否为1
            if len(unique_files) == 0:
                pass
            elif len(unique_files) > 1:
                file_list_str = ', '.join(unique_files)
                error_msg = f"ERROR: 检测到测试个数大于一个: {file_list_str}，测试测试的文件是{source_file_name}"
                print(error_msg)
                return error_msg
            else:
                tested_source_file = unique_files[0]
                if source_file_name not in tested_source_file:
                    error_msg = f"ERROR: 测试的不是期望的源文件{source_file_name}，请测试源文件而不是测试现在的文件{tested_source_file}"
                    print(error_msg)
                    return error_msg

        # 根据格式选择相应的解析方式
        if is_new_format:
            return _parse_new_format_coverage(content, new_pattern)
        else:
            return _parse_old_format_coverage(content, old_pattern)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"覆盖率报告文件不存在: {html_file_path}") from e
    except Exception as e:
        raise Exception(f"解析覆盖率报告时发生错误: {e}") from e


def _detect_report_format(content: str) -> bool:
    """
    检测覆盖率报告格式

    Returns:
        bool: True表示新格式(GCovr), False表示老格式(Ceedling)
    """

    # 检查表头列数来判断格式
    # 新格式有5列：Function, Call count, Line coverage, Branch coverage, Block coverage
    # 老格式有3列：Function, Call count, Coverage
    if "Branch coverage" in content and "Block coverage" in content and 'Line coverage' in content:
        return True

    return False

def _parse_new_format_coverage(content: str, pattern: str) -> Dict[str, Dict]:
    """
    解析新格式(GCovr)覆盖率数据
    """
    matches = re.findall(pattern, content)
    results = {}

    for match in matches:
        function_name_found = match[0].strip()
        call_count = match[1].strip()
        line_coverage = match[2].strip()  # Line coverage
        branch_coverage = match[3].strip()  # Branch coverage
        block_coverage = match[4].strip()   # Block coverage

        results[function_name_found] = {
            'function_name': function_name_found,
            "call_count": call_count,
            "coverage_rate": line_coverage,  # 保持向后兼容，使用line coverage作为主要覆盖率
            "line_coverage": line_coverage,
            "branch_coverage": branch_coverage,
            "block_coverage": block_coverage
        }

    return results


def _parse_old_format_coverage(content: str, pattern: str) -> Dict[str, Dict]:
    """
    解析老格式(Ceedling)覆盖率数据
    """
    matches = re.findall(pattern, content)
    results = {}

    for match in matches:
        function_name_found = match[0].strip()
        call_count = match[1].strip()
        coverage_rate = match[2].strip()

        results[function_name_found] = {
            'function_name': function_name_found,
            "call_count": call_count,
            "coverage_rate": coverage_rate
        }

    return results


def add_detailed_report_for_function(results, functions_infos, detail_html_file_path):
    # 无相关key增加
    if not os.path.exists(detail_html_file_path):
        return results

    for function_name in results.keys():

        # # 覆盖率解析
        func_info_with_function_name = functions_infos.get(function_name, None)

        if not func_info_with_function_name:
            continue
        else:
            start_line = func_info_with_function_name.start_line
            end_line = func_info_with_function_name.end_line
            detail_line_report, uncover_line_report = get_formatted_code_with_coverage_improved(detail_html_file_path, start_line, end_line)
            results[function_name]['detailed_report'] = detail_line_report
            results[function_name]['uncover_line_report_list'] = uncover_line_report
    return results

def use_uncover_line_fix_coverage_rate(results):
    for _, function_info in results.items():
        if 'detailed_report' not in function_info:
            continue
        if 'uncover_line_report_list' not in function_info:
            continue

        uncover_line_report = function_info['uncover_line_report_list']
        detail_line_report = function_info['detailed_report']
        coverage_rate = function_info['coverage_rate']

        coverage_rate = float(function_info['coverage_rate'].strip('%'))

        # 对于覆盖率很高的增加检测修复
        if coverage_rate > 99:
            remove_rate = int(len(uncover_line_report) / len(detail_line_report.split('\n')) * 100)
            remove_rate = max(remove_rate, 0)
            remove_rate = min(remove_rate, coverage_rate)
            coverage_rate = coverage_rate - remove_rate

        function_info['coverage_rate'] = f'{coverage_rate}%'

    return results




def get_coverage_report(function_name: Optional[str] = None) -> str:
    """
    获取当前目录下，格式化的覆盖率报告 - 专为AI Agent提供可读性良好的文本报告

    Args:
        function_name (Optional[str]): 要查询的函数名，如果为None则返回所有函数的覆盖率报告

    Returns:
        str: 格式化的覆盖率报告文本

    Examples:
        >>> # 获取特定函数的覆盖率报告
        >>> print(get_coverage_report(function_name="os_ipicall_recv_activate_task"))
        函数覆盖率报告
        ================
        os_ipicall_recv_activate_task | 调用次数: called 7 times | 覆盖率: 100.0%

        >>> # 默认获取当前ceedling项目下所有函数的覆盖率报告
        >>> print(get_coverage_report())
        函数覆盖率报告
        ================
        总计函数数量: 2

        1. os_ipicall_recv_activate_task | 调用次数: called 7 times | 覆盖率: 100.0%
        2. os_ipicall_get_event | 调用次数: not called | 覆盖率: 0.0%
    """

    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file_name = haloos_global_env_config.SOURCE_FILE_NAME
    source_file_path = os.path.join(working_directory,'src',source_file_name)

    # lx fix: 模型调用传入不会传入build这个目录，gcovr固定的
    # html_file_path = Path(f"{working_directory}") / "build" / "artifacts" / "gcov" / "gcovr" / "GcovCoverageResults.functions.html"

    # 修复___开头函数被过滤问题，最新获取覆盖率的路径
    html_file_path = Path(f"{working_directory}") / "build" / "artifacts" / "gcov" / "gcovr" / "include_internal_functions_coverage.functions.html"

    # 若前面编译失败报错没有这个文件，那么走默认的文件尝试
    if not os.path.exists(html_file_path):
        html_file_path = Path(f"{working_directory}") / "build" / "artifacts" / "gcov" / "gcovr" / "GcovCoverageResults.functions.html"

    # 使用通配符匹配
    gcover_base_path  = os.path.join(working_directory,'build/artifacts/gcov/gcovr')
    detail_html_file_path_match = glob.glob(f"{gcover_base_path}/GcovCoverageResults.*.c.*.html")
    if detail_html_file_path_match:
        detail_html_file_path = detail_html_file_path_match[0]
    else:
        detail_html_file_path = ''

    fix_report_coverage = True
    # 可能耗时思考是否开启
    locator = CFunctionLocator(source_file_path, use_clang=True)
    functions_infos = locator.functions_info

    single_function_detailed = ''

    try:
        # 获取所有函数的覆盖率
        results = get_coverage_data(html_file_path)
        results = add_detailed_report_for_function(results, functions_infos, detail_html_file_path)

        # 增加详细覆盖率
        if fix_report_coverage:
            # 修正覆盖率的值
            results = use_uncover_line_fix_coverage_rate(results)

        if not results:
            return "函数覆盖率报告\n================\n未找到任何函数覆盖率数据"

        if function_name:
            # 未找到函数信息
            if function_name not in results:
                return f"函数覆盖率报告\n================\n未找到函数: {function_name}"

        report_lines = ["函数覆盖率报告", "================"]


        # 单个函数报告
        if function_name:

            func_info = results[function_name]
            report_lines.append(
                f"{func_info['function_name']} | 调用次数: {func_info['call_count']} | 覆盖率: {func_info['coverage_rate']}"
            )

            coverage_rate = float(func_info['coverage_rate'].strip('%'))

            # 加入详细覆盖率报告，只打印覆盖率不足100的覆盖率
            if coverage_rate < 100:
                # 函数行
                gcvoer_detailed_content = func_info.get('detailed_report', None)

                if gcvoer_detailed_content:
                    single_function_detailed = '\n' + '函数覆盖率详细报告如下: \n' + gcvoer_detailed_content
                else:
                    single_function_detailed = ''
                #返回
        else:
            # 所有函数报告
            report_lines.append(f"总计函数数量: {len(results)}")
            report_lines.append("")
            function_index = 0
            for function_name, func_info in results.items():
                function_index += 1
                report_lines.append(
                    f"{function_index}. {func_info['function_name']} | 调用次数: {func_info['call_count']} | 覆盖率: {func_info['coverage_rate']}"
                )

        return "\n".join(report_lines) + single_function_detailed

    except Exception as e:
        return f"函数覆盖率报告\n================\n生成报告时发生错误: {e}"
