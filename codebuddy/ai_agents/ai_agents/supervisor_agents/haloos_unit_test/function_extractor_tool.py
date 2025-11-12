"""
函数代码提取器
只提供两个核心API，所有逻辑封装在函数内部
"""

import re
import os
from typing import Optional, List
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import CFunctionLocator
from ai_agents.supervisor_agents.haloos_unit_test.macro_extractor import _parse_function_internal_macro_structure,_generate_all_internal_macro_combinations,_parse_compound_expression, _parse_single_condition,fix_micro_combinations_order,filter_function_calls_from_macro_configs,filter_developer_special_value
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import remove_comments_with_mapping, is_valid_c_identifier

def extract_function_by_lines(file_path: str, start_line: int, end_line: int) -> Optional[str]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return None

    # 检查行号范围
    if start_line < 1 or end_line < 1 or start_line > len(lines) or end_line > len(lines):
        return None

    if start_line > end_line:
        return None

    # 提取指定范围的代码（转换为0-based索引）
    selected_lines = lines[start_line - 1:end_line]
    return ''.join(selected_lines).rstrip('\n')


def analyze_function_macro_nesting_and_config(file_path, line_range=[], remove_comment=True):
    """
    分析函数被哪些宏条件嵌套包裹，直接返回宏配置的一维列表

    Args:
        file_path: C文件路径
        function_name: 函数名

    Returns:
        list: 一维列表，包含一组宏配置
              例如: ['PLATFORM_ARM=1', 'DEBUG_MODE=1'] 或 [] (无宏嵌套)
              如果函数未找到或发生错误，返回 []
    """

    # 函数未找到，目前改为不需要测试。
    if line_range is None:
        return None  # 函数未找到，返回None

    start_line, end_line = line_range

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 去除注释，去除前后行映射
    if remove_comment:
        file_content = ''.join(lines)
        file_content, _ = remove_comments_with_mapping(file_content)
        lines = file_content.split('\n')

    # 重新设计算法：构建完整的宏结构树，然后找到函数所在的路径
    macro_blocks = _parse_macro_structure(lines)


    # 找到包含函数的宏路径
    function_path = _find_function_macro_path(macro_blocks, start_line)
    # 生成宏配置集合
    config_list = _generate_macro_config_list(function_path)

    return config_list  # 直接返回一维列表

def _check_branch_contains_error(lines, start_line, end_line):
    """检查指定行范围内是否包含 #error 指令（忽略嵌套的宏结构）"""
    if end_line is None:
        end_line = len(lines)

    nesting_level = 0
    for i in range(start_line - 1, min(end_line, len(lines))):
        line = lines[i].strip()

        # 如果是分支起始行，跳过（不算入内容检查）
        if i == start_line - 1 and (line.startswith('#if') or line.startswith('#elif') or line.startswith('#else')):
            continue

        # 跟踪嵌套级别
        if line.startswith('#if'):
            nesting_level += 1
        elif line.startswith('#endif'):
            nesting_level -= 1
        elif line.startswith('#error') and nesting_level == 0:
            # 只有在当前分支层级（nesting_level == 0）的 #error 才算
            return True
    return False


