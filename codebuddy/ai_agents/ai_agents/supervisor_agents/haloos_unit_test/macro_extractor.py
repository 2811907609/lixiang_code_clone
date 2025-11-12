import re
from itertools import product
from typing import List, Dict
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import remove_comments_with_mapping,is_2d_list,is_conventional_macro_name,is_valid_c_identifier
def _parse_if_condition(condition_line: str) -> List[str]:
    """解析 #if 条件"""
    match = re.search(r'#if\s+(.+)', condition_line)
    if match:
        expr = match.group(1).strip()

        # 移除注释部分
        comment_match = re.search(r'/\*.*?\*/', expr)
        if comment_match:
            expr = expr[:comment_match.start()].strip()

        # 移除外层括号
        if expr.startswith('(') and expr.endswith(')'):
            expr = expr[1:-1].strip()

        # 解析条件表达式
        return _parse_condition_expression(expr)

    return []

def _parse_elif_condition(condition_line: str) -> List[str]:
    """解析 #elif 条件"""
    match = re.search(r'#elif\s+(.+)', condition_line)
    if match:
        expr = match.group(1).strip()
        # 移除外层括号
        if expr.startswith('(') and expr.endswith(')'):
            expr = expr[1:-1].strip()

        # 解析条件表达式
        return _parse_condition_expression(expr)

    return []


def _parse_ifdef_condition(condition_line: str) -> List[str]:
    """解析 #ifdef 条件"""
    match = re.search(r'#ifdef\s+(\w+)', condition_line)
    if match:
        macro_name = match.group(1)
        return [f"{macro_name}=1"]

    return []


def _parse_ifndef_condition(condition_line: str) -> List[str]:
    """解析 #ifndef 条件"""
    match = re.search(r'#ifndef\s+(\w+)', condition_line)
    if match:
        macro_name = match.group(1)
        return [f"{macro_name}=0"]

    return []


def _parse_else_condition_for_branch(parent_block: Dict) -> List[str]:
    """为 else 分支解析条件"""
    # 分析同一个 if 块中的所有分支，生成 else 条件
    used_conditions = []
    macro_name = None

    for branch in parent_block.get('branches', []):
        if branch['type'] in ['if', 'elif']:
            condition = branch['condition']
            # 提取宏名和值
            if '==' in condition:
                match = re.search(r'(\w+)\s*==\s*(\d+)', condition)
                if match:
                    macro_name = match.group(1)
                    used_conditions.append(int(match.group(2)))
        elif branch['type'] == 'ifdef':
            # 处理 #ifdef 条件的 else 分支
            condition = branch['condition']
            match = re.search(r'#ifdef\s+(\w+)', condition)
            if match:
                macro_name = match.group(1)
                # ifdef 的 else 分支表示宏未定义，使用 ***remove* 占位符
                return [f"{macro_name}=***remove*"]
        elif branch['type'] == 'ifndef':
            # 处理 #ifndef 条件的 else 分支
            condition = branch['condition']
            match = re.search(r'#ifndef\s+(\w+)', condition)
            if match:
                macro_name = match.group(1)
                # ifndef 的 else 分支表示宏已定义，设置为1
                return [f"{macro_name}=1"]

    if macro_name and used_conditions:
        # 生成一个未使用的值作为 else 条件
        else_value = max(used_conditions) + 1
        return [f"{macro_name}={else_value}"]

    return []

