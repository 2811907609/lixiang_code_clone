"""
C文件宏指令去除工具

用于去除C代码中的预处理器宏指令，如 #if, #endif, #else, #elif, #error 等，
并将这些行替换为空行以保持代码行数不变。
"""

import re


def remove_c_macro_directives(code: str) -> str:
    """
    去除C代码中的宏指令行，将其替换为空行

    Args:
        code (str): 输入的C代码字符串

    Returns:
        str: 去除宏指令后的代码字符串

    Examples:
        >>> code = '''#if (Dem_GetSizeOfDTCStaChgCbkList() > 0)
        ... void some_function() {
        ...     // 函数内容
        ... }
        ... #endif
        ... #error "Dem: Unknown aging counter clear behavior"'''
        >>> result = remove_c_macro_directives(code)
        >>> print(result)

        void some_function() {
            // 函数内容
        }

    """
    if not code:
        return code

    lines = code.split('\n')
    processed_lines = []

    # 匹配各种宏指令的正则表达式
    macro_patterns = [
        r'^\s*#\s*if\b',      # #if
        r'^\s*#\s*ifdef\b',   # #ifdef
        r'^\s*#\s*ifndef\b',  # #ifndef
        r'^\s*#\s*elif\b',    # #elif
        r'^\s*#\s*else\b',    # #else
        r'^\s*#\s*endif\b',   # #endif
        r'^\s*#\s*error\b',   # #error
        r'^\s*#\s*warning\b', # #warning
        r'^\s*#\s*pragma\b',  # #pragma
    ]

    # 编译所有模式为一个大的正则表达式
    combined_pattern = '|'.join(f'({pattern})' for pattern in macro_patterns)
    macro_regex = re.compile(combined_pattern)

    for line in lines:
        # 检查当前行是否匹配任何宏指令模式
        if macro_regex.match(line):
            # 将宏指令行替换为空行
            processed_lines.append('')
        else:
            # 保留非宏指令行
            processed_lines.append(line)

    return '\n'.join(processed_lines)
