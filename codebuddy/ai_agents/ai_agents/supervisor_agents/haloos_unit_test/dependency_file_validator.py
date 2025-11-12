import os
import re
import tree_sitter
from typing import Optional, Tuple, List, Dict, Set
from pathlib import Path
from ai_agents.supervisor_agents.haloos_unit_test.extract_function_declarations import check_function_declarations,check_internal_function_if_in_external_header,extract_function_declarations,check_wrong_preproc_function_def,extract_file_include_statement
from ai_agents.supervisor_agents.haloos_unit_test.function_extractor_tool import conditional_macros
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import get_c_parser, list_all_files_pathlib,get_relative_path,read_file_content_get_tree_node
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.ceedling_yaml_validator import CeedlingYamlValidator
def extract_define_macros_with_treesitter(file_path: str) -> List[Dict[str, any]]:
    """
    使用tree-sitter从C文件中提取#define宏定义

    Args:
        file_path: C源文件路径

    Returns:
        List[Dict]: 宏定义信息列表，每个字典包含：
            - name: 宏名称
            - value: 宏值（如果有）
            - line: 定义所在行号
    """
    if not os.path.exists(file_path):
        return []

    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 获取tree-sitter解析器
        parser, c_language = get_c_parser()

        # 解析代码
        tree = parser.parse(content.encode('utf-8'))

        # 提取#define宏定义
        macros = []
        _extract_define_macros_from_node(tree.root_node, content, macros)

        # 检查是否有空内容的preproc_def节点被遗漏，使用行级别解析作为补充
        macros = _supplement_missing_macros(tree.root_node, content, macros)

        return macros

    except Exception as e:
        print(f"Tree-sitter解析失败: {e}")
        return []


def _supplement_missing_macros(root_node: tree_sitter.Node, content: str, existing_macros: List[Dict]) -> List[Dict]:
    """
    补充遗漏的宏定义，主要处理字节偏移错误导致的空内容问题
    """
    # 获取已提取的行号集合
    extracted_lines = {macro['line'] for macro in existing_macros}

    # 查找所有preproc_def节点
    preproc_def_lines = []
    _find_preproc_def_lines(root_node, preproc_def_lines)

    # 处理遗漏的行
    lines = content.splitlines()
    supplemented_macros = list(existing_macros)

    for line_num in preproc_def_lines:
        if line_num not in extracted_lines and line_num <= len(lines):
            line_content = lines[line_num - 1]

            # 使用正则表达式解析该行
            define_pattern = r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)$'
            match = re.match(define_pattern, line_content)

            if match:
                macro_name = match.group(1)
                macro_value = match.group(2).strip()

                # 移除行尾注释
                if '//' in macro_value:
                    macro_value = macro_value.split('//')[0].strip()
                if '/*' in macro_value:
                    macro_value = macro_value.split('/*')[0].strip()

                supplemented_macros.append({
                    'name': macro_name,
                    'value': macro_value,
                    'line': line_num
                })

    # 按行号排序
    supplemented_macros.sort(key=lambda x: x['line'])
    return supplemented_macros


def _find_preproc_def_lines(node: tree_sitter.Node, line_numbers: List[int]):
    """
    递归查找所有preproc_def节点的行号
    """
    if node.type == 'preproc_def':
        line_num = node.start_point[0] + 1
        line_numbers.append(line_num)

    for child in node.children:
        _find_preproc_def_lines(child, line_numbers)


def _extract_define_macros_from_node(node: tree_sitter.Node, content: str, macros: List[Dict]):
    """
    递归遍历AST节点，提取#define宏定义
    """
    # 只处理 #define 预处理指令
    if node.type == 'preproc_def':
        macro_info = _parse_define_macro(node, content)
        if macro_info:
            macros.append(macro_info)

    # 递归处理子节点
    for child in node.children:
        _extract_define_macros_from_node(child, content, macros)