def _parse_compound_expression(expr):
    """解析复合表达式，支持 && 和 || 操作符，正确处理嵌套括号

    Args:
        expr: 表达式字符串，如 "((A == 1) || (B >= 2)) && (C == 1)"

    Returns:
        list: 配置字符串列表，对于 && 返回所有条件，对于 || 返回第一个条件
    """
    expr = expr.strip()

    # 检查括号匹配，如果不匹配则返回空结果
    bracket_count = 0
    for char in expr:
        if char == '(':
            bracket_count += 1
        elif char == ')':
            bracket_count -= 1
        if bracket_count < 0:  # 右括号多于左括号
            return []

    if bracket_count != 0:  # 左括号多于右括号
        return []

    # 移除最外层括号（如果存在）
    if expr.startswith('(') and expr.endswith(')'):
        # 检查是否是完整的外层括号
        bracket_count = 0
        for i, char in enumerate(expr):
            if char == '(':
                bracket_count += 1
            elif char == ')':
                bracket_count -= 1
                if bracket_count == 0 and i < len(expr) - 1:
                    # 不是完整的外层括号
                    break
        else:
            # 是完整的外层括号，移除它们
            expr = expr[1:-1].strip()

    # 寻找顶层的 || 操作符（优先级最低）
    bracket_count = 0
    or_positions = []

    for i, char in enumerate(expr):
        if char == '(':
            bracket_count += 1
        elif char == ')':
            bracket_count -= 1
        elif bracket_count == 0 and expr[i:i+2] == '||':
            or_positions.append(i)

    if or_positions:
        # 找到顶层的 ||，只处理第一个部分
        first_part = expr[:or_positions[0]].strip()
        return _parse_compound_expression(first_part)

    # 寻找顶层的 && 操作符
    bracket_count = 0
    and_positions = []

    for i, char in enumerate(expr):
        if char == '(':
            bracket_count += 1
        elif char == ')':
            bracket_count -= 1
        elif bracket_count == 0 and expr[i:i+2] == '&&':
            and_positions.append(i)

    if and_positions:
        # 找到顶层的 &&，处理所有部分
        configs = []
        parts = []
        start = 0

        for pos in and_positions:
            parts.append(expr[start:pos].strip())
            start = pos + 2
        parts.append(expr[start:].strip())  # 最后一部分

        for part in parts:
            part_configs = _parse_compound_expression(part)
            configs.extend(part_configs)

        return configs

    # 单个条件
    config = _parse_single_condition(expr)
    return [config] if config else []

def _clean_macro_name(macro_name):
    """清理宏名，移除 defined 等前缀"""
    macro_name = macro_name.strip()

    # 移除 defined( 前缀
    if macro_name.startswith('defined('):
        macro_name = macro_name[8:].rstrip(')')

    # 移除 defined 前缀
    elif macro_name.startswith('defined '):
        macro_name = macro_name[8:]

    # 移除其他可能的前缀和后缀
    macro_name = macro_name.strip().strip('()')

    # 只保留有效的宏名字符
    match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', macro_name)
    if match:
        return match.group(1)

    return macro_name

def _parse_single_condition(condition):
    """解析单个条件表达式

    Args:
        condition: 单个条件字符串，如 "MACRO_NAME == 1" 或 "defined(MACRO_NAME)"

    Returns:
        str: 配置字符串，如 "MACRO_NAME=1"，如果解析失败返回None
    """
    condition = condition.strip()

    # 检查是否包含函数调用格式，如果包含则直接返回None
    # 匹配类似 funcName() 的模式，但排除 defined(MACRO) 这种特殊情况
    if not condition.startswith('defined'):
        # 检查是否包含函数调用格式 identifier(...)
        if re.search(r'\w+\s*\([^)]*\)', condition):
            return None  # 跳过函数调用格式的条件

    # 安全地移除最外层匹配的括号（只有当整个字符串被完整的括号包围时）
    while condition.startswith('(') and condition.endswith(')'):
        # 检查括号是否匹配
        bracket_count = 0
        is_complete_bracket = True
        for i, char in enumerate(condition):
            if char == '(':
                bracket_count += 1
            elif char == ')':
                bracket_count -= 1
                if bracket_count == 0 and i < len(condition) - 1:
                    # 在字符串中间就bracket_count为0，说明不是完整的外层括号
                    is_complete_bracket = False
                    break

        if is_complete_bracket and bracket_count == 0:
            condition = condition[1:-1].strip()
        else:
            break

    # 处理 defined(MACRO_NAME) 格式
    defined_match = re.match(r'defined\s*\(\s*(\w+)\s*\)', condition)
    if defined_match:
        macro_name = defined_match.group(1)
        return f"{macro_name}=1"

    # 处理 defined MACRO_NAME 格式
    defined_match2 = re.match(r'defined\s+(\w+)', condition)
    if defined_match2:
        macro_name = defined_match2.group(1)
        return f"{macro_name}=1"

    # 按优先级检查操作符（先检查双字符操作符）
    if '!=' in condition:
        parts = condition.split('!=')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            macro_value = parts[1].strip()

            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)

            # 先判断是否是标准宏，调整位置
            if check_macro_in_standard_dict(macro_name) and not check_macro_in_standard_dict(macro_value):
                tmp_swap = macro_name
                macro_name = macro_value
                macro_value = tmp_swap

            # 相反
            if macro_value.isdigit():
                value = int(macro_value)
                if value in [0,1]:
                    result_value = 0 if value != 0 else 1
                else:
                    result_value = value + 1
                return f"{macro_name}={result_value}"
            # 不为None
            elif check_macro_in_standard_dict(macro_value):
                result_value = check_macro_in_standard_dict(macro_value, return_statard_value=True) + 1
                return f"{macro_name}={result_value}"
            # 兜底
            else:
                return f"{macro_name}=0"

    elif '==' in condition:
        parts = condition.split('==')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            macro_value = parts[1].strip()
            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)
            return f"{macro_name}={macro_value}"

    elif '>=' in condition:
        parts = condition.split('>=')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            macro_value = parts[1].strip()
            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)
            return f"{macro_name}={macro_value}"

    elif '<=' in condition:
        parts = condition.split('<=')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            macro_value = parts[1].strip()
            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)
            return f"{macro_name}={macro_value}"

    elif '>' in condition:
        parts = condition.split('>')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)
            try:
                macro_value = int(parts[1].strip()) + 1
                return f"{macro_name}={macro_value}"
            except ValueError:
                return f"{macro_name}={parts[1].strip()}"

    elif '<' in condition:
        parts = condition.split('<')
        if len(parts) == 2:
            macro_name = parts[0].strip()
            # 清理宏名中可能的 defined 前缀
            macro_name = _clean_macro_name(macro_name)
            try:
                value = int(parts[1].strip())
                macro_value = max(0, value - 1)
                return f"{macro_name}={macro_value}"
            except ValueError:
                return f"{macro_name}=0"

    else:
        # 简单的宏名，设置为1，但先清理可能的前缀
        clean_name = _clean_macro_name(condition)
        # 验证是否是有效的宏名：不能是纯数字，必须符合C标识符规范
        if clean_name.isdigit() or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', clean_name):
            return None  # 返回None表示无效的宏条件
        return f"{clean_name}=1"

    return None