def _parse_macro_structure(lines):
    """解析文件中的完整宏结构"""
    blocks = []
    stack = []


    for line_num, line in enumerate(lines):
        line = line.strip()
        line_number = line_num + 1

        if line.startswith('#if'):
            # 开始一个新的条件块
            if line.startswith('#ifdef'):
                condition_type = 'ifdef'
            elif line.startswith('#ifndef'):
                condition_type = 'ifndef'
            else:
                condition_type = 'if'

            block = {
                'type': condition_type,
                'condition': line,
                'line_number': line_number,
                'branches': [],
                'current_branch': {
                    'type': condition_type,
                    'condition': line,
                    'line_number': line_number,
                    'start_line': line_number,
                    'end_line': None,
                    'children': []
                }
            }

            if stack:
                stack[-1]['current_branch']['children'].append(block)
            else:
                blocks.append(block)

            stack.append(block)

        elif line.startswith('#elif'):
            if stack:
                # 结束当前分支，检查是否包含 #error
                current_block = stack[-1]
                current_block['current_branch']['end_line'] = line_number - 1

                # 检查当前分支是否包含 #error，如果不包含才添加到分支列表
                branch_start = current_block['current_branch']['start_line']
                branch_end = current_block['current_branch']['end_line']
                if not _check_branch_contains_error(lines, branch_start, branch_end):
                    current_block['branches'].append(current_block['current_branch'])

                current_block['current_branch'] = {
                    'type': 'elif',
                    'condition': line,
                    'line_number': line_number,
                    'start_line': line_number,
                    'end_line': None,
                    'children': []
                }

        elif line.startswith('#else'):
            if stack:
                # 结束当前分支，检查是否包含 #error
                current_block = stack[-1]
                current_block['current_branch']['end_line'] = line_number - 1

                # 检查当前分支是否包含 #error，如果不包含才添加到分支列表
                branch_start = current_block['current_branch']['start_line']
                branch_end = current_block['current_branch']['end_line']
                if not _check_branch_contains_error(lines, branch_start, branch_end):
                    current_block['branches'].append(current_block['current_branch'])

                current_block['current_branch'] = {
                    'type': 'else',
                    'condition': line,
                    'line_number': line_number,
                    'start_line': line_number,
                    'end_line': None,
                    'children': []
                }

        elif line.startswith('#endif'):
            if stack:
                # 结束当前条件块，检查最后一个分支是否包含 #error
                current_block = stack.pop()
                current_block['current_branch']['end_line'] = line_number

                # 检查最后一个分支是否包含 #error，如果不包含才添加到分支列表
                branch_start = current_block['current_branch']['start_line']
                branch_end = current_block['current_branch']['end_line']
                if not _check_branch_contains_error(lines, branch_start, branch_end):
                    current_block['branches'].append(current_block['current_branch'])

                current_block['end_line'] = line_number
    return blocks

def _find_function_macro_path(macro_blocks, function_line):
    """在宏结构中找到包含函数的路径"""

    def search_in_blocks(blocks, current_path, parent_block=None):
        for block in blocks:
            for branch in block['branches']:
                # 检查函数是否在这个分支中
                if branch['start_line'] <= function_line <= (branch['end_line'] or float('inf')):
                    branch_info = {
                        'line_number': branch['line_number'],
                        'condition': branch['condition'],
                        'type': branch['type'],
                        'parent_block': block  # 传递当前块作为父块，用于else分支分析
                    }
                    new_path = current_path + [branch_info]

                    # 递归检查子块
                    child_path = search_in_blocks(branch['children'], new_path, block)
                    if child_path is not None:
                        return child_path
                    else:
                        return new_path
        return None

    result = search_in_blocks(macro_blocks, [])
    return result if result else []


def _generate_macro_config_list(macro_path):
    """根据宏路径生成配置列表（一维列表）"""
    if not macro_path:
        return []  # 无宏嵌套，返回空配置

    current_config = []

    for i, macro_info in enumerate(macro_path):
        condition_line = macro_info['condition']
        condition_type = macro_info['type']

        # 对于else分支，传递父块信息用于分析同级分支
        parent_block = macro_info.get('parent_block')

        config = _parse_macro_condition(condition_line, condition_type, parent_block)
        if config:  # 只有当config不为None时才添加
            # 检查是否是复合条件
            if isinstance(config, str) and config.startswith("COMPOUND:"):
                # 解析复合条件
                compound_configs = config[9:].split(",")  # 去掉 "COMPOUND:" 前缀
                current_config.extend(compound_configs)
            else:
                current_config.append(config)

    return current_config