def _parse_define_macro(node: tree_sitter.Node, content: str) -> Optional[Dict]:
    """解析 #define 宏定义"""
    try:
        # 获取宏名称
        name_node = node.child_by_field_name('name')
        if not name_node:
            return None

        macro_name = content[name_node.start_byte:name_node.end_byte]

        # 如果字节偏移提取的内容为空，使用行号备用方法
        if not macro_name.strip():
            return _parse_define_macro_fallback(node, content)

        # 获取宏值（如果有）
        value_node = node.child_by_field_name('value')
        macro_value = ""
        if value_node:
            macro_value = content[value_node.start_byte:value_node.end_byte].strip()

        return {
            'name': macro_name,
            'value': macro_value,
            'line': node.start_point[0] + 1,  # tree-sitter使用0-based行号
        }
    except Exception:
        return None


def _parse_define_macro_fallback(node: tree_sitter.Node, content: str) -> Optional[Dict]:
    """
    当字节偏移提取失败时的备用方法，直接从行内容解析
    """
    try:
        # 获取行号
        line_num = node.start_point[0] + 1
        lines = content.splitlines()

        if line_num <= len(lines):
            line_content = lines[line_num - 1]

            # 使用正则表达式解析该行的宏定义
            define_pattern = r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)$'
            match = re.match(define_pattern, line_content)

            if match:
                macro_name = match.group(1)
                macro_value = match.group(2).strip()

                # 移除行尾注释
                if '//' in macro_value:
                    macro_value = macro_value.split('//')[0].strip()
                if '/*' in macro_value:
                    macro_value = macro_value.split('/*')[0].strip()

                return {
                    'name': macro_name,
                    'value': macro_value,
                    'line': line_num
                }

        return None
    except Exception:
        return None


def get_macro_names_from_file_treesitter(file_path: str) -> Set[str]:
    """
    使用tree-sitter从文件中提取所有#define宏名称

    Args:
        file_path: C源文件路径

    Returns:
        Set[str]: 宏名称集合
    """
    macros = extract_define_macros_with_treesitter(file_path)

    return {macro['name'] for macro in macros}


def get_macro_names_from_file(file_path):

    # 给定文件，返回文件内所有宏定义的名字
    if not os.path.exists(file_path):
        return []

    # 获取文件内条件编译组合
    configs_list = conditional_macros(file_path,use_clang=False)

    # 基于条件编译组合，解析条件编译宏
    macro_set = set()
    for macro_conditional in configs_list:
        for macro_item in macro_conditional:
            if '=' in macro_item:
                macro_item_list = macro_item.split('=')
                left_macro_name = macro_item_list[0].strip()

                # 规范格式下左边为条件编译宏
                macro_name = left_macro_name
                macro_set.add(macro_name)
            else:
                continue
    return macro_set

def check_macros_exist_in_file(extracted_macros, target_file_path: str) -> Tuple[bool, List[str]]:

    found_macros = []
    try:
        # 如果源文件没有宏，返回 (False, [])（没有宏要检查）
        if not extracted_macros:
            return False, []

        # 检查目标文件是否存在
        if not os.path.exists(target_file_path):
            return False, []

            # 优先使用tree-sitter方法
        try:
            macro_set_in_h_file = get_macro_names_from_file_treesitter(target_file_path)
        except Exception as e:
            print(f"Tree-sitter提取失败 {e}")
            return False, []

        for macro_item_in_h_file in macro_set_in_h_file:
            if macro_item_in_h_file in extracted_macros:
                found_macros.append(macro_item_in_h_file)
        # 返回结果：是否找到任何宏，以及找到的所有宏列表
        return len(found_macros) > 0, found_macros
    except Exception:
        print('出现任何错误都返回 (False, [])')
        return False, []