def _parse_condition_expression(expr: str) -> List[str]:
    """解析条件表达式，支持复合条件"""
    # 检查是否包含逻辑操作符
    if '&&' in expr or '||' in expr:
        return _parse_compound_expression(expr)
    else:
        # 单个条件
        config = _parse_single_condition(expr)
        return [config] if config else []

def _parse_branch_condition(branch: Dict, parent_block: Dict) -> List[str]:
    """
    解析分支条件，生成配置列表
    """
    condition_line = branch.get('condition', '')
    condition_type = branch.get('type', '')

    parsed_conditions = []
    if condition_type == 'if':
        parsed_conditions = _parse_if_condition(condition_line)
    elif condition_type == 'elif':
        parsed_conditions = _parse_elif_condition(condition_line)
    elif condition_type == 'ifdef':
        parsed_conditions = _parse_ifdef_condition(condition_line)
    elif condition_type == 'ifndef':
        parsed_conditions = _parse_ifndef_condition(condition_line)
    elif condition_type == 'else':
        parsed_conditions = _parse_else_condition_for_branch(parent_block)
    return parsed_conditions if parsed_conditions else []

def _get_block_all_combinations(block: Dict) -> List[List[str]]:
    """
    获取一个宏块的所有可能分支组合
    """
    combinations = []

    for branch in block.get('branches', []):
        # 解析当前分支的条件
        branch_config = _parse_branch_condition(branch, block)

        # 处理子块
        child_combinations = []
        if branch.get('children'):
            child_blocks_combinations = []
            for child_block in branch['children']:
                child_combos = _get_block_all_combinations(child_block)
                if child_combos:
                    child_blocks_combinations.append(child_combos)

            # 计算子块的笛卡尔积
            if child_blocks_combinations:
                for child_combination in product(*child_blocks_combinations):
                    merged_child_config = []
                    for child_config in child_combination:
                        if isinstance(child_config, list):
                            merged_child_config.extend(child_config)
                        else:
                            merged_child_config.append(child_config)
                    child_combinations.append(merged_child_config)

        # 合并当前分支条件和子块条件
        if child_combinations:
            for child_config in child_combinations:
                final_config = branch_config + child_config if branch_config else child_config
                if final_config:
                    combinations.append(final_config)
        else:
            if branch_config:
                combinations.append(branch_config)

    return combinations