def _parse_macro_condition(condition_line, condition_type, sibling_conditions=None):
    """解析单个宏条件，生成配置字符串

    支持的比较操作符：
    - == : MACRO_NAME == value → MACRO_NAME=value
    - != : MACRO_NAME != value → MACRO_NAME=0 (如果value!=0) 或 MACRO_NAME=1 (如果value==0)
    - >  : MACRO_NAME > value → MACRO_NAME=value+1
    - >= : MACRO_NAME >= value → MACRO_NAME=value
    - <  : MACRO_NAME < value → MACRO_NAME=value-1 (如果value>0，否则=0)
    - <= : MACRO_NAME <= value → MACRO_NAME=value

    支持的逻辑操作符：
    - && : 所有条件都必须满足 → 返回所有条件的配置列表
    - || : 只需要第一个条件满足 → 返回第一个条件的配置

    Returns:
        str or list: 对于简单条件返回单个配置字符串，对于复合条件返回配置列表
    """
    if condition_type == 'if':
        match = re.search(r'#if\s+(.+)', condition_line)
        if match:
            expr = match.group(1).strip()

            # 检查是否包含逻辑操作符
            if '&&' in expr or '||' in expr:
                # 使用新的复合表达式解析器
                configs = _parse_compound_expression(expr)
                # 对于复合条件，返回特殊格式标记，让上层函数知道这需要特殊处理
                if len(configs) > 1:
                    # 返回一个特殊标记，包含所有配置
                    return "COMPOUND:" + ",".join(configs)
                else:
                    return configs[0] if configs else None
            else:
                # 使用原有的单个条件解析逻辑
                return _parse_single_condition(expr)

    elif condition_type == 'ifdef':
        match = re.search(r'#ifdef\s+(\w+)', condition_line)
        if match:
            macro_name = match.group(1)
            return f"{macro_name}=1"

    elif condition_type == 'ifndef':
        match = re.search(r'#ifndef\s+(\w+)', condition_line)
        if match:
            # ifndef条件成立时，宏应该未定义，所以不返回任何配置
            return None  # 返回None表示不添加任何宏配置

    elif condition_type == 'elif':
        match = re.search(r'#elif\s+(.+)', condition_line)
        if match:
            expr = match.group(1).strip()

            # 与if条件相同的逻辑，支持逻辑操作符和比较操作符
            if '&&' in expr or '||' in expr:
                # 使用复合表达式解析器
                configs = _parse_compound_expression(expr)
                if len(configs) > 1:
                    return "COMPOUND:" + ",".join(configs)
                else:
                    return configs[0] if configs else None
            else:
                # 使用单个条件解析逻辑
                return _parse_single_condition(expr)

    elif condition_type == 'else':
        # 通用的else处理：从父块中分析同级分支条件
        return _generate_else_condition(sibling_conditions)

    return None


def _generate_else_condition(parent_block):
    """为else分支生成合适的宏配置"""
    if not parent_block or 'branches' not in parent_block:
        return None  # 无法分析时返回None

    # 分析同一个if块中的所有分支，提取宏名和已使用的值
    used_values = []
    macro_name = None

    # 查找同级的if/elif/ifdef分支以确定宏名和已使用的值
    for branch in parent_block['branches']:
        if branch['type'] in ['if', 'elif', 'ifdef']:
            condition = branch['condition']
            # 提取宏名和值 - 处理各种格式
            if '==' in condition:
                # 处理 #if (MACRO_NAME == value) 格式
                match = re.search(r'\(?\s*(\w+)\s*==\s*(\d+)\s*\)?', condition)
                if match:
                    macro_name = match.group(1)
                    used_values.append(int(match.group(2)))
            elif branch['type'] == 'if' and '>' in condition:
                # 处理 #if (MACRO_NAME > value) 格式
                match = re.search(r'\(?\s*(\w+)\s*>\s*(\d+)\s*\)?', condition)
                if match:
                    macro_name = match.group(1)
                    # 对于 >0 这样的条件，else应该是=0
                    if int(match.group(2)) == 0:
                        return f"{macro_name}=0"
            elif 'defined(' in condition:
                # 处理 #if defined(MACRO_NAME) 格式
                match = re.search(r'defined\s*\(\s*(\w+)\s*\)', condition)
                if match:
                    macro_name = match.group(1)
                    return f"{macro_name}=0"  # defined的else应该是未定义/0
            elif 'defined ' in condition:
                # 处理 #if defined MACRO_NAME 格式
                match = re.search(r'defined\s+(\w+)', condition)
                if match:
                    macro_name = match.group(1)
                    return f"{macro_name}=0"
            elif '#ifdef' in condition:
                # 处理 #ifdef MACRO_NAME 格式
                match = re.search(r'#ifdef\s+(\w+)', condition)
                if match:
                    macro_name = match.group(1)
                    #return f"{macro_name}=0"  # ifdef的else应该是未定义/0
                    return f"{macro_name}=**remove**"  # ifdef的else应该是未定义,但是后续排列组合要考虑其为定义情况，因此设置占位符
            else:
                # 处理简单的宏名格式，如 #if (MODE) 或 #elif (MACRO_NAME)
                if branch['type'] == 'if':
                    match = re.search(r'#if\s+\(?\s*(\w+)\s*\)?', condition)
                elif branch['type'] == 'elif':
                    match = re.search(r'#elif\s+\(?\s*(\w+)\s*\)?', condition)
                else:
                    match = None

                if match:
                    macro_name = match.group(1)
                    # 对于简单的宏名，如 #if (MODE)，else 分支应该是 MODE=0
                    # 因为 #if (MODE) 表示 MODE 为非0值时成立
                    # 但不立即返回，继续收集其他分支的信息
                    if not used_values:  # 如果还没有收集到具体的值
                        used_values.append(1)  # 假设简单宏名对应值1

    if macro_name and used_values:
        # 找一个未使用的值，通常else用0
        if 0 not in used_values:
            return f"{macro_name}=0"
        else:
            # 如果0已被使用，找最大值+1
            return f"{macro_name}={max(used_values) + 1}"

    # 如果无法确定合适的else条件，返回None
    return None


