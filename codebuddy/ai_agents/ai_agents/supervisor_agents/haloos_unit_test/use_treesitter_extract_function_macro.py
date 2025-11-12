import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FunctionMacroInfo:
    """函数宏信息"""
    macro_name: str          # 宏名，如 "FUNC"
    macro_arguments: List[str]  # 宏参数列表，如 ["void", "OS_CODE"]
    start_line: int          # 起始行号
    end_line: int           # 结束行号
    full_text: str           # 宏部分的文本，如 "FUNC(void, WDGM_CODE)"
    declaration_text: str = ""  # 完整的声明文本（可选）


class FunctionMacroDetector:
    """函数宏检测器"""

    def __init__(self, content: str):
        """
        初始化检测器

        Args:
            content: C代码内容
        """
        self.content = content
        self.lines = content.splitlines()
        self.function_macros: List[FunctionMacroInfo] = []

        # 初始化 Tree-sitter
        self.c_language = Language(tsc.language())
        self.parser = Parser(self.c_language)

        # 识别函数宏
        self._detect_function_macros()

    def _detect_function_macros(self):
        """检测代码中的函数宏"""
        if not self.content:
            return

        # 使用 Tree-sitter 解析代码
        tree = self.parser.parse(self.content.encode('utf-8'))
        self._analyze_ast(tree.root_node)

    def _analyze_ast(self, node: tree_sitter.Node, parent: tree_sitter.Node = None):
        """分析 AST 查找函数宏模式"""
        # 定义可能包含 FUNC 宏的节点类型
        candidate_node_types = ['declaration', 'function_definition', 'ERROR', 'expression_statement', 'call_expression']

        # 检查当前节点是否是候选类型，并且包含函数宏
        if node.type in candidate_node_types and self._contains_function_macro(node):
            macro_info = self._extract_macro_info_from_candidate_node(node)
            if macro_info:
                self.function_macros.append(macro_info)

        # 特殊处理：检查 function_declarator 节点中的宏模式
        if node.type == 'function_declarator' and self._is_function_declarator_macro(node):
            # 如果父节点是 function_definition，直接使用
            if parent and parent.type == 'function_definition':
                macro_info = self._extract_macro_from_function_declarator(parent)
                if macro_info:
                    self.function_macros.append(macro_info)

        # 递归遍历子节点
        for child in node.children:
            self._analyze_ast(child, node)

    def _find_function_macro_patterns(self, translation_unit: tree_sitter.Node):
        """查找函数宏模式"""
        children = translation_unit.children

        for i in range(len(children)):
            current = children[i]

            # 新模式：单个 declaration 节点包含 macro_type_specifier
            if self._is_macro_declaration_pattern(current):
                macro_info = self._extract_macro_info_from_declaration(current)
                if macro_info:
                    self.function_macros.append(macro_info)
                continue

            # 原有模式：expression_statement (宏调用) + function_definition
            if i < len(children) - 1:
                next_node = children[i + 1]
                if self._is_function_macro_pattern(current, next_node):
                    macro_info = self._extract_macro_info(current, next_node)
                    if macro_info:
                        self.function_macros.append(macro_info)

    def _is_function_macro_pattern(self, expr_stmt: tree_sitter.Node, next_node: tree_sitter.Node) -> bool:
        """
        判断是否是函数宏模式的特征：
        模式1: expression_statement + function_definition（简单情况）
        模式2: expression_statement + declaration（复杂情况，包含ERROR节点）

        共同特征：
        1. expression_statement 包含 call_expression
        2. call_expression 有至少两个参数（返回类型、属性）
        """
        # 检查第一个节点是表达式语句
        if expr_stmt.type != 'expression_statement':
            return False

        # 检查第二个节点是 function_definition 或 declaration
        if next_node.type not in ['function_definition', 'declaration']:
            return False

        # 检查表达式语句是否包含函数调用
        call_expr = self._get_call_expression(expr_stmt)
        if not call_expr:
            return False

        # 检查调用表达式是否有参数列表（至少2个参数）
        if not self._has_valid_argument_list(call_expr):
            return False

        # 对于 function_definition 模式，不需要额外检查
        if next_node.type == 'function_definition':
            return True

        # 对于 declaration 模式，检查是否包含 ERROR 节点和 macro_type_specifier
        if next_node.type == 'declaration':
            has_error = self._has_error_node(next_node)
            has_macro_type = self._has_macro_type_specifier(next_node)
            return has_error or has_macro_type  # 至少满足一个条件

        return False

    def _is_macro_declaration_pattern(self, decl_node: tree_sitter.Node) -> bool:
        """
        判断是否是包含宏类型说明符的声明模式
        模式：declaration 节点包含 macro_type_specifier 和 function_declarator
        """
        if decl_node.type != 'declaration':
            return False

        # 检查是否包含 macro_type_specifier 和 function_declarator
        has_macro_type = False
        has_function_declarator = False

        for child in decl_node.children:
            if child.type == 'macro_type_specifier':
                has_macro_type = True
            elif child.type == 'function_declarator':
                has_function_declarator = True

        return has_macro_type and has_function_declarator

    def _extract_macro_info_from_declaration(self, decl_node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """从 declaration 节点中提取宏信息"""
        try:
            macro_type_specifier = None

            # 查找 macro_type_specifier
            for child in decl_node.children:
                if child.type == 'macro_type_specifier':
                    macro_type_specifier = child
                    break

            if not macro_type_specifier:
                return None

            # 提取宏名 - 通常是第一个 identifier
            macro_name = ""
            macro_arguments = []

            for child in macro_type_specifier.children:
                if child.type == 'identifier':
                    macro_name = child.text.decode('utf-8')
                    break

            # 提取宏参数 - 更精确的方式
            self._extract_macro_arguments_from_specifier(macro_type_specifier, macro_arguments)

            # 使用精确的行范围计算方法
            start_line, end_line = self._get_precise_macro_range(macro_type_specifier)

            # full_text 只包含宏部分
            macro_full_text = macro_type_specifier.text.decode('utf-8')

            # declaration_text 包含完整声明
            declaration_text = decl_node.text.decode('utf-8')

            return FunctionMacroInfo(
                macro_name=macro_name,
                macro_arguments=macro_arguments,
                start_line=start_line,
                end_line=end_line,
                full_text=macro_full_text,
                declaration_text=declaration_text
            )

        except Exception:
            return None

    def _extract_macro_arguments_from_specifier(self, macro_type_specifier: tree_sitter.Node, macro_arguments: List[str]):
        """从 macro_type_specifier 中提取宏参数"""
        in_parentheses = False
        current_arg = ""

        for child in macro_type_specifier.children:
            if child.type == '(':
                in_parentheses = True
                continue
            elif child.type == ')':
                # 添加最后一个参数
                if current_arg.strip():
                    macro_arguments.append(current_arg.strip())
                break
            elif in_parentheses:
                if child.type == ',':
                    # 保存当前参数并开始新参数
                    if current_arg.strip():
                        macro_arguments.append(current_arg.strip())
                    current_arg = ""
                elif child.type in ['type_identifier', 'identifier']:
                    if current_arg:
                        current_arg += " "
                    current_arg += child.text.decode('utf-8')
                elif child.type == 'type_descriptor':
                    # 处理复合类型 - 获取整个类型描述符的文本
                    if current_arg:
                        current_arg += " "
                    current_arg += child.text.decode('utf-8')
                elif child.type == 'ERROR':
                    # 处理 ERROR 节点 - 这可能包含逗号分隔的参数
                    error_text = child.text.decode('utf-8').strip()

                    # 检查ERROR节点是否包含逗号分隔的内容
                    if ',' in error_text:
                        # 拆分ERROR节点中的内容
                        parts = error_text.split(',')

                        # 处理第一部分（添加到当前参数）
                        first_part = parts[0].strip()
                        if first_part:
                            if current_arg:
                                current_arg += " "
                            current_arg += first_part

                        # 保存当前参数
                        if current_arg.strip():
                            macro_arguments.append(current_arg.strip())

                        # 处理后续部分（每个都是新参数的开始）
                        for part in parts[1:]:
                            part = part.strip()
                            if part:
                                current_arg = part
                            else:
                                current_arg = ""
                    else:
                        # ERROR节点不包含逗号，直接添加到当前参数
                        if current_arg:
                            current_arg += " "
                        current_arg += error_text

    def _extract_macro_arguments_from_parameter_list(self, parameter_list: tree_sitter.Node, macro_arguments: List[str]):
        """从 parameter_list 中提取宏参数"""
        current_arg = ""

        for child in parameter_list.children:
            if child.type == '(':
                continue
            elif child.type == ')':
                # 添加最后一个参数
                if current_arg.strip():
                    macro_arguments.append(current_arg.strip())
                break
            elif child.type == ',':
                # 保存当前参数并开始新参数
                if current_arg.strip():
                    macro_arguments.append(current_arg.strip())
                current_arg = ""
            elif child.type in ['type_identifier', 'identifier', 'primitive_type']:
                if current_arg:
                    current_arg += " "
                current_arg += child.text.decode('utf-8')
            elif child.type == 'parameter_declaration':
                # 直接处理参数声明
                param_text = child.text.decode('utf-8').strip()
                if param_text:
                    macro_arguments.append(param_text)
            elif child.type == 'ERROR':
                # 处理 ERROR 节点中可能包含的参数
                error_text = child.text.decode('utf-8').strip()
                if error_text:
                    if current_arg:
                        current_arg += " "
                    current_arg += error_text

    def _get_precise_macro_range(self, macro_node: tree_sitter.Node) -> Tuple[int, int]:
        """
        获取宏调用的精确行范围
        确保返回的行范围只包含宏调用本身，而不是整个声明或函数定义
        """
        # 如果是 macro_type_specifier，直接使用其范围
        if macro_node.type == 'macro_type_specifier':
            start_line = macro_node.start_point[0]
            end_line = macro_node.end_point[0]
            return start_line, end_line

        # 如果是 expression_statement，查找其中的 call_expression
        if macro_node.type == 'expression_statement':
            for child in macro_node.children:
                if child.type == 'call_expression':
                    start_line = child.start_point[0]
                    end_line = child.end_point[0]
                    return start_line, end_line

        # 如果是其他类型的节点，递归查找 macro_type_specifier 或 call_expression
        for child in macro_node.children:
            if child.type in ['macro_type_specifier', 'call_expression']:
                start_line = child.start_point[0]
                end_line = child.end_point[0]
                return start_line, end_line

        # 默认返回节点自身的范围
        start_line = macro_node.start_point[0]
        end_line = macro_node.end_point[0]
        return start_line, end_line

    def _is_function_macro_name(self, name: str) -> bool:
        """
        判断是否是函数属性宏名

        规则：
        1. 全大写字母
        2. 可以包含下划线
        3. 可以包含数字
        4. 至少包含一个字母（排除纯数字或符号）
        """
        if not name:
            return False

        # 检查是否只包含大写字母、下划线和数字
        if not all(c.isupper() or c == '_' or c.isdigit() for c in name):
            return False

        # 确保至少包含一个字母（排除纯数字或下划线的情况）
        if not any(c.isupper() for c in name):
            return False

        return True

    def _contains_function_macro(self, node: tree_sitter.Node) -> bool:
        """检查节点是否包含函数宏（通过查找 macro_type_specifier 或函数宏标识符）"""
        # 方法1：查找 macro_type_specifier 子节点
        if self._has_macro_type_specifier_recursive(node):
            return True

        # 方法2：查找包含函数宏的标识符（通用判断）
        if self._has_function_macro_identifier(node):
            return True

        # 方法3：检查是否是函数宏调用表达式
        if self._is_function_macro_call_expression(node):
            return True

        return False

    def _has_macro_type_specifier_recursive(self, node: tree_sitter.Node) -> bool:
        """递归查找 macro_type_specifier 节点"""
        if node.type == 'macro_type_specifier':
            return True

        for child in node.children:
            if self._has_macro_type_specifier_recursive(child):
                return True

        return False

    def _has_function_macro_identifier(self, node: tree_sitter.Node) -> bool:
        """查找函数宏标识符"""
        if node.type == 'identifier':
            identifier_name = node.text.decode('utf-8')
            if self._is_function_macro_name(identifier_name):
                return True

        for child in node.children:
            if self._has_function_macro_identifier(child):
                return True

        return False

    def _is_function_macro_call_expression(self, node: tree_sitter.Node) -> bool:
        """检查是否是函数宏调用表达式"""
        if node.type == 'call_expression':
            # 检查第一个子节点是否是 identifier 且符合宏名规则
            if node.children and node.children[0].type == 'identifier':
                func_name = node.children[0].text.decode('utf-8')
                if self._is_function_macro_name(func_name):
                    # 确保有参数列表且至少有2个参数
                    return self._has_valid_argument_list(node)
        return False

    def _extract_macro_info_from_candidate_node(self, node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """从候选节点中提取宏信息"""
        try:
            # 首先尝试查找 macro_type_specifier
            macro_type_specifier = self._find_macro_type_specifier(node)
            if macro_type_specifier:
                macro_info = self._extract_macro_info_from_specifier(macro_type_specifier, node)
                if macro_info:  # 只有验证通过的宏信息才返回
                    return macro_info

            # 检查是否是函数宏调用表达式
            if self._is_function_macro_call_expression(node):
                return self._extract_macro_info_from_call_expression(node)

            # 新增：检查 function_definition 中的 function_declarator 模式
            if node.type == 'function_definition':
                func_declarator_info = self._extract_macro_from_function_declarator(node)
                if func_declarator_info:
                    return func_declarator_info

            # 如果没有找到 macro_type_specifier，尝试其他方法
            return self._extract_macro_info_fallback(node)

        except Exception:
            return None

    def _find_macro_type_specifier(self, node: tree_sitter.Node) -> Optional[tree_sitter.Node]:
        """查找 macro_type_specifier 节点"""
        if node.type == 'macro_type_specifier':
            return node

        for child in node.children:
            result = self._find_macro_type_specifier(child)
            if result:
                return result

        return None

    def _extract_macro_info_from_specifier(self, macro_type_specifier: tree_sitter.Node, parent_node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """从 macro_type_specifier 中提取宏信息"""
        # 提取宏名
        macro_name = ""
        for child in macro_type_specifier.children:
            if child.type == 'identifier':
                candidate_name = child.text.decode('utf-8')
                # 验证是否是真正的宏名
                if self._is_function_macro_name(candidate_name):
                    macro_name = candidate_name
                    break

        # 如果没有找到有效的宏名，返回None
        if not macro_name:
            return None

        # 提取宏参数
        macro_arguments = []
        self._extract_macro_arguments_from_specifier(macro_type_specifier, macro_arguments)

        # 使用精确的行范围计算方法
        start_line, end_line = self._get_precise_macro_range(macro_type_specifier)

        # full_text 只包含宏部分
        macro_full_text = macro_type_specifier.text.decode('utf-8')

        # declaration_text 包含完整节点
        declaration_text = parent_node.text.decode('utf-8')

        return FunctionMacroInfo(
            macro_name=macro_name,
            macro_arguments=macro_arguments,
            start_line=start_line,
            end_line=end_line,
            full_text=macro_full_text,
            declaration_text=declaration_text
        )

    def _extract_macro_info_from_call_expression(self, call_expr_node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """从 call_expression 节点中提取函数宏信息"""
        try:
            # 提取宏名
            macro_name = ""
            if call_expr_node.children and call_expr_node.children[0].type == 'identifier':
                macro_name = call_expr_node.children[0].text.decode('utf-8')

            # 提取宏参数列表
            macro_arguments = self._extract_macro_arguments_list(call_expr_node)

            # 使用精确的行范围计算方法
            start_line, end_line = self._get_precise_macro_range(call_expr_node)

            # full_text 包含整个调用表达式
            full_text = call_expr_node.text.decode('utf-8')

            return FunctionMacroInfo(
                macro_name=macro_name,
                macro_arguments=macro_arguments,
                start_line=start_line,
                end_line=end_line,
                full_text=full_text,
                declaration_text=""
            )

        except Exception:
            return None

    def _extract_macro_from_function_declarator(self, function_def_node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """从 function_definition 中的 function_declarator 提取宏信息"""
        try:
            # 首先查找 macro_type_specifier 节点，这是真正的宏调用
            macro_type_specifier = None
            for child in function_def_node.children:
                if child.type == 'macro_type_specifier':
                    macro_type_specifier = child
                    break

            # 如果找到了 macro_type_specifier，优先使用它
            if macro_type_specifier:
                return self._extract_macro_info_from_specifier(macro_type_specifier, function_def_node)

            # 如果没有找到 macro_type_specifier，查找 function_declarator 中的宏模式
            func_declarator = None
            for child in function_def_node.children:
                if child.type == 'function_declarator':
                    func_declarator = child
                    break

            if not func_declarator or len(func_declarator.children) < 2:
                return None

            # 检查第一个子节点是否是 identifier (潜在的宏名)
            first_child = func_declarator.children[0]
            if first_child.type != 'identifier':
                return None

            macro_name = first_child.text.decode('utf-8')

            # 检查是否是宏名
            if not self._is_function_macro_name(macro_name):
                return None

            # 检查第二个子节点是否是 parameter_list (宏参数)
            second_child = func_declarator.children[1]
            if second_child.type != 'parameter_list':
                return None

            # 提取宏参数 - 改进的参数提取逻辑
            macro_args = []
            self._extract_macro_arguments_from_parameter_list(second_child, macro_args)

            # 计算行范围（只使用宏调用部分的范围）
            start_line = first_child.start_point[0]
            end_line = second_child.end_point[0]

            # 构造宏文本 - 只包含宏调用部分，而不是整个函数声明
            if macro_args:
                macro_args_str = ', '.join(macro_args)
                full_text = f"{macro_name}({macro_args_str})"
            else:
                full_text = f"{macro_name}()"

            # 获取完整声明文本
            declaration_text = function_def_node.text.decode('utf-8')

            return FunctionMacroInfo(
                macro_name=macro_name,
                macro_arguments=macro_args,
                start_line=start_line,
                end_line=end_line,
                full_text=full_text,
                declaration_text=declaration_text
            )

        except Exception:
            return None

    def _is_function_declarator_macro(self, func_declarator: tree_sitter.Node) -> bool:
        """检查 function_declarator 是否包含宏模式"""
        if func_declarator.type != 'function_declarator' or len(func_declarator.children) < 2:
            return False

        # 检查第一个子节点是否是宏名
        first_child = func_declarator.children[0]
        if first_child.type == 'identifier':
            macro_name = first_child.text.decode('utf-8')
            if self._is_function_macro_name(macro_name):
                # 检查第二个子节点是否是参数列表
                second_child = func_declarator.children[1]
                return second_child.type == 'parameter_list'

        return False

    def _find_parent_function_definition(self, node: tree_sitter.Node) -> Optional[tree_sitter.Node]:
        """查找包含指定节点的function_definition父节点"""
        # 这是一个简化实现，实际中可能需要更复杂的遍历逻辑
        # 由于我们在_analyze_ast中处理，可以传递上下文信息
        return None  # 暂时返回None，因为我们会在调用处直接传递parent

    def _extract_macro_info_fallback(self, node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """备用提取方法（用于特殊情况）"""
        # 这里可以处理一些特殊情况，比如 expression_statement 中的 FUNC 调用
        return None

    def _get_call_expression(self, expr_stmt: tree_sitter.Node) -> Optional[tree_sitter.Node]:
        """获取表达式语句中的调用表达式"""
        for child in expr_stmt.children:
            if child.type == 'call_expression':
                return child
        return None

    def _has_valid_argument_list(self, call_expr: tree_sitter.Node) -> bool:
        """检查调用表达式是否有有效的参数列表（至少2个参数）"""
        for child in call_expr.children:
            if child.type == 'argument_list':
                # 计算参数个数
                arg_count = 0
                for arg_child in child.children:
                    if arg_child.type == 'identifier':
                        arg_count += 1

                # 函数宏通常有2个参数：返回类型和属性
                return arg_count >= 2

        return False

    def _has_error_node(self, node: tree_sitter.Node) -> bool:
        """检查节点是否包含 ERROR 节点"""
        if node.type == 'ERROR':
            return True

        for child in node.children:
            if self._has_error_node(child):
                return True

        return False

    def _has_macro_type_specifier(self, decl: tree_sitter.Node) -> bool:
        """检查声明是否包含 macro_type_specifier"""
        for child in decl.children:
            if child.type == 'macro_type_specifier':
                return True
        return False

    def _extract_macro_info(self, expr_stmt: tree_sitter.Node, next_node: tree_sitter.Node) -> Optional[FunctionMacroInfo]:
        """提取函数宏信息"""
        try:
            call_expr = self._get_call_expression(expr_stmt)
            if not call_expr:
                return None

            # 提取宏名
            macro_name = ""
            if call_expr.children and call_expr.children[0].type == 'identifier':
                macro_name = call_expr.children[0].text.decode('utf-8')

            # 提取宏参数列表
            macro_arguments = self._extract_macro_arguments_list(call_expr)

            # 使用精确的行范围计算方法，优先使用 call_expression 的范围
            start_line, end_line = self._get_precise_macro_range(expr_stmt)
            full_text = call_expr.text.decode('utf-8') if call_expr else expr_stmt.text.decode('utf-8')

            return FunctionMacroInfo(
                macro_name=macro_name,
                macro_arguments=macro_arguments,
                start_line=start_line,
                end_line=end_line,
                full_text=full_text,
                declaration_text=""
            )

        except Exception:
            return None

    def _extract_macro_arguments_list(self, call_expr: tree_sitter.Node) -> List[str]:
        """提取宏参数列表"""
        arguments = []

        for child in call_expr.children:
            if child.type == 'argument_list':
                for arg_child in child.children:
                    if arg_child.type == 'identifier':
                        arguments.append(arg_child.text.decode('utf-8'))
                break

        return arguments


    def _find_function_end_line(self, start_line: int) -> int:
        """查找函数结束行"""
        brace_count = 0
        in_function_body = False

        for i in range(start_line - 1, len(self.lines)):
            line = self.lines[i]

            for char in line:
                if char == '{':
                    brace_count += 1
                    in_function_body = True
                elif char == '}':
                    brace_count -= 1

                    if in_function_body and brace_count == 0:
                        return i + 1

        return start_line

    def _get_text_range(self, start_line: int, end_line: int) -> str:
        """获取指定行范围的文本"""
        if start_line <= 0 or end_line <= 0 or start_line > len(self.lines):
            return ""

        end_line = min(end_line, len(self.lines))
        return '\n'.join(self.lines[start_line - 1:end_line])

    def get_function_macros(self) -> List[FunctionMacroInfo]:
        """获取所有检测到的函数宏"""
        return self.function_macros

    def print_summary(self):
        """打印检测摘要"""
        print(f"检测到 {len(self.function_macros)} 个函数宏:")
        print("-" * 60)

        for macro_info in self.function_macros:
            print(f"宏名: {macro_info.macro_name}")
            print(f"宏参数: {macro_info.macro_arguments}")
            print(f"行范围: {macro_info.start_line}-{macro_info.end_line}")
            print(f"宏文本: {macro_info.full_text}")
            if hasattr(macro_info, 'declaration_text') and macro_info.declaration_text:
                print("完整声明:")
                print(macro_info.declaration_text)
            print("-" * 60)
        print(f"检测到 {len(self.function_macros)} 个函数宏:")


def detect_function_macros(content: str) -> List[FunctionMacroInfo]:
    """
    检测代码内容中的函数宏

    Args:
        content: C代码内容

    Returns:
        List[FunctionMacroInfo]: 检测到的函数宏信息列表
    """
    detector = FunctionMacroDetector(content)
    return detector.get_function_macros()