# 外部函数声明去做,需要check_base_dependency_file_format_and_content检测过了再做这个检测
def check_dependency_external_declaration_file():

    return_info = []
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file = haloos_global_env_config.SOURCE_FILE_NAME
    source_file_full_path = os.path.join(working_directory,'src',source_file)

    # 检测1: 外部函数声明文件不要包含内部函数声明
    external_declaration_h_file = 'external_function.h'
    external_declaration_h_file_full_path = os.path.join(working_directory,'test/support/',external_declaration_h_file)

    if external_declaration_h_file is not None:
        external_declaration_flag, external_declaration_list = check_internal_function_if_in_external_header(source_file_full_path,external_declaration_h_file_full_path)
    else:
        external_declaration_flag, external_declaration_list = True, []
    if external_declaration_flag:
        source_h_file_name = f'test/support/{external_declaration_h_file}'
        if len(external_declaration_list) == 1:
            return_info.append(f"{source_h_file_name}只应该包含外部函数声明，在{source_h_file_name}内不应该包含{external_declaration_list[0]}内部函数的声明")
        else:
            formatted_functions = '\n'.join([f"  - {func}" for func in external_declaration_list])
            return_info.append(f"{source_h_file_name}只应该包含外部函数声明，在{source_h_file_name}内不应该包含以下{len(external_declaration_list)}个内部函数的声明:\n{formatted_functions}")

    # 检测2: 内部函数文件内不要有外部函数的声明

    return return_info