def analyze_function_internal_macro_combinations(file_path: str, line_range = [],remove_comment=True, repair_macro_order=True) -> List[List[str]]:
    """
    分析函数内部和外部的宏条件组合，生成所有可能的宏配置组合
    复用 _parse_macro_structure 和 _find_function_macro_path 的逻辑

    规则：
    1. #if #endif 只需要满足 #if 条件
    2. 对于有 #if #elif #else 的，每个分支都需要单独列出
    3. 对于同层的宏定义，生成笛卡尔积组合
    4. 对于嵌套的宏定义，递归处理
    5. 过滤掉函数调用格式的宏配置

    Args:
        file_path: C文件路径
        function_name: 函数名

    Returns:
        List[List[str]]: 二维列表，每个子列表包含一组宏配置
                        例如: [["MACRO1=1", "MACRO2=1"], ["MACRO1=1", "MACRO2=2"]]
                        如果函数未找到或无宏条件，返回 []
    """
    external_condition = analyze_function_macro_nesting_and_config(file_path, line_range, remove_comment=remove_comment)

    special_macro_conditional = '0=1'

    # # 首先获取函数的行范围
    # line_range = get_function_line_range(file_path, function_name,use_clang=use_clang)

    if line_range is None:
        return []  # 函数未找到，返回空列表

    # 空的为None，并且不是list
    if not external_condition and not isinstance(external_condition, list):
        external_condition = []

    # 如果函数被if 0包裹，不需要考虑条件编译组合
    if special_macro_conditional in external_condition:
        return []

    start_line, end_line = line_range

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 提取函数内部的代码行
    function_lines = lines[start_line-1:end_line]


    # 去除注释，去除前后行映射
    if remove_comment:
        function_content = ''.join(function_lines)
        function_content, _ = remove_comments_with_mapping(function_content)
        function_lines = function_content.split('\n')

    # 解析函数内部的宏结构
    internal_macro_blocks = _parse_function_internal_macro_structure(function_lines, start_line)

    # 生成所有可能的宏条件组合
    combinations = _generate_all_internal_macro_combinations(internal_macro_blocks)

    if len(combinations) != 0:
        combinations = [external_condition + c for c in combinations]
    else:
        combinations = [external_condition]

    if repair_macro_order:
        combinations = fix_micro_combinations_order(combinations)

    # 过滤掉函数调用格式的配置
    combinations = filter_function_calls_from_macro_configs(combinations)

    # 处理用户特殊值
    combinations = filter_developer_special_value(combinations)
    return combinations


