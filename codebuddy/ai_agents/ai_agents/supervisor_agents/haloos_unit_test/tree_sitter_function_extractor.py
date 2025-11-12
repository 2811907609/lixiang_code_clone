import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import remove_comments_with_mapping, is_conventional_macro_name,change_function_name_by_line
from ai_agents.supervisor_agents.haloos_unit_test.remove_c_file_macro_if_endif import remove_c_macro_directives
from ai_agents.supervisor_agents.haloos_unit_test.hybrid_function_macro_detector import HybridFunctionMacroDetector, DetectionMethod
@dataclass
class FunctionInfo:
    """函数信息数据类"""
    name: str
    start_line: int
    end_line: int
    other_function_definitions: List[dict] = field(default_factory=list)


class TreeSitterFunctionExtractor:
    """简化的TreeSitter函数提取器，只处理标准函数定义"""

    def __init__(self, file_path: str, use_macro_function_format = True, remove_macro_statement=True, macro_detection_method: DetectionMethod = DetectionMethod.MERGED):
        self.file_path = file_path
        self.content = ""
        self.functions_info: Dict[str, FunctionInfo] = {}

        # 初始化 tree-sitter
        self.c_language = Language(tsc.language())
        self.parser = Parser(self.c_language)

        self.use_macro_function_format = use_macro_function_format
        self.remove_macro_statement = remove_macro_statement
        self.macro_detection_method = macro_detection_method

        # 加载和解析文件
        self._load_file()
        self._extract_functions()

    def _load_file(self):
        """加载C源文件内容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.content = f.read()

            if self.remove_macro_statement:

                wrong_comment_remove = False
                # 注释去除
                self.content,line_mapping = remove_comments_with_mapping(self.content)

                for before_line, after_line in line_mapping.items():
                    if before_line != after_line:
                        wrong_comment_remove = True
                        break
                # 如果注释去除没错
                if not wrong_comment_remove:
                    # if else等等去除但是保持当前行
                    # 这么测试会去掉由于复杂问题的提取问题，但是也有需要特殊处理的
                    self.content = remove_c_macro_directives(self.content)

            if self.use_macro_function_format:
                self.content = self.replace_macro_with_first_function(self.content)
                # print(self.content)




        except FileNotFoundError as e:
            raise FileNotFoundError(f"文件不存在: {self.file_path}") from e
        except Exception as e:
            raise Exception(f"读取文件失败: {e}") from e

    def _extract_functions(self):
        """只提取标准函数定义"""
        if not self.content:
            return

        # 解析代码
        tree = self.parser.parse(self.content.encode('utf-8'))

        # 只使用标准函数定义遍历
        self._traverse_node_standard(tree.root_node)

    def _traverse_node_standard(self, node: tree_sitter.Node):
        """标准函数定义遍历"""
        if node.type == 'function_definition':
            # 过滤掉错误识别的语句（如 else if, if, while 等）
            if self._is_valid_function_definition(node):
                self._extract_standard_function(node)

        # 递归遍历子节点
        for child in node.children:
            self._traverse_node_standard(child)

    def _is_valid_function_definition(self, function_node: tree_sitter.Node) -> bool:
        """检查是否是有效的函数定义，过滤掉错误识别的控制流语句和包含太多声明的代码块"""
        if len(function_node.children) < 2:
            return False

        # 1. 检查第一层子节点是否包含过多的declaration节点（这是错误识别的关键特征）
        declaration_count = 0
        for child in function_node.children:
            if child.type == 'declaration':
                declaration_count += 1

        # 如果第一层包含超过3个declaration节点，很可能是错误识别
        # 真正的函数定义通常不会在第一层包含多个declaration
        if declaration_count > 3:
            return False

        # 2. 检查第一个子节点
        first_child = function_node.children[0]

        # 如果第一个子节点是type_identifier，检查是否是控制流关键字
        if first_child.type == 'type_identifier':
            first_text = first_child.text.decode('utf-8')

            # 常见的被错误识别为函数定义的关键字
            invalid_keywords = {
                'else', 'if', 'while', 'for', 'switch', 'do', 'return',
                'break', 'continue', 'goto', 'case', 'default'
            }

            # 如果第一个节点是控制流关键字，进一步检查确认这不是真正的函数
            if first_text in invalid_keywords:
                # 检查第二个子节点是否是function_declarator且以控制流关键字开头
                if len(function_node.children) > 1:
                    second_child = function_node.children[1]
                    if second_child.type == 'function_declarator':
                        declarator_text = second_child.text.decode('utf-8')
                        # 如果是 else if 模式，则确实是错误识别
                        if first_text == 'else' and declarator_text.startswith('if '):
                            return False
                        # 如果是单独的控制流关键字且声明器也是控制流模式
                        elif declarator_text.startswith(('if ', 'while ', 'for ', 'switch ', 'do ')):
                            return False
                # 对于单独的控制流关键字（如单独的else），也过滤掉
                return False

        # 对于其他情况，认为是有效的函数定义
        return True


    def _extract_standard_function(self, function_node: tree_sitter.Node):
        """提取标准函数定义"""
        try:
            # 检查函数节点是否包含错误节点
            if self._has_error_node(function_node):
                # 尝试修复并重新提取函数名
                function_name = self._get_function_name_with_repair(function_node)
            else:
                function_name = self._get_function_name_from_definition(function_node)

            if not function_name:
                return

            # 检查函数名是否符合宏的命名规范，如果是则过滤掉
            if is_conventional_macro_name(function_name):
                return

            # TreeSitter使用0基索引，转换为1基索引以与CFunctionLocator对齐
            start_line = function_node.start_point[0] + 1
            end_line = function_node.end_point[0] + 1

            func_info = FunctionInfo(
                name=function_name,
                start_line=start_line,
                end_line=end_line
            )

            if function_name in self.functions_info:
                # 合并函数信息
                line_function_name = change_function_name_by_line(func_info)
                self.functions_info[function_name].other_function_definitions.append({line_function_name:func_info})
            else:
                self.functions_info[function_name] = func_info

        except Exception:
            pass  # 静默处理错误


    def _get_function_name_from_definition(self, function_node: tree_sitter.Node) -> Optional[str]:
        """从标准函数定义节点中获取函数名称，只处理标准的函数声明"""
        def find_identifier_in_declarator(node: tree_sitter.Node) -> Optional[str]:
            if node.type == 'identifier':
                return node.text.decode('utf-8')

            for child in node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf-8')
                elif child.type in ['function_declarator', 'pointer_declarator']:
                    # 只处理标准的 declarator，排除 parenthesized_declarator
                    result = find_identifier_in_declarator(child)
                    if result:
                        return result
            return None

        # 只查找标准的 function_declarator 和 pointer_declarator
        for child in function_node.children:
            if child.type in ['function_declarator', 'pointer_declarator']:
                name = find_identifier_in_declarator(child)
                if name:
                    return name

        # 如果没有找到标准的 declarator，直接返回 None
        # 不强行提取，保持严谨性
        return None

    def _has_error_node(self, node: tree_sitter.Node) -> bool:
        """递归检查节点及其子节点是否包含错误节点"""
        if node.type == 'ERROR':
            return True

        # 递归检查所有子节点
        for child in node.children:
            if self._has_error_node(child):
                return True

        return False

    def _get_function_name_with_repair(self, function_node: tree_sitter.Node) -> Optional[str]:
        """
        修复包含错误节点的函数定义，去除错误节点后重新提取函数名

        Args:
            function_node: 包含错误节点的函数定义节点

        Returns:
            Optional[str]: 修复后提取的函数名，如果失败返回None
        """
        try:
            # 获取函数节点的文本内容
            function_text = function_node.text.decode('utf-8')

            # 移除错误节点并重构函数文本
            repaired_text = self._remove_error_nodes_from_text(function_node, function_text)


            if not repaired_text:
                return None

            # 重新解析修复后的文本
            repaired_tree = self.parser.parse(repaired_text.encode('utf-8'))

            # 在修复后的AST中查找函数定义
            for node in repaired_tree.root_node.children:
                if node.type == 'function_definition':
                    # 不管是否还有错误节点，都尝试提取函数名
                    # 因为函数签名部分通常是正确的，错误通常在函数体中
                    function_name = self._get_function_name_from_definition(node)
                    if function_name:
                        return function_name

            return None

        except Exception:
            return None

    def _remove_error_nodes_from_text(self, node: tree_sitter.Node, original_text: str) -> str:
        """
        从节点文本中移除所有错误节点对应的文本片段

        Args:
            node: 原始节点
            original_text: 原始文本

        Returns:
            str: 移除错误节点后的文本
        """
        try:
            # 收集所有ERROR节点的文本位置
            error_ranges = []
            self._collect_error_node_ranges(node, error_ranges)

            if not error_ranges:
                return original_text

            # 按照位置倒序排列，从后往前替换，避免位置偏移问题
            error_ranges.sort(key=lambda x: x[0], reverse=True)

            # 获取原始文本的字节版本
            original_bytes = original_text.encode('utf-8')
            result_bytes = bytearray(original_bytes)

            # 从后往前移除ERROR节点对应的字节范围
            for start_byte, end_byte in error_ranges:
                # 将ERROR节点对应的字节范围替换为空
                del result_bytes[start_byte:end_byte]

            # 转换回字符串
            return result_bytes.decode('utf-8')

        except Exception:
            return original_text

    def _collect_error_node_ranges(self, node: tree_sitter.Node, error_ranges: List[Tuple[int, int]]):
        """
        收集所有ERROR节点的字节范围

        Args:
            node: 当前节点
            error_ranges: 用于收集ERROR节点范围的列表
        """
        if node.type == 'ERROR':
            # 记录ERROR节点的字节范围
            start_byte = node.start_byte
            end_byte = node.end_byte
            error_ranges.append((start_byte, end_byte))
            return

        # 递归处理子节点
        for child in node.children:
            self._collect_error_node_ranges(child, error_ranges)


    def get_function_info(self, function_name: str) -> Optional[FunctionInfo]:
        """获取指定函数的信息"""
        return self.functions_info.get(function_name)

    def get_all_functions(self) -> Dict[str, FunctionInfo]:
        """获取所有函数信息"""
        return self.functions_info.copy()

    def list_function_names(self) -> List[str]:
        """获取所有函数名称列表"""
        return list(self.functions_info.keys())

    def print_function_summary(self):
        """打印函数摘要信息"""
        print(f"文件: {self.file_path}")
        print(f"找到 {len(self.functions_info)} 个函数:")
        print("-" * 50)

        for func_name, func_info in self.functions_info.items():
            print(f"函数: {func_name}")
            print(f"  行范围: {func_info.start_line}-{func_info.end_line}")
            print()

    def get_macro_detection_info(self) -> Optional[HybridFunctionMacroDetector]:
        """获取宏检测详细信息"""
        if not self.content:
            return None

        try:
            return HybridFunctionMacroDetector(self.content)
        except Exception:
            return None

    def replace_macro_with_first_function(self, content: str) -> str:
        """
        基于混合检测器提取的宏信息，将同一行的宏文本替换成其第一个函数参数

        Args:
            content: C代码内容字符串

        Returns:
            str: 替换后的代码内容
        """
        if not content:
            return content

        try:
            # 使用混合检测器提取宏信息
            hybrid_detector = HybridFunctionMacroDetector(content)
            macro_infos = hybrid_detector.get_function_macros(self.macro_detection_method)
            if not macro_infos:
                return content

            # 将内容按行分割
            lines = content.splitlines()

            # 按行号倒序处理，避免替换时行号变化影响后续处理
            macro_infos_sorted = sorted(macro_infos, key=lambda x: x.start_line, reverse=True)

            for macro_info in macro_infos_sorted:
                # 检查宏是否在单行内（start_line == end_line）
                if macro_info.start_line == macro_info.end_line:
                    # 获取宏的第一个函数参数（通常是返回类型）
                    if macro_info.macro_arguments and len(macro_info.macro_arguments) > 0:
                        first_function = macro_info.macro_arguments[0]

                        line_index = macro_info.start_line

                        if 0 <= line_index < len(lines):
                            original_line = lines[line_index]

                            # 在该行中查找并替换宏文本
                            if macro_info.full_text in original_line:
                                # 将宏文本替换为第一个函数参数
                                modified_line = original_line.replace(macro_info.full_text, first_function)
                                lines[line_index] = modified_line

            # 重新组合成字符串
            return '\n'.join(lines)

        except Exception as e:
            # 如果处理过程中出现异常，返回原始内容
            print(f"警告：宏替换过程中发生错误: {e}")
            return content
