
import re

from typing import Dict, List, Tuple, Optional
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import remove_comments_with_mapping,is_conventional_macro_name,change_function_name_by_line,FunctionInfo
from ai_agents.supervisor_agents.haloos_unit_test.tree_sitter_function_extractor import TreeSitterFunctionExtractor


def _is_c_keyword_or_macro_standalone(name: str) -> bool:
    """
    独立的C关键字和宏检查函数

    Args:
        name: 要检查的名称

    Returns:
        bool: 是否是关键字或宏
    """
    # C语言关键字
    c_keywords = {
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
        'break', 'continue', 'return', 'goto', 'sizeof', 'typedef',
        'struct', 'union', 'enum', 'auto', 'register', 'static', 'extern',
        'const', 'volatile', 'void', 'char', 'short', 'int', 'long',
        'float', 'double', 'signed', 'unsigned', 'inline'
    }

    # 常见的宏和特殊标识符
    common_macros = {
        'FUNC', 'FUNC_CODE', 'FUNC_OS_CODE', 'OS_CODE',
        'NULL', 'TRUE', 'FALSE', 'MAX', 'MIN',
        'sizeof', 'offsetof', 'UNUSED', 'STATIC',
        'PUBLIC', 'PRIVATE', 'PROTECTED'
    }

    return name in c_keywords or name in common_macros

