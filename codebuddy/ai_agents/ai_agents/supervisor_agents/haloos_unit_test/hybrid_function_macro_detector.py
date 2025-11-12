"""
混合函数宏检测器
结合tree-sitter和正则表达式两种方法的优势
"""

from typing import List, Dict
from enum import Enum
from ai_agents.supervisor_agents.haloos_unit_test.use_treesitter_extract_function_macro import FunctionMacroDetector, FunctionMacroInfo
from ai_agents.supervisor_agents.haloos_unit_test.regex_function_macro_detector import RegexFunctionMacroDetector


class DetectionMethod(Enum):
    """检测方法枚举"""
    TREE_SITTER = "tree_sitter"
    REGEX = "regex"
    MERGED = "merged"


class HybridFunctionMacroDetector:
    """混合函数宏检测器"""

    def __init__(self, content: str):
        """
        初始化混合检测器

        Args:
            content: C代码内容
        """
        self.content = content
        self.tree_sitter_macros: List[FunctionMacroInfo] = []
        self.regex_macros: List[FunctionMacroInfo] = []
        self.merged_macros: List[FunctionMacroInfo] = []

        # 执行两种检测方法
        self._detect_with_both_methods()

        # 执行合并
        self._merge_results()

    def _detect_with_both_methods(self):
        """使用两种方法检测函数宏"""
        try:
            # Tree-sitter检测
            tree_sitter_detector = FunctionMacroDetector(self.content)
            self.tree_sitter_macros = tree_sitter_detector.get_function_macros()
        except Exception as e:
            print(f"Tree-sitter检测失败: {e}")
            self.tree_sitter_macros = []

        try:
            # 正则表达式检测
            regex_detector = RegexFunctionMacroDetector(self.content)
            self.regex_macros = regex_detector.get_function_macros()
        except Exception as e:
            print(f"正则表达式检测失败: {e}")
            self.regex_macros = []

    def _merge_results(self):
        """合并两种检测结果"""
        # 按行号组织tree-sitter结果
        tree_sitter_by_line = self._group_macros_by_line(self.tree_sitter_macros)

        # 按行号组织正则表达式结果
        regex_by_line = self._group_macros_by_line(self.regex_macros)

        # 获取所有涉及的行号
        all_lines = set(tree_sitter_by_line.keys()) | set(regex_by_line.keys())

        # 逐行处理
        for line_num in sorted(all_lines):
            tree_sitter_macros_on_line = tree_sitter_by_line.get(line_num, [])
            regex_macros_on_line = regex_by_line.get(line_num, [])

            merged_macros_on_line = self._merge_macros_on_same_line(
                tree_sitter_macros_on_line,
                regex_macros_on_line
            )

            self.merged_macros.extend(merged_macros_on_line)

        # 按行号排序最终结果
        self.merged_macros.sort(key=lambda x: x.start_line)

    def _group_macros_by_line(self, macros: List[FunctionMacroInfo]) -> Dict[int, List[FunctionMacroInfo]]:
        """按行号分组宏"""
        grouped = {}
        for macro in macros:
            line_num = macro.start_line
            if line_num not in grouped:
                grouped[line_num] = []
            grouped[line_num].append(macro)
        return grouped

    def _merge_macros_on_same_line(self, tree_sitter_macros: List[FunctionMacroInfo],
                                   regex_macros: List[FunctionMacroInfo]) -> List[FunctionMacroInfo]:
        """合并同一行上的宏"""
        result = []

        # 如果只有一种方法有结果，直接使用
        if not tree_sitter_macros:
            return regex_macros
        if not regex_macros:
            return tree_sitter_macros

        # 两种方法都有结果，需要比较和合并
        used_regex_indices = set()

        for ts_macro in tree_sitter_macros:
            merged = False

            for i, regex_macro in enumerate(regex_macros):
                if i in used_regex_indices:
                    continue

                # 检查是否匹配（宏名和参数相同）
                if self._macros_match(ts_macro, regex_macro):
                    # 合并匹配的宏（优先使用tree-sitter结果，但可以补充信息）
                    merged_macro = self._merge_matching_macros(ts_macro, regex_macro)
                    result.append(merged_macro)
                    used_regex_indices.add(i)
                    merged = True
                    break
                elif self._macros_conflict(ts_macro, regex_macro):
                    # 发现冲突，跳过这两个宏
                    used_regex_indices.add(i)
                    merged = True
                    break

            # 如果没有找到匹配或冲突，直接添加tree-sitter结果
            if not merged:
                result.append(ts_macro)

        # 添加未使用的正则表达式结果
        for i, regex_macro in enumerate(regex_macros):
            if i not in used_regex_indices:
                result.append(regex_macro)

        return result

    def _macros_match(self, macro1: FunctionMacroInfo, macro2: FunctionMacroInfo) -> bool:
        """检查两个宏是否匹配"""
        # 宏名必须相同
        if macro1.macro_name != macro2.macro_name:
            return False

        # 参数必须相同
        if len(macro1.macro_arguments) != len(macro2.macro_arguments):
            return False

        # 逐个比较参数（忽略空白差异）
        for arg1, arg2 in zip(macro1.macro_arguments, macro2.macro_arguments):
            if self._normalize_argument(arg1) != self._normalize_argument(arg2):
                return False

        return True

    def _macros_conflict(self, macro1: FunctionMacroInfo, macro2: FunctionMacroInfo) -> bool:
        """检查两个宏是否冲突（宏名相同但参数不同）"""
        # 如果宏名相同但参数不同，认为是冲突
        if macro1.macro_name == macro2.macro_name:
            return not self._macros_match(macro1, macro2)

        return False

    def _normalize_argument(self, arg: str) -> str:
        """标准化参数字符串"""
        import re
        # 移除多余空白并转换为小写进行比较
        return re.sub(r'\s+', ' ', arg.strip().lower())

    def _merge_matching_macros(self, ts_macro: FunctionMacroInfo, regex_macro: FunctionMacroInfo) -> FunctionMacroInfo:
        """合并匹配的宏（优先使用tree-sitter结果）"""
        # 使用tree-sitter的结果作为基础，但可以补充regex的信息
        return FunctionMacroInfo(
            macro_name=ts_macro.macro_name,
            macro_arguments=ts_macro.macro_arguments,
            start_line=ts_macro.start_line,
            end_line=ts_macro.end_line,
            full_text=ts_macro.full_text,
            declaration_text=ts_macro.declaration_text or regex_macro.declaration_text
        )

    def get_function_macros(self, method: DetectionMethod = DetectionMethod.MERGED) -> List[FunctionMacroInfo]:
        """
        获取函数宏列表

        Args:
            method: 检测方法选择

        Returns:
            List[FunctionMacroInfo]: 函数宏列表
        """
        if method == DetectionMethod.TREE_SITTER:
            return self.tree_sitter_macros.copy()
        elif method == DetectionMethod.REGEX:
            return self.regex_macros.copy()
        elif method == DetectionMethod.MERGED:
            return self.merged_macros.copy()
        else:
            raise ValueError(f"不支持的检测方法: {method}")

    def print_comparison(self):
        """打印各种方法的比较结果"""
        print("=== 函数宏检测结果比较 ===")
        print(f"Tree-sitter检测到: {len(self.tree_sitter_macros)} 个宏")
        print(f"正则表达式检测到: {len(self.regex_macros)} 个宏")
        print(f"合并后: {len(self.merged_macros)} 个宏")
        print()

        print("--- Tree-sitter结果 ---")
        self._print_macro_list(self.tree_sitter_macros)

        print("--- 正则表达式结果 ---")
        self._print_macro_list(self.regex_macros)

        print("--- 合并结果 ---")
        self._print_macro_list(self.merged_macros)

    def _print_macro_list(self, macros: List[FunctionMacroInfo]):
        """打印宏列表"""
        if not macros:
            print("  (无)")
            print()
            return

        for i, macro in enumerate(macros, 1):
            print(f"  {i}. {macro.macro_name}({', '.join(macro.macro_arguments)}) - 行{macro.start_line}")
        print()


def detect_function_macros_hybrid(content: str, method: DetectionMethod = DetectionMethod.MERGED) -> List[FunctionMacroInfo]:
    """
    便捷函数：使用混合方法检测函数宏

    Args:
        content: C代码内容
        method: 检测方法选择

    Returns:
        List[FunctionMacroInfo]: 检测到的函数宏列表
    """
    detector = HybridFunctionMacroDetector(content)
    return detector.get_function_macros(method)