# 依赖文件：除外部函数依赖文件外的其他检测
def check_base_dependency_file_format_and_content():
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file = haloos_global_env_config.SOURCE_FILE_NAME
    system_function_declarations_path = haloos_global_env_config.SYSTEM_FUN_DECLARATION_PATH

    return_info = []

    if not working_directory or not source_file:
        return return_info

    source_file_full_path = os.path.join(working_directory,'src',source_file)
    wrapper_h_file = os.path.join(working_directory,'test/support/wrapper.h')
    test_support_repo = os.path.join(working_directory, 'test/support')

    internal_h_file = source_file.replace('.c','.h')
    internal_function_file =  os.path.join(working_directory,'test/support/',internal_h_file)

    all_header_file = list_all_files_pathlib(test_support_repo)

    # 检测1: 条件编译宏不能定义在任何文件内
    for check_header_file in all_header_file:
        if check_header_file.endswith('.h'):
            # 检测1.1:条件编译
            source_macros = get_extracted_macros_from_source_file()
            macros_flag, macros_definition_list = check_macros_exist_in_file(source_macros, check_header_file)
            if macros_flag:
                check_relative_header_file = get_relative_path(check_header_file,working_directory)
                return_info.append(f"在{check_relative_header_file}中存在条件编译宏的定义 {';'.join(macros_definition_list)} , 请去除，条件编译宏不期望定义在头文件内")
            # 检测1.2：宏函数的定义，不要将函数定义成函数宏的形式：define function() 0这种不允许
            wrong_macro_list = check_wrong_preproc_function_def(check_header_file)
            wrong_marco_name_list = [wrong_macro_item['name'] for wrong_macro_item in wrong_macro_list]
            if len(wrong_macro_list):
                check_relative_header_file = get_relative_path(check_header_file,working_directory)
                return_info.append(f"在{check_relative_header_file}中, {';'.join(wrong_marco_name_list)}不应该被定义成函数宏的形式")

    # 检测2：内部函数声明文件要包含所有内部声明
    declaration_macro_error_flag, error_macro_func = check_function_declarations(source_file_full_path, internal_function_file, check_header_file_macro_format=True)
    if declaration_macro_error_flag:
        source_h_file_name = f'test/support/{internal_h_file}'
        return_info.append(f"ERROR: 在{source_h_file_name}内存在未展开的宏: {';'.join(error_macro_func)}, **请将宏展开！！**")
    else:
        declaration_flag, missing_declaration_list = check_function_declarations(source_file_full_path,internal_function_file)
        if declaration_flag:
            source_h_file_name = f'test/support/{internal_h_file}'
            if len(missing_declaration_list) == 1:
                return_info.append(f"在{source_h_file_name}内缺少{missing_declaration_list[0]}函数的声明; 注意：由于后续测试需要，如果是静态函数也需要声明在该文件内，静态函数的声明需要包含 static 关键字")
            else:
                formatted_functions = '\n'.join([f"  - {func}" for func in missing_declaration_list])
                return_info.append(f"在{source_h_file_name}内缺少以下{len(missing_declaration_list)}个函数的声明:\n{formatted_functions}; 注意：由于后续测试需要，如果是静态函数也需要声明在该文件内，静态函数的声明需要包含 static 关键字")

    # 检测3: 所有.h文件内都不要定义系统函数的声明，否则后续mock可能造成测试崩溃
    wrong_header_declaration_dict= check_system_function_declarations_in_support_headers(system_function_declarations_path)
    if wrong_header_declaration_dict:
        for file_name, wrong_header_file_list in wrong_header_declaration_dict.items():
            return_info.append(f"在{file_name}中定义了系统文件内的函数声明: {';'.join(wrong_header_file_list)}, 请去除，不要重复定义在头文件内")

    # 检测4: wrapper.h文件中是否有函数声明不要有
    declaration = extract_function_declarations(wrapper_h_file)
    if len(declaration) > 0:
        return_info.append('ERROR: test/support下的wrapper.h内包含了函数声明，希望该文件包含外部数据结构，非条件编译宏及外部变量，不希望包含函数声明或函数定义')


    # 检测5: test/support下不要有.c文件，文件后缀名检测
    files = os.listdir(test_support_repo)
    c_files = [f for f in files if f.endswith('.c')]
    if len(c_files) > 0:
        return_info.append('ERROR: test/support下不应该包含.c文件,应该只有.h文件；不应该在test/support下创建c文件去定义全局变量或函数实现')
    for check_header_file in all_header_file:
        check_relative_header_file = get_relative_path(check_header_file,test_support_repo)
        if check_multiple_extensions(check_relative_header_file):
            return_info.append(f'ERROR: {check_relative_header_file}文件包含多重扩展名，不符合c文件规范')

    # 检测6: 外部函数声明全部集中在一个文件内
    file_declaration_dict = {}
    for check_header_file in all_header_file:
        if check_header_file.endswith('.h'):
            check_relative_header_file = get_relative_path(check_header_file,test_support_repo)
            declaration = extract_function_declarations(check_header_file)
            if len(declaration) > 0 and check_relative_header_file not in ['wrapper.h',internal_h_file]:
                file_declaration_dict[check_relative_header_file] = declaration

    if len(file_declaration_dict) > 1:
        declaration_file_list = list(file_declaration_dict.keys())
        return_info.append(f"在{';'.join(declaration_file_list)}内均存在函数声明，请将外部函数声明集中在external_function.h内，且外部函数声明文件内不要有内部函数声明；其余头文件引用该文件即可")
    elif len(file_declaration_dict) == 1:
        declaration_file_list_item = list(file_declaration_dict.keys())[0]
        if declaration_file_list_item != 'external_function.h':
            return_info.append(f"外部函数声明集中{declaration_file_list_item}内，不符合期望，期望外部函数均集中在external_function.h内")

    # 检测7: 其他文件头文件内是否include了external_function.h
    three_human_create_file = ['wrapper.h',internal_h_file, 'external_function.h']
    no_external_statement_file = []
    for check_header_file in all_header_file:
        check_header_statement = 'external_function.h'
        if not check_header_file.endswith('.h'):
            continue
        check_relative_header_file = get_relative_path(check_header_file,test_support_repo)
        header_file_tree = read_file_content_get_tree_node(check_header_file)
        include_path_list = extract_file_include_statement(header_file_tree)
        if check_header_statement not in include_path_list and check_relative_header_file not in three_human_create_file:
            no_external_statement_file.append(check_relative_header_file)

    # 不为空
    if len(no_external_statement_file) > 0:
        return_info.append(f"{';'.join(no_external_statement_file)}头文件内没有include external_function.h头文件，请在这些头文件内include external_function.h头文件")

    # 检测8: 防止模型乱创建文件：提取源文件内引用的头文件，提取当前项目support下所有文件，查看是否存在不期望的文件，去掉; 注意嵌套问题
    not_wangt_header_file_list = set()
    source_file_tree = read_file_content_get_tree_node(source_file_full_path)
    source_file_include_path_list = extract_file_include_statement(source_file_tree)
    if extract_file_include_statement:
        source_file_include_path_list.extend(three_human_create_file)
    else:
        source_file_include_path_list = three_human_create_file

    # 处理多余空格
    source_file_set =set()
    for source_include_statement in source_file_include_path_list:
        source_include_statement = source_include_statement.replace(' ','').replace('/','_')
        source_file_set.add(source_include_statement)

    for check_header_file in all_header_file:
        check_relative_header_file = get_relative_path(check_header_file,test_support_repo)
        if not check_relative_header_file:
            continue

        check_relative_header_file_original = check_relative_header_file
        check_relative_header_file = check_relative_header_file.replace(' ','').replace('/','_')
        compareset_item = set()
        compareset_item.add(check_relative_header_file)
        # 直接字符串比较有玄学bug， /会自动变下划线, 如果不在
        if not compareset_item.issubset(source_file_set):
            not_wangt_header_file_list.add(check_relative_header_file_original)
    if len(not_wangt_header_file_list) > 0:
        return_info.append(f"不期望的文件: test/support下存在{'; '.join(not_wangt_header_file_list)}的这些不期望的文件，请删除文件")


    # 检测9: 配置文件发生不期望修改，可能会造成整个test/support下文件被删除的严重问题
    current_file_dir = Path(__file__).parent  # 当前.py文件所在目录
    initial_yaml_path = current_file_dir / "initial_ceedling_project.yml"
    project_yaml_file_path = os.path.join(working_directory, 'project.yml')
    ceedling_project_yaml_validator = CeedlingYamlValidator(str(initial_yaml_path))
    project_yaml_validate_flag, project_yaml_validate_info = ceedling_project_yaml_validator.valid_ceedling_yaml(project_yaml_file_path)
    if not project_yaml_validate_flag:
        project_yaml_validate_info = '\n'.join(project_yaml_validate_info)
        return_info.append(f"ERROR: 配置文件发生不期望修改，可能会造成预期外的问题\n{project_yaml_validate_info}")
    return return_info