class ReCFunctionLocator:
    """C函数定位器类"""

    def __init__(self, file_path: str,
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
        self.use_tree_sitter = use_tree_sitter
        self.merge_results = merge_results
        self.use_macro_function_format = use_macro_function_format
        self.remove_macro_statement = remove_macro_statement
        self.test_repo = None
        self.lines: List[str] = []
        self.lines_original: List[str] = []
        self.functions_info: Dict[str, FunctionInfo] = {}

        # 编译正则表达式模式
        self._compile_patterns()

        # 加载和解析文件
        self._load_file()
        self._parse_functions()

    def _parse_functions(self):
        if self.use_tree_sitter:
            functions_info_static_extract = self.get_functions_with_merge(
                use_tree_sitter=True,
                merge_results=self.merge_results,
                use_macro_function_format=self.use_macro_function_format,
                remove_macro_statement=self.remove_macro_statement
            )
        else:
            # 原有逻辑：获取正则的结果
            functions_info_static_extract = self._parse_functions_by_re()
        self.functions_info = functions_info_static_extract

    def _compile_patterns(self):
        """编译所有需要的正则表达式模式"""
        # FUNC族宏模式：支持任意修饰符 + FUNC宏的组合
        # 匹配: [任意修饰符...] FUNC_*(...) 函数名(参数)
        self.func_macro_pattern = re.compile(
            r'^\s*'                                                               # 行开始
            r'(?:([a-zA-Z_]\w*)\s+)*?'                                            # 任意数量的修饰符（非贪婪匹配）
            r'(FUNC[A-Z0-9_]*)\s*'                                                # FUNC族宏名
            r'\(\s*([^)]+)\s*\)\s+'                                               # 宏参数
            r'([a-zA-Z_]\w*)\s*'                                                  # 函数名
            r'\(([^{]*)\)\s*\{?'                                                  # 函数参数
        )

        # 标准函数定义模式：支持复杂修饰符组合
        self.standard_func_pattern = re.compile(
            r'^\s*(?:(static|extern|inline|const|volatile|inline_function)\s+)+'  # 至少一个修饰符
            r'([a-zA-Z_]\w*(?:\s*\*+)?(?:\s+[a-zA-Z_]\w*)*?)\s+'                  # 返回类型
            r'([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'                                 # 函数名和参数
        )

        # 增强的多修饰符函数定义模式：专门处理static inline等多修饰符组合和复杂指针类型
        # 修复了灾难性回溯问题
        self.enhanced_func_pattern = re.compile(
            r'^\s*'                                                               # 行开始
            r'(?:(static)\s+)?'                                                   # 可选static
            r'(?:(extern)\s+)?'                                                   # 可选extern
            r'(?:(inline)\s+)?'                                                   # 可选inline
            r'(?:(const)\s+)?'                                                    # 可选const
            r'(?:(volatile)\s+)?'                                                 # 可选volatile
            r'(?:(inline_function)\s+)?'                                          # 可选inline_function
            r'([a-zA-Z_]\w*(?:\s+[a-zA-Z_]\w*)*?)\s*'                             # 返回类型名（修复回溯问题）
            r'(\*+)?\s*'                                                          # 指针符号（可选，支持多级指针）
            r'([a-zA-Z_]\w*)\s*'                                                  # 函数名
            r'\(([^{]*)\)\s*\{?'                                                  # 函数参数
        )

        # 简单函数定义模式：无修饰符的函数
        self.simple_func_pattern = re.compile(
            r'^\s*([a-zA-Z_]\w*(?:\s*\*+)?(?:\s+[a-zA-Z_]\w*)*?)\s+'              # 返回类型
            r'([a-zA-Z_]\w*)\s*\(([^{]*)\)\s*\{?'                                 # 函数名和参数
        )

        # 函数声明模式（以分号结尾）
        self.declaration_pattern = re.compile(r';\s*$')

        # 注释模式
        self.single_line_comment = re.compile(r'//.*$')
        self.multi_line_comment_start = re.compile(r'/\*')
        self.multi_line_comment_end = re.compile(r'\*/')

        # 预处理指令模式 - 只检测#if相关指令
        self.preprocessor_pattern = re.compile(r'^\s*#if')

        # 函数名提取模式（从已知的函数定义行中提取函数名）
        self.func_name_extract = re.compile(r'\b([a-zA-Z_]\w*)\s*\(')

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

    def _remove_comments(self, line: str) -> str:
        """移除行中的注释"""
        # 移除单行注释
        line = self.single_line_comment.sub('', line)
        return line.strip()

    def _is_preprocessor_directive(self, line: str) -> bool:
        """判断是否是预处理指令"""
        return bool(self.preprocessor_pattern.match(line))

    def _is_function_declaration(self, line: str) -> bool:
        """判断是否是函数声明（而非定义）"""
        return bool(self.declaration_pattern.search(line))

    def _find_function_end(self, start_line: int) -> int:
        """
        使用大括号计数找到函数结束位置

        Args:
            start_line: 函数开始行号（从0开始）

        Returns:
            函数结束行号（从0开始），如果找不到返回-1
        """
        brace_count = 0
        found_opening_brace = False

        for i in range(start_line, len(self.lines)):
            line = self._remove_comments(self.lines[i])

            # 跳过预处理指令
            if self._is_preprocessor_directive(line):
                continue

            # 计算大括号
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening_brace = True
                elif char == '}':
                    brace_count -= 1

                    # 如果找到了开始括号且计数回到0，说明函数结束
                    if found_opening_brace and brace_count == 0:
                        return i

        return -1  # 没有找到匹配的结束括号

    def _is_function_definition_start(self, line: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        判断是否是函数定义的开始

        Returns:
            (是否是函数定义, 函数名, 返回类型, 参数列表)
        """
        clean_line = self._remove_comments(line)

        # 跳过空行和预处理指令
        if not clean_line or self._is_preprocessor_directive(clean_line):
            return False, None, None, None

        # 跳过函数声明
        if self._is_function_declaration(clean_line):
            return False, None, None, None

        # 早期退出检查：如果行不包含可能的函数定义特征，直接跳过
        if not ('(' in clean_line and (
            any(keyword in clean_line for keyword in ['static', 'extern', 'inline', 'const', 'volatile']) or
            'FUNC' in clean_line or
            clean_line.strip()[0].islower() or clean_line.strip()[0].isupper()
        )):
            return False, None, None, None

        # 优先检查是否包含FUNC族宏（通过字符串检查，避免正则匹配错误）
        if 'FUNC' in clean_line and '(' in clean_line:
            # 这是一个包含FUNC宏的行，使用FUNC宏模式解析
            func_match = self.func_macro_pattern.match(clean_line)

            if func_match:
                groups = func_match.groups()

                # 新的正则表达式分组结构：
                # (modifiers..., macro_name, macro_params, func_name, func_params)
                # 第一个分组是所有修饰符的合并匹配，后面4个是宏信息

                if len(groups) >= 4:
                    # 提取修饰符 - 需要从原始字符串中提取所有FUNC前的修饰符
                    func_pos = clean_line.find('FUNC')
                    modifiers_part = clean_line[:func_pos].strip()
                    modifiers = [mod.strip() for mod in modifiers_part.split() if mod.strip()]

                    macro_name = groups[1]    # FUNC宏名
                    macro_params = groups[2]  # 宏参数
                    func_name = groups[3]     # 函数名
                    parameters = groups[4] if len(groups) > 4 else ""    # 函数参数

                    # 检查函数名是否有效：不能是FUNC相关的宏名
                    if (macro_name and func_name and len(func_name.strip()) >= 2 and
                        not func_name.startswith('FUNC') and
                        not _is_c_keyword_or_macro_standalone(func_name)):
                        # 构建返回类型，包含修饰符和宏信息
                        modifiers_str = ' '.join(modifiers) + ' ' if modifiers else ''
                        return_type = f"{modifiers_str}{macro_name}({macro_params})".strip()
                        return True, func_name.strip(), return_type, (parameters or "").strip()

        # 只对可能包含修饰符的行尝试增强模式
        if any(keyword in clean_line for keyword in ['static', 'extern', 'inline', 'const', 'volatile']):
            enhanced_match = self.enhanced_func_pattern.match(clean_line)

            if enhanced_match:
                groups = enhanced_match.groups()

                # 收集所有修饰符（前6个分组）
                modifiers = []
                modifier_names = ['static', 'extern', 'inline', 'const', 'volatile', 'inline_function']
                for i in range(min(6, len(groups))):
                    if groups[i]:  # 如果这个修饰符存在
                        modifiers.append(modifier_names[i])

                # 提取函数相关信息
                if len(groups) >= 10:
                    return_type_name = groups[6]  # 返回类型名
                    pointer_part = groups[7]      # 指针符号
                    func_name = groups[8]         # 函数名
                    parameters = groups[9]        # 函数参数

                    if func_name and return_type_name and len(func_name.strip()) >= 2:

                        if (not _is_c_keyword_or_macro_standalone(func_name) and
                            not func_name.startswith('FUNC')):
                            # 构建完整的返回类型，包括修饰符、类型名和指针符号
                            modifiers_str = ' '.join(modifiers) + ' ' if modifiers else ''
                            pointer_str = pointer_part if pointer_part else ''
                            full_return_type = f"{modifiers_str}{return_type_name}{pointer_str}".strip()
                            return True, func_name.strip(), full_return_type, (parameters or "").strip()

        # 检查简单函数模式（无修饰符）- 最快的模式
        simple_match = self.simple_func_pattern.match(clean_line)

        if simple_match:
            return_type = simple_match.group(1).strip()
            func_name = simple_match.group(2).strip()
            parameters = simple_match.group(3).strip()

            if (not _is_c_keyword_or_macro_standalone(func_name) and
                len(func_name.strip()) >= 2 and
                not func_name.startswith('FUNC')):
                return True, func_name, return_type, parameters

        return False, None, None, None

    def _is_potential_multiline_function_start(self, line: str) -> bool:
        """
        检测是否是潜在的多行函数定义开始
        识别那些可能是函数定义开始但参数列表不完整的行

        Returns:
            bool: 是否可能是多行函数的开始
        """
        clean_line = self._remove_comments(line)

        # 跳过空行和预处理指令
        if not clean_line or self._is_preprocessor_directive(clean_line):
            return False

        # 跳过函数声明
        if self._is_function_declaration(clean_line):
            return False

        # 检查是否包含函数定义的基本特征
        if '(' not in clean_line:
            return False

        # 检查是否有修饰符或看起来像函数定义
        has_modifiers = any(keyword in clean_line for keyword in ['static', 'extern', 'inline', 'const', 'volatile'])
        has_func_pattern = 'FUNC' in clean_line
        has_identifier_pattern = bool(re.search(r'[a-zA-Z_]\w*\s*\(', clean_line))

        if not (has_modifiers or has_func_pattern or has_identifier_pattern):
            return False

        # 检查是否参数列表不完整（没有闭合的括号或没有函数体开始）
        open_parens = clean_line.count('(')
        close_parens = clean_line.count(')')

        # 如果有开括号但没有匹配的闭括号，或者有闭括号但没有函数体，可能是多行函数
        if open_parens > close_parens:
            return True
        elif open_parens == close_parens and ')' in clean_line:
            # 检查闭括号后是否没有函数体开始
            paren_pos = clean_line.rfind(')')
            after_paren = clean_line[paren_pos+1:].strip()
            if not after_paren or (after_paren and '{' not in after_paren):
                return True

        return False

    def _handle_multiline_function_signature(self, start_line_idx: int) -> Tuple[Optional[str], Optional[str], Optional[str], int]:
        """
        处理跨行的函数签名

        Returns:
            (函数名, 返回类型, 参数列表, 签名结束行号)
        """
        combined_lines = []
        current_idx = start_line_idx
        found_complete_signature = False
        paren_count = 0

        # 收集连续的行直到找到完整的函数签名
        while current_idx < len(self.lines):
            line = self._remove_comments(self.lines[current_idx])

            # 跳过预处理指令
            if self._is_preprocessor_directive(line):
                current_idx += 1
                continue

            # 跳过空行，但不要在函数签名中间停止
            if not line.strip():
                current_idx += 1
                continue

            combined_lines.append(line.strip())

            # 计算括号平衡
            paren_count += line.count('(') - line.count(')')

            # 如果找到了函数体开始，函数签名结束
            if '{' in line:
                found_complete_signature = True
                break

            # 如果括号已经平衡且有闭括号，检查是否是完整签名
            if paren_count == 0 and ')' in line:
                # 检查下一行是否是函数体开始
                next_idx = current_idx + 1
                while next_idx < len(self.lines):
                    next_line = self._remove_comments(self.lines[next_idx]).strip()
                    if not next_line:
                        next_idx += 1
                        continue
                    if next_line.startswith('{'):
                        found_complete_signature = True
                        current_idx = next_idx
                        break
                    elif not self._is_preprocessor_directive(next_line):
                        # 如果下一个非空行不是函数体，可能不是函数定义
                        break
                    next_idx += 1
                break

            current_idx += 1

            # 防止无限循环
            if current_idx - start_line_idx > 15:
                break

        if not combined_lines:
            return None, None, None, current_idx

        # 合并所有行，清理多余的空格
        combined_signature = ' '.join(combined_lines)
        combined_signature = re.sub(r'\s+', ' ', combined_signature)  # 将多个空格合并为单个

        # 尝试从合并的签名中提取函数信息
        is_func, func_name, return_type, params = self._is_function_definition_start(combined_signature)

        if is_func and found_complete_signature:
            return func_name, return_type, params, current_idx

        return None, None, None, current_idx

    def _parse_functions_by_re(self):
        """解析文件中的所有函数"""
        i = 0
        function_info_re = {}

        while i < len(self.lines):
            line = self.lines[i]

            # 检查是否是函数定义开始
            is_func_start, func_name, return_type, params = self._is_function_definition_start(line)

            if is_func_start:
                # 找到函数结束位置
                end_line = self._find_function_end(i)

                if end_line != -1:
                    # 检查是否是FUNC宏
                    is_func_macro = 'FUNC(' in line

                    function_info = FunctionInfo(
                        name=func_name,
                        start_line=i + 1,  # 转换为1基索引
                        end_line=end_line + 1,  # 转换为1基索引
                        return_type=return_type,
                        parameters=params,
                        is_func_macro=is_func_macro
                    )
                    # 检查是否存在同名函数
                    if func_name in function_info_re:
                        # 合并函数信息
                        line_function_name = change_function_name_by_line(function_info)
                        function_info_re[func_name].other_function_definitions.append({line_function_name:function_info})
                    else:
                        function_info_re[func_name] = function_info
                    i = end_line + 1
                else:
                    # 可能是跨行函数签名，尝试处理
                    multi_func_name, multi_return_type, multi_params, next_idx = self._handle_multiline_function_signature(i)

                    if multi_func_name:
                        end_line = self._find_function_end(next_idx)
                        if end_line != -1:
                            is_func_macro = any('FUNC(' in self.lines[j] for j in range(i, next_idx + 1))

                            function_info = FunctionInfo(
                                name=multi_func_name,
                                start_line=i + 1,
                                end_line=end_line + 1,
                                return_type=multi_return_type,
                                parameters=multi_params,
                                is_func_macro=is_func_macro
                            )

                            # function_info_re[multi_func_name] = function_info
                            # 检查是否存在同名函数
                            if multi_func_name in function_info_re:
                                # 合并函数信息
                                line_function_name = change_function_name_by_line(function_info)
                                function_info_re[multi_func_name].other_function_definitions.append({line_function_name:function_info})
                            else:
                                function_info_re[multi_func_name] = function_info
                            i = end_line + 1
                        else:
                            i = next_idx + 1
                    else:
                        i += 1
            elif self._is_potential_multiline_function_start(line):
                # 检测到潜在的多行函数开始，尝试处理
                multi_func_name, multi_return_type, multi_params, next_idx = self._handle_multiline_function_signature(i)

                if multi_func_name:
                    end_line = self._find_function_end(next_idx)
                    if end_line != -1:
                        is_func_macro = any('FUNC(' in self.lines[j] for j in range(i, next_idx + 1))

                        function_info = FunctionInfo(
                            name=multi_func_name,
                            start_line=i + 1,
                            end_line=end_line + 1,
                            return_type=multi_return_type,
                            parameters=multi_params,
                            is_func_macro=is_func_macro
                        )

                        # function_info_re[multi_func_name] = function_info
                        # 检查是否存在同名函数
                        if multi_func_name in function_info_re:
                            # 合并函数信息
                            line_function_name = change_function_name_by_line(function_info)
                            function_info_re[multi_func_name].other_function_definitions.append({line_function_name:function_info})
                        else:
                            function_info_re[multi_func_name] = function_info
                        i = end_line + 1
                    else:
                        i = next_idx + 1
                else:
                    i += 1
            else:
                i += 1

        # 加一个函数名过滤，如果是宏函数则不要
        filtered_function_info = {}
        for func_name, func_info in function_info_re.items():
            # 过滤掉宏函数：使用is_conventional_macro_name检查函数名是否符合宏的命名规范
            if not is_conventional_macro_name(func_name):
                filtered_function_info[func_name] = func_info

        return filtered_function_info

    def list_all_functions(self) -> List[str]:
        """
        列出文件中的所有函数名

        Returns:
            函数名列表
        """
        return list(self.functions_info.keys())

    def get_functions_by_tree_sitter(self, use_macro_function_format: bool = True,
                                   remove_macro_statement: bool = True) -> Dict[str, FunctionInfo]:
        """
        使用 tree-sitter 获取函数信息

        Args:
            use_macro_function_format: 是否使用宏函数格式
            remove_macro_statement: 是否移除宏语句

        Returns:
            Dict[str, FunctionInfo]: 函数信息字典，键为函数名，值为FunctionInfo对象
        """
        try:
            # 使用 TreeSitterFunctionExtractor 提取函数信息
            extractor = TreeSitterFunctionExtractor(
                self.file_path,
                use_macro_function_format=use_macro_function_format,
                remove_macro_statement=remove_macro_statement
            )

            # 获取所有函数信息
            tree_sitter_functions = extractor.get_all_functions()

            # 转换为 FunctionInfo 格式
            result = {}
            for func_name, func_info in tree_sitter_functions.items():
                # 创建 FunctionInfo 对象，兼容现有的数据结构
                function_info = FunctionInfo(
                    name=func_name,
                    start_line=func_info.start_line,
                    end_line=func_info.end_line,
                    return_type="",  # TreeSitter 提取器没有返回类型信息
                    parameters="",   # TreeSitter 提取器没有参数信息
                    is_func_macro=False  # 默认为False
                )
                result[func_name] = function_info

            return result

        except Exception as e:
            print(f"警告: tree-sitter 函数提取失败: {e}")
            return {}

    def merge_function_results(self, regex_functions: Dict[str, FunctionInfo],
                             tree_sitter_functions: Dict[str, FunctionInfo]) -> Dict[str, FunctionInfo]:
        """
        合并正则表达式和 tree-sitter 的函数提取结果

        合并规则：
        1. 如果函数名相同且开始行、结束行相同，则直接merge
        2. 如果函数名不同，但是开始行和结束行与另一个不同名的函数间存在冲突，则不要
        3. 若函数名相同，但是开始行和结束行不同，则以tree_sitter为准

        Args:
            regex_functions: 正则表达式提取的函数信息
            tree_sitter_functions: tree-sitter 提取的函数信息

        Returns:
            Dict[str, FunctionInfo]: 合并后的函数信息
        """
        merged_functions = {}

        # 首先添加所有正则表达式提取的函数
        for func_name, func_info in regex_functions.items():
            merged_functions[func_name] = func_info

        # 处理 tree-sitter 提取的函数
        for ts_func_name, ts_func_info in tree_sitter_functions.items():
            if ts_func_name in merged_functions:
                # 函数名相同的情况
                regex_func_info = merged_functions[ts_func_name]

                if (regex_func_info.start_line == ts_func_info.start_line and
                    regex_func_info.end_line == ts_func_info.end_line):
                    # 规则1: 函数名相同且开始行、结束行相同，则直接merge
                    # 保留正则表达式的详细信息，但可以补充 tree-sitter 的信息
                    merged_functions[ts_func_name] = regex_func_info
                else:
                    # 规则3: 函数名相同，但是开始行和结束行不同，则以tree_sitter为准
                    # 保留 tree-sitter 的位置信息，但尽量保留正则表达式的详细信息
                    merged_func_info = FunctionInfo(
                        name=ts_func_name,
                        start_line=ts_func_info.start_line,  # 使用 tree-sitter 的位置
                        end_line=ts_func_info.end_line,      # 使用 tree-sitter 的位置
                        return_type=regex_func_info.return_type,  # 保留正则的返回类型
                        parameters=regex_func_info.parameters,    # 保留正则的参数信息
                        is_func_macro=regex_func_info.is_func_macro,  # 保留正则的宏信息
                        other_function_definitions=ts_func_info.other_function_definitions
                    )
                    merged_functions[ts_func_name] = merged_func_info
            else:
                # 函数名不同的情况，检查是否与现有函数存在位置冲突
                has_conflict = False

                for existing_func_name, existing_func_info in merged_functions.items():
                    if existing_func_name != ts_func_name:
                        # 检查行号范围是否重叠
                        if (self._ranges_overlap(ts_func_info.start_line, ts_func_info.end_line,
                                                existing_func_info.start_line, existing_func_info.end_line)):
                            # 规则2: 存在冲突，不添加此函数
                            has_conflict = True
                            break

                if not has_conflict:
                    # 没有冲突，可以添加此函数
                    merged_functions[ts_func_name] = ts_func_info

        return merged_functions

    def _ranges_overlap(self, start1: int, end1: int, start2: int, end2: int) -> bool:
        """
        检查两个行号范围是否重叠

        Args:
            start1, end1: 第一个范围的开始和结束行号
            start2, end2: 第二个范围的开始和结束行号

        Returns:
            bool: 是否存在重叠
        """
        return not (end1 < start2 or end2 < start1)

    def get_functions_with_merge(self, use_tree_sitter: bool = True,
                               merge_results: bool = True,
                               use_macro_function_format: bool = True,
                               remove_macro_statement: bool = True) -> Dict[str, FunctionInfo]:
        """
        获取函数信息，支持 tree-sitter 和结果合并

        Args:
            use_tree_sitter: 是否使用 tree-sitter 提取
            merge_results: 是否合并 tree-sitter 和正则表达式的结果
            use_macro_function_format: 是否使用宏函数格式
            remove_macro_statement: 是否移除宏语句

        Returns:
            Dict[str, FunctionInfo]: 函数信息字典
        """
        # 获取正则表达式提取的结果
        regex_functions = self._parse_functions_by_re()

        if not use_tree_sitter:
            return regex_functions

        # 获取 tree-sitter 提取的结果
        tree_sitter_functions = self.get_functions_by_tree_sitter(
            use_macro_function_format=use_macro_function_format,
            remove_macro_statement=remove_macro_statement
        )

        if not merge_results:
            # 不合并，选择更全面的结果
            if len(tree_sitter_functions) >= len(regex_functions):
                return tree_sitter_functions
            else:
                return regex_functions

        # 合并结果
        return self.merge_function_results(regex_functions, tree_sitter_functions)