def _merge_and_group_macro_configs(macro_list: List[str]) -> List[List[str]]:
    """
    按照用户需求处理宏配置列表

    规则：
    1. 对于值相同的宏进行合并
    2. 对于赋值不同的宏，组装成二维list

    例如：[aaa=1, bbb=1, bbb=2] -> [[aaa=1, bbb=1], [aaa=1, bbb=2]]

    Args:
        macro_list: 一维宏配置列表

    Returns:
        List[List[str]]: 二维列表，每个子列表包含一组宏配置组合
    """
    if not macro_list:
        return []

    # 按宏名分组，保持值的顺序
    macro_groups = {}
    macro_order = []  # 记录宏名出现的顺序

    for macro in macro_list:
        if '=' in macro:
            name, value = macro.split('=', 1)
            # 过滤掉无效的宏名：不能以数字开头，必须是有效的C标识符
            if not is_valid_c_identifier(name):
                continue
            if name not in macro_groups:
                macro_groups[name] = []
                macro_order.append(name)
            if value not in macro_groups[name]:
                macro_groups[name].append(value)

    # 如果所有宏都只有一个值，直接返回一个组合
    if all(len(values) == 1 for values in macro_groups.values()):
        result = []
        for name in macro_order:
            result.append(f"{name}={macro_groups[name][0]}")
        return [result] if result else []

    # 生成所有可能的组合
    from itertools import product

    value_combinations = []
    for name in macro_order:
        values = macro_groups[name]
        value_combinations.append([(name, value) for value in values])

    # 计算笛卡尔积
    result_combinations = []
    for combination in product(*value_combinations):
        config_list = [f"{name}={value}" for name, value in combination]
        result_combinations.append(config_list)
    return result_combinations

def convert_macros_to_gcc_flags(macro_configs: List[List[str]]) -> List[List[str]]:
    """
    将 conditional_macros 返回的宏配置转换为 gcc 编译器标志格式

    将格式从 'VCOS_MODULE_CONFIG_ISOLATE=1' 转换为 '-DVCOS_MODULE_CONFIG_ISOLATE=1'

    Args:
        macro_configs: conditional_macros 函数返回的二维列表
                      格式: [['MACRO1=1', 'MACRO2=0'], ['MACRO3=1']]

    Returns:
        List[List[str]]: gcc 编译器标志格式的二维列表
                        格式: [['-DMACRO1=1', '-DMACRO2=0'], ['-DMACRO3=1']]

    Examples:
        >>> configs = [['VCOS_MODULE_CONFIG_ISOLATE=1', 'DEBUG=0']]
        >>> gcc_flags = convert_macros_to_gcc_flags(configs)
        >>> print(gcc_flags)
        [['-DVCOS_MODULE_CONFIG_ISOLATE=1', '-DDEBUG=0']]
    """
    result = []

    for config_list in macro_configs:
        gcc_flags = []
        for macro_def in config_list:
            # 添加 -D 前缀
            gcc_flag = f"-D{macro_def}"
            gcc_flags.append(gcc_flag)

        if gcc_flags:
            result.append(gcc_flags)

    return result


def conditional_macros(file_path: str, remove_comment=True, repair_macro_order=True, use_clang=False) -> List[List[str]]:
    """
    从C文件中提取所有函数的宏条件，并按照用户需求合并处理

    对于值一样的合并成一个，如果赋值不一样的，则将其组装成一个二维的list
    例如：[aaa=1, bbb=1, bbb=2] -> [[aaa=1, bbb=1], [aaa=1, bbb=2]]

    Args:
        file_path: C文件路径

    Returns:
        List[List[str]]: 二维列表，每个子列表包含一组宏配置组合
    """

    locator = CFunctionLocator(file_path,use_clang)
    functions_infos = locator.functions_info
    func_dict = dict()
    for _, func_info in functions_infos.items():
        func_dict[func_info.name] = func_info
        for item in func_info.other_function_definitions:
            for item_key, item_info in item.items():
                func_dict[item_key] = item_info

    all_macro_configs = []
    # 收集所有函数的宏配置
    for _, func_info_item in func_dict.items():  # 修复：func_set 是集合，不是函数
        line_range = [func_info_item.start_line, func_info_item.end_line]
        result = analyze_function_internal_macro_combinations(file_path, line_range, remove_comment=remove_comment, repair_macro_order=repair_macro_order)
        if result:
            all_macro_configs.extend(result)

    # 如果没有宏配置，返回空列表
    if not all_macro_configs:
        return []

    # 将所有宏配置展平为一维列表
    flat_macros = []
    for config_list in all_macro_configs:
        flat_macros.extend(config_list)

    # 按照用户需求处理：合并相同值的宏，分组不同值的宏
    result = _merge_and_group_macro_configs(flat_macros)

    # 处理用户特殊值
    result = filter_developer_special_value(result)
    return result