def check_multiple_extensions(filename):
    """检测多重扩展名问题"""
    # 计算文件名中点的数量
    dot_count = filename.count('.')

    # 如果有多个点，可能是多重扩展名
    if dot_count > 1:
        # 排除隐藏文件（以.开头）
        if not filename.startswith('.'):
            return True

    return False

def check_dependency_file_by_two_stage():
    # stage 1: 基础检测
    base_return_info = check_base_dependency_file_format_and_content()
    if len(base_return_info) > 0:
        return base_return_info

    # stage 2: 外部声明文件检测
    external_file_return_info = check_dependency_external_declaration_file()
    return external_file_return_info

def check_system_function_declarations_in_support_headers(system_files_path: str = '',
                                                        system_files: List[str] = '') -> Optional[Dict[str, List[str]]]:
    """
    检查指定系统文件中的函数声明是否存在于test/support下的头文件中

    此函数用于分析系统文件中的函数声明，并检查这些声明是否被包含在测试支持目录的头文件中。

    Args:
        system_files_path (str, optional): 系统文件所在的根路径。如果为None，会自动查找Linux默认位置
        system_files (List[str], optional): 要检查的系统文件列表。如果为None，则使用常用系统文件列表
                                          常用文件包括: ['stdio.h', 'stdlib.h', 'string.h', 'stdint.h', 'stdbool.h']

    Returns:
        Optional[Dict[str, List[str]]]: 检测结果字典，格式为：
            {
                '头文件名1': [检测到的函数声明列表],
                '头文件名2': [检测到的函数声明列表],
                ...
            }
            如果没有检测到任何声明，返回None

    Examples:
        >>> # 检查默认系统文件（自动查找系统路径）
        >>> result = check_system_function_declarations_in_support_headers()
        >>> print(result)
        {'wrapper.h': ['printf', 'malloc'], 'external_declarations.h': ['strlen', 'strcpy']}

        >>> # 指定系统文件路径
        >>> result = check_system_function_declarations_in_support_headers("/usr/include")
        >>> print(result)
        {'wrapper.h': ['printf', 'malloc']}
    """
    # 默认ceedling可能引入的常用系统文件
    if not system_files:
        system_files = ['stdio.h', 'stdlib.h', 'string.h', 'ctype.h','stdint.h', 'stdbool.h']

    # 如果没有指定系统文件路径，自动查找Linux常见路径
    if not system_files_path:
        linux_default_paths = [
            '/usr/include',
            '/usr/local/include',
            '/opt/include',
            '/usr/include/x86_64-linux-gnu',
            '/usr/include/linux'
        ]

        system_files_path = None
        for path in linux_default_paths:
            if os.path.exists(path):
                system_files_path = path
                break

    # 检查系统文件路径是否存在
    if not system_files_path or not os.path.exists(system_files_path):
        return None

    # 检查test/support目录是否存在
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    if not working_directory:
        return None

    test_support_dir = os.path.join(working_directory, 'test', 'support')
    if not os.path.exists(test_support_dir):
        return None

    # 第一步: 从系统文件中提取函数声明
    system_function_declarations = set()

    for system_file in system_files:
        system_file_path = os.path.join(system_files_path, system_file)
        if os.path.exists(system_file_path):
            try:
                # 使用现有的函数声明提取功能
                declarations = extract_function_declarations(system_file_path)
                for decl in declarations:
                    system_function_declarations.add(decl['name'])
            except Exception:
                continue  # 忽略解析错误，继续处理其他文件

    if not system_function_declarations:
        return None

    # 第二步: 扫描test/support目录下的所有.h文件并检查声明
    result = {}

    for root, dirs, files in os.walk(test_support_dir):
        for file in files:
            if file.endswith('.h'):
                header_file_path = os.path.join(root, file)
                try:
                    # 提取该头文件中的函数声明
                    header_declarations = extract_function_declarations(header_file_path)

                    # 优化: 遍历头文件中的函数(较少)，检查是否在系统函数集合中(较多)
                    found_functions = []
                    for decl in header_declarations:
                        func_name = decl['name']
                        if func_name in system_function_declarations:
                            found_functions.append(func_name)

                    # 如果找到了系统函数声明，添加到结果中
                    if found_functions:
                        result[file] = sorted(found_functions)  # 排序便于查看

                except Exception:
                    continue  # 忽略解析错误，继续处理其他文件

    # 返回结果，如果没有找到任何声明返回None
    return result if result else None