def _generate_all_internal_macro_combinations(macro_blocks: List[Dict],filter_conflicts=True) -> List[List[str]]:
    """
    生成所有可能的宏条件组合

    规则：
    1. 对于只有 #if #endif 的，只需要满足 #if 条件
    2. 对于有 #if #elif #else 的，每个分支都需要单独列出
    3. 对于同层的宏定义，生成笛卡尔积组合
    4. 对于嵌套的宏定义，递归处理
    """
    if not macro_blocks:
        return []

    # 获取顶层所有宏块的分支组合
    top_level_combinations = []

    for block in macro_blocks:
        block_combinations = _get_block_all_combinations(block)
        if block_combinations:
            top_level_combinations.append(block_combinations)

    # 如果没有有效的组合，返回空
    if not top_level_combinations:
        return []

    # 如果只有一个宏块，直接返回其组合
    if len(top_level_combinations) == 1:
        return top_level_combinations[0]

    # 多个宏块的情况，需要智能合并
    final_combinations = []

    # 首先收集所有条件，按宏名分组以检测冲突
    all_conditions = []
    for block_combinations in top_level_combinations:
        for combination in block_combinations:
            if combination:
                config_list = combination if isinstance(combination, list) else [combination]
                all_conditions.extend(config_list)

    # 预处理：纠正可能的顺序错误（STD_ON=MACRO -> MACRO=STD_ON）
    corrected_conditions = []
    for condition in all_conditions:
        if '=' in condition:
            left_part = condition.split('=')[0].strip()
            right_part = condition.split('=')[1].strip()

            # 检查是否是错误的顺序：STD_ON/STD_OFF 出现在左边
            if left_part in ['STD_ON', 'STD_OFF']:
                # 纠正顺序：STD_ON=MACRO -> MACRO=STD_ON
                corrected_condition = f"{right_part}={left_part}"
                corrected_conditions.append(corrected_condition)
            else:
                corrected_conditions.append(condition)
        else:
            corrected_conditions.append(condition)

    # 按宏名分组，检测冲突
    macro_groups = {}
    for condition in corrected_conditions:
        if '=' in condition:
            macro_name = condition.split('=')[0]
            if macro_name not in macro_groups:
                macro_groups[macro_name] = []
            macro_groups[macro_name].append(condition)

    # 识别有冲突的宏（同一个宏有多个不同值）
    conflicting_macros = {}
    non_conflicting_conditions = []

    for macro_name, conditions in macro_groups.items():
        unique_conditions = list(set(conditions))
        if len(unique_conditions) > 1:
            # 有冲突，每个值都是一个独立的选择
            conflicting_macros[macro_name] = unique_conditions
        else:
            # 无冲突，可以直接添加
            non_conflicting_conditions.extend(unique_conditions)

    # 生成组合策略
    if conflicting_macros:
        # 有冲突的情况：为每个冲突宏的每个值生成独立组合

        # 获取所有冲突宏的所有可能值组合
        conflict_macro_names = list(conflicting_macros.keys())
        conflict_values_lists = [conflicting_macros[name] for name in conflict_macro_names]

        for conflict_combination in product(*conflict_values_lists):
            # 每个冲突组合与非冲突条件合并
            base_combination = list(conflict_combination) + non_conflicting_conditions

            # 去重
            unique_config = []
            seen_configs = set()
            for config in base_combination:
                if config and config not in seen_configs:
                    seen_configs.add(config)
                    unique_config.append(config)

            if unique_config:
                final_combinations.append(unique_config)
    else:
        # 无冲突的情况：直接合并所有条件
        if non_conflicting_conditions:
            unique_config = []
            seen_configs = set()
            for config in non_conflicting_conditions:
                if config and config not in seen_configs:
                    seen_configs.add(config)
                    unique_config.append(config)

            if unique_config:
                final_combinations.append(unique_config)

    # 组合级别的去重：移除重复的组合
    unique_combinations = []
    seen_combinations = set()

    for combination in final_combinations:
        # 将组合排序后转换为元组，用于比较
        sorted_combination = tuple(sorted(combination))
        if sorted_combination not in seen_combinations:
            seen_combinations.add(sorted_combination)
            unique_combinations.append(combination)

    return unique_combinations

