
import re
import os
import tree_sitter
from typing import Dict, List, Tuple, Optional
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import count_files_pathlib,get_top3_largest_files,remove_comments_with_mapping,FunctionInfo
from ai_agents.supervisor_agents.haloos_unit_test.clang_function_locator import get_c_function_definition_info_by_clang
from ai_agents.supervisor_agents.haloos_unit_test.re_function_locator import ReCFunctionLocator,_is_c_keyword_or_macro_standalone

def extract_function_calls_with_tree_sitter(content: str, function_start_line: int, function_end_line: int, all_functions: set) -> List[str]:
    """
    使用tree-sitter从函数体中抽取函数调用

    Args:
        content: 完整的源文件内容
        function_start_line: 函数开始行号（1-based）
        function_end_line: 函数结束行号（1-based）
        all_functions: 文件中所有函数名的集合

    Returns:
        List[str]: 函数调用名称列表
    """
    # 获取tree-sitter解析器
    c_language = Language(tsc.language())
    parser = Parser(c_language)

    # 解析代码
    tree = parser.parse(content.encode('utf-8'))

    # 提取函数调用
    return _extract_function_calls_from_tree(tree, function_start_line, function_end_line, all_functions)


def _extract_function_calls_from_tree(tree: tree_sitter.Tree, function_start_line: int, function_end_line: int, all_functions: set) -> List[str]:
    """
    从tree-sitter解析树中提取指定函数内的函数调用

    Args:
        tree: tree-sitter解析树
        function_start_line: 函数开始行号（1-based）
        function_end_line: 函数结束行号（1-based）
        all_functions: 文件中所有函数名的集合

    Returns:
        List[str]: 函数调用名称列表
    """
    called_functions = set()

    def traverse_node(node):
        """递归遍历节点，查找函数调用"""
        # 检查节点是否在目标函数的行范围内
        node_start_line = node.start_point[0] + 1  # 转换为1-based
        node_end_line = node.end_point[0] + 1      # 转换为1-based

        # 只处理在目标函数范围内的节点
        if node_start_line >= function_start_line and node_end_line <= function_end_line:
            # 检查是否是函数调用节点
            if node.type == 'call_expression':
                function_call_info = _extract_function_call_from_node(node, all_functions)
                if function_call_info:
                    called_functions.add(function_call_info)

        # 总是递归遍历子节点，不管是否在范围内
        # 因为父节点可能跨越边界但子节点在范围内
        for child in node.children:
            traverse_node(child)

    # 从根节点开始遍历
    traverse_node(tree.root_node)

    return list(called_functions)

def _extract_function_call_from_node(call_node: tree_sitter.Node, all_functions: set) -> Optional[str]:
    """
    从call_expression节点中提取函数调用名称

    Args:
        call_node: call_expression节点
        all_functions: 文件中所有函数名的集合

    Returns:
        Optional[str]: 函数名或None
    """
    # 获取call_expression的第一个子节点，这通常是被调用的函数
    if not call_node.children:
        return None

    function_node = call_node.children[0]

    # 直接的函数名调用
    if function_node.type == 'identifier':
        function_name = function_node.text.decode('utf-8')

        # 检查是否是文件中定义的函数，且不是关键字
        if function_name in all_functions and not _is_c_keyword_or_macro_standalone(function_name):
            return function_name

    # 处理成员访问调用，如 obj.func() 或 obj->func()
    elif function_node.type == 'field_expression':
        # field_expression的最后一个identifier通常是函数名
        for child in reversed(function_node.children):
            if child.type == 'identifier':
                function_name = child.text.decode('utf-8')
                if function_name in all_functions and not _is_c_keyword_or_macro_standalone(function_name):
                    return function_name
                break

    # 处理指针调用，如 (*func_ptr)()
    elif function_node.type == 'parenthesized_expression':
        for child in function_node.children:
            if child.type == 'unary_expression':
                # 查找unary_expression中的identifier
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        function_name = subchild.text.decode('utf-8')
                        if function_name in all_functions and not _is_c_keyword_or_macro_standalone(function_name):
                            return function_name

    return None

