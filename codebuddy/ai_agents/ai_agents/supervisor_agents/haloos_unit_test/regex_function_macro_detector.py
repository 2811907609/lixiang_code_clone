"""
基于正则表达式的函数宏检测器
用于识别函数属性宏并将其转换为FunctionMacroInfo格式
作为tree-sitter方法的补充，特别适用于处理复杂的宏语法
"""

import re
from typing import List, Optional, Tuple
from ai_agents.supervisor_agents.haloos_unit_test.use_treesitter_extract_function_macro import FunctionMacroInfo


class RegexFunctionMacroDetector:
    """基于正则表达式的函数宏检测器"""

    def __init__(self, content: str):
        """
        初始化检测器

        Args:
            content: C代码内容
        """
        self.content = content
        self.lines = content.splitlines()
        self.function_macros: List[FunctionMacroInfo] = []

        # 检测函数宏
        self._detect_function_macros()

    def _detect_function_macros(self):
        """使用正则表达式检测函数宏"""
        # 模式1: 单行宏定义，如 FUNC(void, DCM_CODE) FunctionName(...)
        # 使用 [^)\n]+ 来确保不匹配换行符，保证单行匹配
        pattern = r'(?P<macro_name>FUNC[A-Z0-9_]*)\s*\(\s*(?P<macro_args>[^)\n]+)\s*\)'

        regex = re.compile(pattern)

        for match in regex.finditer(self.content):
            macro_info = self._extract_macro_info_from_match(match)
            if macro_info and self._is_valid_function_macro(macro_info):
                self.function_macros.append(macro_info)

    def _extract_macro_info_from_match(self, match: re.Match) -> Optional[FunctionMacroInfo]:
        """从正则匹配结果中提取宏信息"""
        try:
            # 获取匹配的组
            groups = match.groupdict()

            # 提取宏名
            macro_name = groups.get('macro_name', '').strip()
            if not macro_name:
                return None

            # 提取宏参数
            macro_args_str = groups.get('macro_args', '').strip()
            macro_arguments = self._parse_macro_arguments(macro_args_str)

            # 计算行号
            start_pos = match.start()
            end_pos = match.end()
            start_line, end_line = self._get_line_numbers_from_positions(start_pos, end_pos)

            # 构造完整宏文本
            if macro_arguments:
                macro_args_formatted = ', '.join(macro_arguments)
                full_text = f"{macro_name}({macro_args_formatted})"
            else:
                full_text = f"{macro_name}()"

            # 获取声明文本（整个匹配的文本）
            declaration_text = match.group(0)

            return FunctionMacroInfo(
                macro_name=macro_name,
                macro_arguments=macro_arguments,
                start_line=start_line,
                end_line=end_line,
                full_text=full_text,
                declaration_text=declaration_text
            )

        except Exception:
            return None

    def _parse_macro_arguments(self, args_str: str) -> List[str]:
        """解析宏参数字符串"""
        if not args_str:
            return []

        # 移除多余空白
        args_str = re.sub(r'\s+', ' ', args_str).strip()

        # 简单的逗号分割
        args = [arg.strip() for arg in args_str.split(',')]

        # 过滤空参数
        return [arg for arg in args if arg]

    def _get_line_numbers_from_positions(self, start_pos: int, end_pos: int) -> Tuple[int, int]:
        """从字符位置计算行号"""
        # 计算开始行号
        start_line = self.content[:start_pos].count('\n')

        # 计算结束行号
        end_line = self.content[:end_pos].count('\n')

        return start_line, end_line

    def _is_valid_function_macro(self, macro_info: FunctionMacroInfo) -> bool:
        """验证是否是有效的函数宏"""
        # 检查宏名是否符合命名规则
        if not self._is_function_macro_name(macro_info.macro_name):
            return False

        # 检查是否有参数（函数宏通常至少有返回类型参数）
        if not macro_info.macro_arguments:
            return False

        return True

    def _is_function_macro_name(self, name: str) -> bool:
        """
        判断是否是函数属性宏名

        规则：
        1. 必须以FUNC开始
        2. 全大写字母
        3. 可以包含下划线
        4. 可以包含数字
        """
        if not name:
            return False

        # 必须以FUNC开始
        if not name.startswith('FUNC'):
            return False

        # 检查是否只包含大写字母、下划线和数字
        if not all(c.isupper() or c == '_' or c.isdigit() for c in name):
            return False

        return True

    def get_function_macros(self) -> List[FunctionMacroInfo]:
        """获取检测到的所有函数宏"""
        return self.function_macros.copy()

    def print_summary(self):
        """打印检测结果摘要"""
        print(f"基于正则表达式检测到 {len(self.function_macros)} 个函数宏:")
        print("-" * 50)

        for i, macro in enumerate(self.function_macros, 1):
            print(f"{i}. 宏名: {macro.macro_name}")
            print(f"   参数: {', '.join(macro.macro_arguments)}")
            print(f"   行范围: {macro.start_line}-{macro.end_line}")
            print(f"   完整文本: {macro.full_text}")
            print()


def detect_function_macros_with_regex(content: str) -> List[FunctionMacroInfo]:
    """
    便捷函数：使用正则表达式检测函数宏

    Args:
        content: C代码内容

    Returns:
        List[FunctionMacroInfo]: 检测到的函数宏列表
    """
    detector = RegexFunctionMacroDetector(content)
    return detector.get_function_macros()


if __name__ == "__main__":
    # 测试代码
    test_code = """
#if defined(DEM_USE_INDICATORS)
DEM_STATIC FUNC_P2VAR(const Dem_IndicatorAttributeType *const, AUTOMATIC, DEM_CODE)
    getEventIndicatorAttributeBase(const Dem_EventClassType *eventClass)
{
    const Dem_IndicatorAttributeType *const *indicatorAttributeList = NULL;

    if ((eventClass == NULL) ||
        (eventClass->IndicatorAttributeIndex == DEM_INVALID_U16_REF_INDEX)) {
        return NULL;
    }

    indicatorAttributeList = Dem_GetIndicatorAttributeGroupList();
    if (indicatorAttributeList == NULL) {
        return NULL;
    }

    return &indicatorAttributeList[eventClass->IndicatorAttributeIndex];
}
#endif
"""

    print("测试基于正则表达式的函数宏检测器:")
    print("=" * 60)

    detector = RegexFunctionMacroDetector(test_code)
    detector.print_summary()