def _parse_function_internal_macro_structure(function_lines: List[str], function_start_line: int) -> List[Dict]:
    """
    解析函数内部的宏结构（基于原有的 _parse_macro_structure 逻辑）
    """
    blocks = []
    stack = []

    for relative_line_num, line in enumerate(function_lines):
        line = line.strip()
        absolute_line_number = function_start_line + relative_line_num

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
                'line_number': absolute_line_number,
                'branches': [],
                'current_branch': {
                    'type': condition_type,
                    'condition': line,
                    'line_number': absolute_line_number,
                    'start_line': absolute_line_number,
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
                # 结束当前分支，开始新分支
                current_block = stack[-1]
                current_block['current_branch']['end_line'] = absolute_line_number - 1
                current_block['branches'].append(current_block['current_branch'])

                current_block['current_branch'] = {
                    'type': 'elif',
                    'condition': line,
                    'line_number': absolute_line_number,
                    'start_line': absolute_line_number,
                    'end_line': None,
                    'children': []
                }

        elif line.startswith('#else'):
            if stack:
                # 结束当前分支，开始else分支
                current_block = stack[-1]
                current_block['current_branch']['end_line'] = absolute_line_number - 1
                current_block['branches'].append(current_block['current_branch'])

                current_block['current_branch'] = {
                    'type': 'else',
                    'condition': line,
                    'line_number': absolute_line_number,
                    'start_line': absolute_line_number,
                    'end_line': None,
                    'children': []
                }

        elif line.startswith('#endif'):
            if stack:
                # 结束当前条件块
                current_block = stack.pop()
                current_block['current_branch']['end_line'] = absolute_line_number
                current_block['branches'].append(current_block['current_branch'])
                current_block['end_line'] = absolute_line_number

    return blocks

def analyze_function_internal_macro_combinations_from_file(file_path: str,remove_comment=True,repair_macro_order=True,filter_conflicts=True) -> List[List[str]]:

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 提取函数内部的代码行
    function_lines = lines

    # 去除注释，去除前后行映射
    if remove_comment:
        function_content = ''.join(function_lines)
        function_content, _ = remove_comments_with_mapping(function_content)
        function_lines = function_content.split('\n')

    # 解析函数内部的宏结构
    internal_macro_blocks = _parse_function_internal_macro_structure(function_lines, 0)

    # 生成所有可能的宏条件组合
    combinations = _generate_all_internal_macro_combinations(internal_macro_blocks,filter_conflicts)

    if repair_macro_order:
        combinations = fix_micro_combinations_order(combinations)

    combinations = filter_function_calls_from_macro_configs(combinations)

    # 处理用户特殊值
    combinations = filter_developer_special_value(combinations)
    return combinations


def get_internal_macro_blocks_count(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 提取函数内部的代码行
    function_lines = lines

    # 解析函数内部的宏结构
    internal_macro_blocks = _parse_function_internal_macro_structure(function_lines, 0)

    return len(internal_macro_blocks)


def check_macro_in_standard_dict(macro_name, return_statard_value = False):
    """AUTOSAR标准值"""
    standard_values = {
        # 布尔状态值
        'STD_ON': 1,
        'STD_OFF': 0,
        'TRUE': 1,
        'FALSE': 0,

        # 错误码
        'E_OK': 0,          # 成功通常为0
        'E_NOT_OK': 1,      # 失败通常为1

        # 空指针
        'NULL_PTR': 0,
        'NULL': 0,

        # 调试和检测
        'DEV_ERROR_DETECT': 1,
        'DET_ENABLED': 1,

        # 存储类型 (通常作为枚举值)
        'AUTOMATIC': 0,
        'STATIC': 1,
        'TYPEDEF': 2,

        # 变量修饰符
        'CONST': 1,
        'VAR': 0,

        # 使能状态
        'ENABLED': 1,
        'DISABLED': 0,
        'ACTIVE': 1,
        'INACTIVE': 0,
        'ENABLE': 1,
        'DISABLE': 0
    }

    if not return_statard_value:
        if macro_name in standard_values.keys():
            return True
        else:
            return False
    else:
        return standard_values.get(macro_name, None)

#调整combinations的顺序
def fix_micro_combinations_order(micro_combinations):

    # 验证是否二维列表
    if not is_2d_list(micro_combinations):
        return micro_combinations

    sorted_micro_combinations = []

    for micro_conditional_list in micro_combinations:
        if len(micro_conditional_list) == 0:
            return micro_combinations

        sorted_micro_conditional_list = []
        # 循环检测每个组合顺序时候合格
        for macro_item in micro_conditional_list:
            if '=' in macro_item:
                macro_item_list = macro_item.split('=')
                left_macro_name = macro_item_list[0].strip()
                right_macro_name = macro_item_list[1].strip()

                # 检测规范性
                # 有些开发者写代码不规范，出现if (STD_OFF == CANNM)写法，导致后续解析把标准值解析为宏，没有很好的识别方法，目前直接基于autosar标准值解析
                if not is_conventional_macro_name(left_macro_name) or not is_conventional_macro_name(right_macro_name):
                    new_macro_item = macro_item
                elif left_macro_name.isdigit() and (not right_macro_name.isdigit()):
                    new_macro_item = right_macro_name + '=' + left_macro_name
                elif check_macro_in_standard_dict(left_macro_name) and not check_macro_in_standard_dict(right_macro_name):
                    new_macro_item = right_macro_name + '=' + left_macro_name
                else:
                    new_macro_item = macro_item
                sorted_micro_conditional_list.append(new_macro_item)
            else:
                sorted_micro_conditional_list.append(macro_item)

        sorted_micro_combinations.append(sorted_micro_conditional_list)

    return sorted_micro_combinations

def is_valid_macro_value(value: str) -> bool:
    """检查是否是有效的宏值"""
    if '**' in value:
        return False
    return True


def filter_developer_special_value(macro_configs):
    filtered_configs = []
    for config_list in macro_configs:
        filtered_config = []

    for config_list in macro_configs:
        filtered_config = []
        for macro in config_list:
            if '=' in macro:
                name, value = macro.split('=', 1)
                if not is_valid_macro_value(value):
                    continue
            filtered_config.append(macro)
        filtered_configs.append(filtered_config)
    return filtered_configs

def filter_function_calls_from_macro_configs(macro_configs: List[List[str]]) -> List[List[str]]:
    """
    过滤掉非宏定义的配置

    过滤规则：
    1. 函数调用格式：包含括号 '(' 或 ')'
    2. 非法标识符：不符合C语言标识符规范
    3. 特殊字符：包含空格、特殊符号等
    4. 数字开头：以数字开头的标识符
    5. C/C++语言关键字：过滤掉语言保留关键字

    Args:
        macro_configs: 二维列表，每个子列表包含一组宏配置

    Returns:
        List[List[str]]: 过滤后的宏配置二维列表
    """
    if not macro_configs:
        return []

    # C/C++ 语言关键字列表
    C_CPP_KEYWORDS = {
        # C 关键字
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'define',
        'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static',
        'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
        # C99 关键字
        'inline', 'restrict', '_Bool', '_Complex', '_Imaginary',
        # C11 关键字
        '_Alignas', '_Alignof', '_Atomic', '_Static_assert', '_Noreturn',
        '_Thread_local', '_Generic',
        # C++ 关键字
        'alignas', 'alignof', 'and', 'and_eq', 'asm', 'bitand', 'bitor',
        'bool', 'catch', 'class', 'compl', 'concept', 'const_cast', 'consteval',
        'constexpr', 'constinit', 'co_await', 'co_return', 'co_yield', 'decltype',
        'delete', 'dynamic_cast', 'explicit', 'export', 'false', 'friend',
        'mutable', 'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr',
        'operator', 'or', 'or_eq', 'private', 'protected', 'public', 'reflexpr',
        'reinterpret_cast', 'requires', 'static_assert', 'static_cast', 'template',
        'this', 'thread_local', 'throw', 'true', 'try', 'typeid', 'typename',
        'using', 'virtual', 'wchar_t', 'xor', 'xor_eq'
    }

    def is_valid_macro_name(name: str) -> bool:
        """检查是否是有效的宏名"""
        if not name or not isinstance(name, str):
            return False

        # 1. 过滤函数调用格式
        if '(' in name or ')' in name:
            return False

        # 2. 过滤包含特殊字符的（但保留运算符，因为用户要求删除表达式过滤）
        if any(char in name for char in [' ', '\t', '\n', '\r', '.', '[', ']', '{', '}', '"', "'"]):
            return False

        # 3. 必须符合C标识符规范
        if not is_valid_c_identifier(name):
            return False

        # 4. 过滤C/C++语言关键字
        if name.lower() in C_CPP_KEYWORDS:
            return False

        return True

    filtered_configs = []

    for config_list in macro_configs:
        filtered_config = []

        for macro in config_list:
            if '=' in macro:
                name, value = macro.split('=', 1)
                if is_valid_macro_name(name):
                    filtered_config.append(macro)
            else:
                # 对于没有等号的配置，直接检查整个字符串
                if is_valid_macro_name(macro):
                    filtered_config.append(macro)

        # 只有当过滤后的配置不为空时才添加
        # if filtered_config:
        filtered_configs.append(filtered_config)

    return filtered_configs