extracted_macros_from_source_file = None  # 使用 None 表示未初始化
_last_config_cache = None  # 缓存上次的配置，用于检测配置变化

def get_extracted_macros_from_source_file():
    """
    获取源文件的宏定义（延迟初始化，带配置变化检测）

    Returns:
        set: 源文件中的宏名称集合，如果初始化失败返回空集合
    """
    global extracted_macros_from_source_file, _last_config_cache

    # 获取当前配置
    working_directory = haloos_global_env_config.TEST_REPO_PATH
    source_file = haloos_global_env_config.SOURCE_FILE_NAME
    current_config = (working_directory, source_file)

    # 检查是否需要初始化或重新加载（配置发生变化）
    if extracted_macros_from_source_file is None or _last_config_cache != current_config:
        # 验证配置完整性
        if not working_directory or not source_file:
            print("警告: TEST_REPO_PATH 或 SOURCE_FILE_NAME 未设置，返回空宏集合")
            extracted_macros_from_source_file = set()
            return extracted_macros_from_source_file

        source_file_full_path = os.path.join(working_directory, 'src', source_file)

        try:
            # 提取源文件中的宏
            macros = get_macro_names_from_file(source_file_full_path)
            extracted_macros_from_source_file = macros if macros else set()
            _last_config_cache = current_config
            print(f"已缓存源文件宏定义，共 {len(extracted_macros_from_source_file)} 个宏")
        except Exception as e:
            print(f"提取源文件宏定义失败: {e}")
            extracted_macros_from_source_file = set()

    return extracted_macros_from_source_file