class CFunctionLocator:
    """C函数定位器类"""

    def __init__(self, file_path: str, use_clang=False, only_use_clang=False,
                 use_tree_sitter=True, merge_results=True,
                 use_macro_function_format=True, remove_macro_statement=True):
        """
        初始化函数定位器

        Args:
            file_path: C源文件路径
            use_clang: 是否使用clang
            only_use_clang: 是否只使用clang
            use_tree_sitter: 是否使用tree-sitter
            merge_results: 是否合并tree-sitter和正则表达式的结果
            use_macro_function_format: 是否使用宏函数格式
            remove_macro_statement: 是否移除宏语句
        """
        self.file_path = file_path
        self.only_use_clang = only_use_clang
        self.use_tree_sitter = use_tree_sitter
        self.merge_results = merge_results
        self.use_macro_function_format = use_macro_function_format
        self.remove_macro_statement = remove_macro_statement
        self.test_repo = None
        self.lines: List[str] = []
        self.lines_original: List[str] = []
        self.functions_info: Dict[str, FunctionInfo] = {}

        self._parse_functions(use_clang)
        self._load_file()



    def _load_file(self):
        """加载C源文件内容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
                self.lines_original = file_content.split('\n')
                file_content, line_mapping = remove_comments_with_mapping(file_content)
                self.lines = file_content.split('\n')
        except FileNotFoundError as fne:
            raise FileNotFoundError(f"文件不存在: {self.file_path}") from fne
        except Exception as e:
            raise Exception(f"读取文件失败: {e}") from e

        # 清理重复的函数定义
        self._clean_duplicate_function_definitions()

    def _clean_duplicate_function_definitions(self):
        """清理functions_info中重复的other_function_definitions"""
        for func_name, func_info in self.functions_info.items():
            if func_info.other_function_definitions:
                # 创建一个集合来跟踪已见过的函数定义（基于行号范围）
                seen_definitions = set()

                # 首先添加主函数定义
                main_key = f"{func_info.name}::{func_info.start_line}-{func_info.end_line}"
                seen_definitions.add(main_key)

                # 过滤重复的other_function_definitions
                cleaned_definitions = []
                for definition_dict in func_info.other_function_definitions:
                    cleaned_dict = {}
                    for key, definition in definition_dict.items():
                        # 生成唯一标识（函数名::起始行-结束行）
                        unique_key = f"{definition.name}::{definition.start_line}-{definition.end_line}"

                        # 如果这个定义还没有见过，就保留它
                        if unique_key not in seen_definitions:
                            seen_definitions.add(unique_key)
                            cleaned_dict[key] = definition

                    # 只有当字典不为空时才添加
                    if cleaned_dict:
                        cleaned_definitions.append(cleaned_dict)

                # 更新函数信息
                func_info.other_function_definitions = cleaned_definitions

    def _parse_functions(self, use_clang=True):
        # 项目残缺不完整下，只能利用正则去处理；项目完整，则尝试利用clang去处理；为了保证兜底，也可以加上正则，两个谁多用谁
        repo_can_use_clang = self.tell_if_dependency_correct()

        # 尝试用clang做，准备使用，项目可以使用，详细测试下
        if repo_can_use_clang and self.test_repo is not None and use_clang:
            repo_path = self.test_repo
            # c_file_name = self.file_path.split('/')[-1]
            c_file_name = os.path.basename(self.file_path)
            function_info_clang = get_c_function_definition_info_by_clang(repo_path, c_file_name)
        else:
            function_info_clang = None

        # 如果启用了tree-sitter和合并功能，使用新的合并方法
        re_function_locator = ReCFunctionLocator(
            self.file_path,
            use_tree_sitter=self.use_tree_sitter,
            merge_results=self.merge_results,
            use_macro_function_format=self.use_macro_function_format,
            remove_macro_statement=self.remove_macro_statement
        )
        functions_info_static_extract = re_function_locator.functions_info


        # 选择最终使用的函数信息，如果clang更全就clang否则正则兜底
        if self.only_use_clang and function_info_clang:
            self.functions_info = function_info_clang
        elif function_info_clang and len(function_info_clang) >= len(functions_info_static_extract):
            self.functions_info = function_info_clang
        else:
            self.functions_info = functions_info_static_extract

    def tell_if_dependency_correct(self, split_key_word = 'src/'):

        if  split_key_word not in self.file_path:
            return False

        # 如果是绝对路径
        if os.path.isabs(self.file_path):
            file_split_list = self.file_path.split(split_key_word)
            test_repo = file_split_list[0]
        else:
            test_repo = os.getcwd()

        # support下有文件，且wrapper.h在前三个文件内
        support_repo_file = os.path.join(test_repo,'test','support')
        if not os.path.exists(support_repo_file):
            return False

        dependency_file_count = count_files_pathlib(support_repo_file)
        # 最少有个wrapper.h
        if dependency_file_count < 1:
            return False

        check_file_name = 'wrapper.h'
        is_ceedling_dir = False
        top_three_files = get_top3_largest_files(support_repo_file)
        for select_file_item in top_three_files:
            if check_file_name in select_file_item:
                is_ceedling_dir = True
                break

        # 不是ceedling结构项目
        if not is_ceedling_dir:
            return False

        self.test_repo = test_repo

        return True

    def get_function_info(self, function_name: str) -> Optional[FunctionInfo]:
        """
        获取指定函数的信息

        Args:
            function_name: 函数名

        Returns:
            函数信息对象，如果未找到返回None
        """
        return self.functions_info.get(function_name, None)

    def get_function_lines(self, function_info: FunctionInfo) -> Optional[List[str]]:
        """
        获取指定函数的完整代码行

        Args:
            function_info: 函数信息对象

        Returns:
            函数代码行列表，如果未找到返回None
        """
        if function_info:
            # 转换为0基索引
            start_idx = function_info.start_line - 1
            end_idx = function_info.end_line
            return self.lines[start_idx:end_idx]
        return None

    def get_function_lines_with_context(self, function_name: str = None, function_info: FunctionInfo = None, include_comments: bool = True, include_preprocessor: bool = True, max_context_lines: int = 5) -> Optional[List[str]]:
        """
        获取指定函数的完整代码行，包括前面的注释和条件编译宏

        Args:
            function_name: 函数名
            include_comments: 是否包含函数前的注释
            include_preprocessor: 是否包含函数前的预处理指令（如#if等）
            max_context_lines: 最大上下文行数，防止包含过多文件头部内容

        Returns:
            包含上下文的函数代码行列表，如果未找到返回None
        """
        if function_name:
            func_info = self.get_function_info(function_name)
        else:
            func_info = function_info

        if not func_info:
            return None

        # 转换为0基索引
        func_start_idx = func_info.start_line - 1
        func_end_idx = func_info.end_line

        # 向前查找相关的注释和预处理指令
        context_start_idx = func_start_idx

        # 从函数定义行向前扫描
        i = func_start_idx - 1
        consecutive_empty_lines = 0

        while i >= 0:
            line = self.lines_original[i].strip()

            # 空行处理
            if not line:
                consecutive_empty_lines += 1
                # 如果连续空行过多，可能已经到达文件分隔区域
                if consecutive_empty_lines > 3:
                    break
                i -= 1
                continue
            else:
                consecutive_empty_lines = 0

            # 检查是否是注释
            is_comment = False
            if include_comments:
                is_comment = self._is_function_related_comment(line, i)

            # 检查是否是预处理指令
            is_preprocessor_directive = False
            if include_preprocessor:
                if self._is_preprocessor_directive(line):
                    is_preprocessor_directive = True

            # 如果是相关的上下文，更新起始位置
            if is_comment or is_preprocessor_directive:
                context_start_idx = i
                i -= 1

                # 防止包含过多上下文行
                if func_start_idx - i > max_context_lines:
                    break
            else:
                # 遇到非相关内容就停止
                break

        # 返回包含上下文的代码行
        return self.lines_original[context_start_idx:func_end_idx]

    def get_function_body_location(self, function_name: str) -> Optional[Tuple[int, int]]:
        """
        获取指定函数的行号范围

        Args:
            function_name: 函数名

        Returns:
            (开始行号, 结束行号) 元组，使用1基索引，如果未找到返回None
        """
        func_info = self.get_function_info(function_name)
        if func_info:
            return (func_info.start_line, func_info.end_line)
        return None

    def list_all_functions(self) -> List[str]:
        """
        列出文件中的所有函数名

        Returns:
            函数名列表
        """
        return list(self.functions_info.keys())

    def print_function_summary(self):
        """打印所有函数的摘要信息"""
        if not self.functions_info:
            print("未找到任何函数")
            return

        print(f"在文件 {self.file_path} 中找到 {len(self.functions_info)} 个函数:")
        print("-" * 80)

        for func_name, func_info in self.functions_info.items():
            macro_indicator = " [FUNC宏]" if func_info.is_func_macro else ""
            print(f"函数名: {func_name}{macro_indicator}")
            print(f"  位置: 第 {func_info.start_line}-{func_info.end_line} 行")
            print(f"  返回类型: {func_info.return_type}")
            print(f"  参数: ({func_info.parameters})")
            print()

    def extract_function_calls(self, function_info: FunctionInfo, give_function_list=None) -> Optional[List[str]]:
        """
        使用tree-sitter抽取指定函数内调用的本文件内的其他函数

        Args:
            function_info: 要分析的函数信息对象
            give_function_list: 可选的函数列表，如果不提供则使用文件中所有函数

        Returns:
            函数内调用的本文件内函数名列表，如果函数不存在返回None
        """
        if not function_info:
            return None

        function_name = function_info.name

        # 获取本文件中所有函数名，用于判断调用的是否是本文件内的函数
        if give_function_list is None:
            all_functions = set(self.list_all_functions())
        else:
            all_functions = set(give_function_list)

        # 排除自己，避免递归调用被统计
        all_functions.discard(function_name)

        try:
            # 读取完整文件内容
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 使用tree-sitter提取函数调用
            called_functions = extract_function_calls_with_tree_sitter(
                content,
                function_info.start_line,
                function_info.end_line,
                all_functions
            )

            return called_functions

        except Exception as e:
            # 如果tree-sitter解析失败，回退到原始的正则表达式方法
            print(f"Warning: tree-sitter解析失败，回退到正则表达式方法: {e}")
            return self._extract_function_calls_fallback(function_info, all_functions)

    def _extract_function_calls_fallback(self, function_info: FunctionInfo, all_functions: set) -> List[str]:
        """
        回退方法：使用正则表达式提取函数调用（原始实现）

        Args:
            function_info: 要分析的函数信息对象
            all_functions: 所有函数名的集合

        Returns:
            函数内调用的函数名列表
        """
        function_name = function_info.name

        # 获取函数体代码
        function_lines = self.get_function_lines(function_info)
        if not function_lines:
            return []

        called_functions = set()

        # 编译函数调用的正则表达式
        function_call_pattern = re.compile(r'\b([a-zA-Z_]\w*)\s*\(')

        for line in function_lines:
            # 移除注释
            clean_line = self._remove_comments(line)

            # 跳过预处理指令
            if self._is_preprocessor_directive(clean_line):
                continue

            # 查找所有函数调用
            matches = function_call_pattern.findall(clean_line)

            for match in matches:
                # 过滤掉C语言关键字、宏定义、以及不在本文件中的函数
                if (match in all_functions and
                    match != function_name and  # 排除递归调用自己
                    not _is_c_keyword_or_macro_standalone(match)):
                    called_functions.add(match)

        return list(called_functions)

    def extract_nested_function_calls(self, function_info: FunctionInfo, max_depth: int = 5, visited: Optional[set] = None) -> Dict[str, List[str]]:
        """
        递归抽取指定函数及其调用的函数的嵌套调用关系

        Args:
            function_info: 要分析的函数信息对象
            max_depth: 最大递归深度，防止无限递归
            visited: 已访问的函数集合，用于避免循环调用

        Returns:
            嵌套调用关系字典，键为函数名，值为该函数调用的函数列表
        """
        if visited is None:
            visited = set()

        function_name = function_info.name
        if max_depth <= 0 or function_name in visited:
            return {}

        visited.add(function_name)
        result = {}

        # 获取当前函数直接调用的函数
        direct_calls = self.extract_function_calls(function_info)
        if direct_calls is None:
            return {}

        result[function_name] = direct_calls

        # 递归分析被调用函数的调用关系
        for called_func in direct_calls:
            if called_func not in visited:
                # 获取被调用函数的信息
                called_func_info = self.get_function_info(called_func)
                if called_func_info:
                    nested_calls = self.extract_nested_function_calls(
                        called_func_info, max_depth - 1, visited.copy()
                    )
                    result.update(nested_calls)

        return result
