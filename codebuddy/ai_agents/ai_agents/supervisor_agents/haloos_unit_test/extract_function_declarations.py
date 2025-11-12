"""
函数声明提取工具
使用tree-sitter从C头文件中提取函数声明，重点解析函数名和行号
"""

import os
import tree_sitter
from typing import List, Dict, Optional,Tuple
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import get_all_functions_info_list
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import get_c_parser,is_only_uppercase_letters_with_underscore
from ai_agents.supervisor_agents.haloos_unit_test.use_treesitter_extract_function_macro import FunctionMacroDetector
def extract_function_declarations_dict(file_path: str) -> Dict[str, Dict]:
    """
    从指定的C头文件中提取函数声明，返回字典格式

    Args:
        file_path (str): 头文件路径

    Returns:
        Dict[str, Dict]: 包含函数声明信息的字典，键为函数名
        每个字典包含: name, line_number, declaration
    """
    declarations = extract_function_declarations(file_path)
    return {decl['name']: decl for decl in declarations}


def extract_function_declarations(file_path: str) -> List[Dict]:
    """
    使用tree-sitter从指定的C头文件中提取函数声明

    Args:
        file_path (str): 头文件路径

    Returns:
        List[Dict]: 包含函数声明信息的字典列表
        每个字典包含: name, line_number, declaration
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"错误: 无法读取文件 - {e}")
        return []

    # 获取tree-sitter解析器
    parser, c_language = get_c_parser()

    # 解析代码
    tree = parser.parse(content.encode('utf-8'))

    # 提取函数声明
    return _extract_function_declarations_from_tree(tree, content)


def _extract_function_declarations_from_tree(tree: tree_sitter.Tree, content: str) -> List[Dict]:
    """
    从tree-sitter解析树中提取函数声明，使用遍历方式

    Args:
        tree: tree-sitter解析树
        content: 源代码内容

    Returns:
        List[Dict]: 函数声明信息列表
    """
    functions = []

    def traverse_node(node):
        """递归遍历节点"""
        # 检查是否是声明节点
        if node.type == 'declaration':
            function_info = _extract_function_from_declaration_node(node)
            if function_info:
                functions.append(function_info)

        # 递归遍历子节点
        for child in node.children:
            traverse_node(child)

    # 从根节点开始遍历
    traverse_node(tree.root_node)

    return functions

def _extract_function_from_declaration_node(declaration_node: tree_sitter.Node) -> Optional[Dict]:
    """
    从声明节点中提取函数信息

    Args:
        declaration_node: 声明节点

    Returns:
        Optional[Dict]: 函数信息字典或None
    """
    # 查找function_declarator节点
    function_declarator = None

    def find_function_declarator(node):
        nonlocal function_declarator
        if node.type == 'function_declarator':
            function_declarator = node
            return True

        for child in node.children:
            if find_function_declarator(child):
                return True
        return False

    # 在声明节点中查找function_declarator
    if not find_function_declarator(declaration_node):
        return None

    # 从function_declarator中提取函数名
    function_name = _extract_function_name_from_declarator(function_declarator)
    if not function_name:
        return None

    # 获取行号
    line_number = declaration_node.start_point[0] + 1

    # 获取完整声明文本
    declaration_text = declaration_node.text.decode('utf-8').strip()

    return {
        'name': function_name,
        'line_number': line_number,
        'declaration': declaration_text
    }

def _extract_function_name_from_declarator(function_declarator: tree_sitter.Node) -> Optional[str]:
    """
    从function_declarator节点中提取函数名

    Args:
        function_declarator: function_declarator节点

    Returns:
        Optional[str]: 函数名或None
    """
    def find_identifier(node):
        """递归查找第一个identifier节点"""
        if node.type == 'identifier':
            return node.text.decode('utf-8')

        for child in node.children:
            result = find_identifier(child)
            if result:
                return result

        return None

    # 在function_declarator的declarator子节点中查找函数名
    for child in function_declarator.children:
        if child.type in ['identifier', 'declarator', 'pointer_declarator']:
            function_name = find_identifier(child)
            if function_name:
                return function_name

    return None



def check_function_declarations(c_file_path: str, h_file_path: str, check_header_file_macro_format=False) -> Tuple[bool, List[str]]:
    """
    检查H文件中是否包含C文件中所有函数的声明。

    该工具从C文件中提取所有函数定义，然后检查H文件中是否包含对应的函数声明。
    返回检查结果和缺失声明列表的元组。

    功能特性：
    - 自动提取C文件中的函数定义（支持多种函数定义格式）
    - 智能匹配函数声明（忽略空白符差异）
    - 支持FUNC宏定义的函数格式
    - 排除静态函数和内联函数
    - 容错处理：文件读取失败时返回False和空列表

    Args:
        c_file_path (str): C源文件路径，用于提取函数定义
        h_file_path (str): 头文件路径，用于检查函数声明

    Returns:
        Tuple[bool, List[str]]: 元组包含：
            - bool: True表示有函数缺少声明，False表示H文件包含C文件的所有公共函数声明
            - List[str]: 缺失声明的函数名列表

    Examples:
        >>> success, missing = check_function_declarations("src/os_event.c", "include/os_event.h")
        >>> print(success)  # True
        >>> print(missing)  # []

        >>> success, missing = check_function_declarations("src/missing.c", "include/config.h")
        >>> print(success)  # False
        >>> print(missing)  # ['func1', 'func2']
    """
    try:
        # 检查C文件是否存在
        if not os.path.exists(c_file_path):
            return False, []

        # 检查H文件是否存在
        if not os.path.exists(h_file_path):
            h_file_path = h_file_path.split('/')[-1]
            return False, [f'{h_file_path}不存在，该文件应该存在并包含所有内部函数声明']

        # 提取C文件中的函数定义列表,use_clang=True
        c_functions = get_all_functions_info_list(c_file_path,use_clang=True)

        if not c_functions:
            # 如果C文件没有函数定义，返回True和空列表（没有需要检查的函数）
            return True, []

        # 提取函数声明前，只检测是否规范，不规范直接False
        if check_header_file_macro_format:
            with open(h_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                real_code = f.read()
            detector = FunctionMacroDetector(real_code)
            function_macros = detector.function_macros
            if len(function_macros) > 0:
                return_function_macros_info = []
                for function_macro_item in function_macros:
                    return_function_macros_info.append(f'{function_macro_item.full_text}:{function_macro_item.start_line}-{function_macro_item.end_line}')
                return True, return_function_macros_info
            else:
                return False, []

        # 提取H文件中的函数声明
        h_declarations = extract_function_declarations_dict(h_file_path)
        h_declarations = list(h_declarations.keys())

        # 检查每个C函数是否在H文件中有声明，收集缺失的函数
        missing_declarations = []

        for func_name in c_functions:
            if func_name not in h_declarations:
                missing_declarations.append(func_name)

        # 返回结果：缺少标志和缺失声明列表
        has_missing = len(missing_declarations) > 0

        return has_missing, sorted(missing_declarations)  # 排序便于查看

    except Exception:
        # 出现任何错误都返回False和空列表
        return False, []

def check_internal_function_if_in_external_header(c_file_path: str, h_file_path: str) -> Tuple[bool, List[str]]:
    try:
        # 检查C文件是否存在
        if not os.path.exists(c_file_path):
            return False, []

        # 检查H文件是否存在
        if not os.path.exists(h_file_path):
            h_file_path = h_file_path.split('/')[-1]
            return False, [f'{h_file_path}不存在']

        # 提取C文件中的函数定义列表
        c_functions = get_all_functions_info_list(c_file_path)

        if not c_functions:
            # 如果C文件没有函数定义，返回True和空列表（没有需要检查的函数）
            return True, []

        # 提取H文件中的函数声明
        h_declarations = extract_function_declarations_dict(h_file_path)
        h_declarations = list(h_declarations.keys())
        # 检查每个C函数是否在H文件中有声明，收集缺失的函数
        missing_declarations = []

        for func_name in c_functions:
            if func_name in h_declarations:
                missing_declarations.append(func_name)

        # 返回结果：缺少标志和缺失声明列表
        has_missing = len(missing_declarations) > 0
        return has_missing, sorted(missing_declarations)  # 排序便于查看
    except Exception:
        # 出现任何错误都返回False和空列表
        return False, []

def analyze_macro_definition(node):
    """分析宏定义的特征"""
    if node.type not in ['preproc_function_def']:
        return None

    children = node.children

    if len(children) < 2:
        return None
    if len(children) > 3:
        body_value = children[3]
        body_value = body_value.text.decode('utf-8')
    else:
        body_value = ''

    # 获取宏名称
    name_node = children[1]
    macro_name = name_node.text.decode('utf-8')

    # 获取宏定义内容
    if len(children) > 2:
        definition = children[2].text.decode('utf-8').strip()
    else:
        definition = ""

    return {
        'name': macro_name,
        'parameters': definition,
        'has_parameters': '(' in definition,
        'is_function_like': definition.endswith(')'),
        'definition_length': len(definition),
        'has_replacement': len(definition) > 0,
        'body_value':body_value,
        'full_content': node.text.decode('utf-8')
    }

def parse_preproc_function_def(code):
    """解析代码中的所有宏定义"""
    # 获取tree-sitter解析器
    parser, c_language = get_c_parser()

    tree = parser.parse(code.encode('utf-8'))

    macros_list = []

    def traverse(node):
        if node.type in ['preproc_function_def']:
            macro_info = analyze_macro_definition(node)
            macros_list.append(macro_info)

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return macros_list



def check_wrong_preproc_function_def(c_file):

    if not os.path.exists(c_file):
        return []

    with open(c_file, 'r', encoding='utf-8') as f:
        code = f.read()

    macros_list = parse_preproc_function_def(code)
    wrong_macro_list = []

    # 因为有的项目书写不规范，函数宏就用小写的
    for macro in macros_list:
        # 不是标准宏形式
        if not is_only_uppercase_letters_with_underscore(macro['name']):

            # 判断有无value且value是不是纯数字？
            if not macro['body_value']:  #表示把小写函数宏定义为0，目前认为极其不规范，禁止
                wrong_macro_list.append(macro)
            if macro['body_value'].isdigit():   # 把小写函数宏定义成常量，认为极其不规范
                wrong_macro_list.append(macro)

    return wrong_macro_list



# 获取函数的include 文件

def extract_file_include_statement(tree):
    # tree-sitter查询：查找所有#include预处理指令
    query_text = """
    (preproc_include
    path: (string_literal) @include_path
    )
    (preproc_include
    path: (system_lib_string) @include_path
    )
    """

    parser,C_LANGUAGE = get_c_parser()
    query = C_LANGUAGE.query(query_text)
    captures = query.captures(tree.root_node)

    include_path_list = []

    if "include_path" in captures:
        # get all include include_path
        for node in captures["include_path"]:
            include_path = node.text.decode('utf-8').strip('"<>')
            include_path_list.append(include_path)
    return include_path_list


def extract_function_call_name_list(tree, filter_standard_function=True):

    # tree-sitter查询：查找所有函数调用
    query_text = """
    (call_expression
      function: (identifier) @function_name
    )
    """

    parser,C_LANGUAGE = get_c_parser()
    query = C_LANGUAGE.query(query_text)

    captures = query.captures(tree.root_node)
    called_functions = set()

    if "function_name" in captures:
        for node in captures['function_name']:
            func_name = node.text.decode('utf-8')

            # 排除标准库函数和测试框架函数外，其他所有调用函数
            if not _is_standard_or_test_function(func_name) and filter_standard_function:
                called_functions.add(func_name)

    return called_functions


def _is_standard_or_test_function(func_name: str) -> bool:
    """
    判断是否为标准库函数或测试框架函数

    Args:
        func_name: 函数名

    Returns:
        是否为标准库或测试框架函数
    """
    # 常见的标准库函数
    standard_functions = {
        'printf', 'scanf', 'malloc', 'free', 'strlen', 'strcpy', 'strcmp',
        'memcpy', 'memset', 'fopen', 'fclose', 'fread', 'fwrite',
        'assert', 'exit', 'abort', 'atoi', 'atof', 'sqrt', 'pow','setUp','tearDown'
    }

    # 常见的测试框架函数前缀
    test_prefixes = ['test_', 'setup_', 'teardown_', 'assert_', 'check_', 'verify_']

    # 检查是否为标准库函数
    if func_name in standard_functions:
        return True

    # 检查是否为测试框架函数
    for prefix in test_prefixes:
        if func_name.startswith(prefix):
            return True

    return False
