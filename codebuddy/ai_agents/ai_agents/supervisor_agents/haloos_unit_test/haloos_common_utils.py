
import os
import time
import re
import tree_sitter_c as tsc
from typing import Dict, List
from dataclasses import dataclass,field
from pathlib import Path
from tree_sitter import Language, Parser
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config

# 性能监控配置
ENABLE_PERFORMANCE_TIMING = haloos_global_env_config.ENABLE_PERFORMANCE_TIMING.lower() == 'true'


# 全局解析器实例，避免重复创建
_global_parser = None
_global_c_language = None

def get_c_parser():
    """获取全局C解析器实例，避免重复创建"""
    global _global_parser, _global_c_language
    if _global_parser is None:
        _global_c_language = Language(tsc.language())
        _global_parser = Parser(_global_c_language)
    return _global_parser, _global_c_language


def log_timing(func_name: str, duration: float, details: str = ""):
    """记录函数执行时间"""
    if ENABLE_PERFORMANCE_TIMING:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {func_name}: {duration:.4f}s {details}"
        print(log_msg)

def timing_decorator(func_name: str = None):
    """计时装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if ENABLE_PERFORMANCE_TIMING:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                name = func_name or func.__name__
                log_timing(name, duration)
                return result
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def count_files_pathlib(folder_path):
    try:
        folder = Path(folder_path)
        if not folder.exists():
            print(f"文件夹 '{folder_path}' 不存在")
            return 0

        # 只统计文件
        files = [f for f in folder.iterdir() if f.is_file()]
        return len(files)
    except PermissionError:
        print(f"没有权限访问文件夹 '{folder_path}'")
        return 0

def get_top3_largest_files(path):
    """获取指定路径下最大的前三个文件"""
    try:
        files_info = []

        # 遍历目录中的所有文件

        for filepath in list_all_files_pathlib(path):
            # 只处理文件，跳过目录
            if os.path.isfile(filepath) and filepath.endswith('.h'):
                file_size = os.path.getsize(filepath)
                files_info.append((filepath, file_size))

        # 按文件大小降序排序，取前3个
        top3_files = sorted(files_info, key=lambda x: x[1], reverse=True)[:3]

        filenames = [get_relative_path(filepath,path) for filepath, size in top3_files]

        return filenames

    except Exception as e:
        print(f"错误: {e}")
        return []

# 改为tree-sitter形式

def is_valid_c_identifier(name: str) -> bool:
    """
    检查字符串是否是有效的C标识符

    C标识符规则：
    1. 必须以字母(a-z, A-Z)或下划线(_)开头
    2. 后续字符可以是字母、数字(0-9)或下划线
    3. 不能为空

    Args:
        name: 要检查的字符串

    Returns:
        bool: 如果是有效的C标识符返回True，否则返回False
    """
    import re
    if not name:
        return False
    # C标识符的正则表达式：以字母或下划线开头，后续可以是字母、数字或下划线
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, name))
def remove_comments_with_mapping(c_code):
    """
    高级版本：更精确地处理注释移除
    """
    if not c_code:
        return "", {}

    # 初始化解析器
    # 获取tree-sitter解析器
    parser, c_language = get_c_parser()
    # 解析代码
    tree = parser.parse(bytes(c_code, "utf8"))

    lines = c_code.split('\n')
    result_lines = lines.copy()
    line_mapping = {}

    # 收集所有注释的位置信息
    comments_by_line = {}

    def byte_offset_to_char_offset(text, byte_offset):
        """将字节偏移转换为字符偏移"""
        return len(text.encode('utf-8')[:byte_offset].decode('utf-8'))

    def collect_comments(node):
        if node.type == 'comment':
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            start_col_byte = node.start_point[1]
            end_col_byte = node.end_point[1]

            # 获取开始行和结束行的文本
            start_line_text = lines[start_line] if start_line < len(lines) else ""
            end_line_text = lines[end_line] if end_line < len(lines) else ""

            # 将字节位置转换为字符位置
            start_col = byte_offset_to_char_offset(start_line_text, start_col_byte)
            end_col = byte_offset_to_char_offset(end_line_text, end_col_byte)

            if start_line not in comments_by_line:
                comments_by_line[start_line] = []

            comments_by_line[start_line].append({
                'start_line': start_line,
                'end_line': end_line,
                'start_col': start_col,
                'end_col': end_col,
                'text': node.text.decode('utf-8')
            })
        elif node.type == 'preproc_arg':
            # 特殊处理预处理器参数中的注释
            # #define 的参数可能包含注释，但tree-sitter不会将其识别为独立的注释节点
            arg_text = node.text.decode('utf-8')
            line_no = node.start_point[0]
            line_text = lines[line_no] if line_no < len(lines) else ""

            # 检查单行注释 //，但要避免字符串内的注释符号
            if '//' in arg_text:
                comment_start_in_arg = -1
                in_string = False
                string_char = None

                # 逐字符检查，跳过字符串内的内容
                for i in range(len(arg_text) - 1):
                    char = arg_text[i]
                    next_char = arg_text[i + 1]

                    # 处理字符串开始/结束
                    if not in_string and (char == '"' or char == "'"):
                        in_string = True
                        string_char = char
                    elif in_string and char == string_char:
                        # 检查是否是转义字符
                        escape_count = 0
                        j = i - 1
                        while j >= 0 and arg_text[j] == '\\':
                            escape_count += 1
                            j -= 1
                        if escape_count % 2 == 0:  # 偶数个反斜杠，字符串结束
                            in_string = False
                            string_char = None

                    # 在字符串外寻找注释
                    if not in_string and char == '/' and next_char == '/':
                        comment_start_in_arg = i
                        break

                if comment_start_in_arg != -1:
                    # 计算注释在整行中的位置
                    arg_start_byte = node.start_point[1]
                    arg_start_char = byte_offset_to_char_offset(line_text, arg_start_byte)

                    # 找到注释在参数中的字符位置
                    arg_prefix = arg_text[:comment_start_in_arg]
                    comment_start_char = arg_start_char + len(arg_prefix.encode('utf-8').decode('utf-8'))
                    comment_end_char = len(line_text)

                    if line_no not in comments_by_line:
                        comments_by_line[line_no] = []

                    comments_by_line[line_no].append({
                        'start_line': line_no,
                        'end_line': line_no,
                        'start_col': comment_start_char,
                        'end_col': comment_end_char,
                        'text': arg_text[comment_start_in_arg:]
                    })

            # 检查多行注释 /* */，但要避免字符串内的注释符号
            elif '/*' in arg_text and '*/' in arg_text:
                comment_start_in_arg = -1
                comment_end_in_arg = -1
                in_string = False
                string_char = None

                # 逐字符检查，跳过字符串内的内容
                for i in range(len(arg_text) - 1):
                    char = arg_text[i]
                    next_char = arg_text[i + 1]

                    # 处理字符串开始/结束
                    if not in_string and (char == '"' or char == "'"):
                        in_string = True
                        string_char = char
                    elif in_string and char == string_char:
                        # 检查是否是转义字符
                        escape_count = 0
                        j = i - 1
                        while j >= 0 and arg_text[j] == '\\':
                            escape_count += 1
                            j -= 1
                        if escape_count % 2 == 0:  # 偶数个反斜杠，字符串结束
                            in_string = False
                            string_char = None

                    # 在字符串外寻找注释开始
                    if not in_string and char == '/' and next_char == '*':
                        comment_start_in_arg = i
                        # 继续寻找注释结束
                        for j in range(i + 2, len(arg_text) - 1):
                            j_char = arg_text[j]
                            j_next_char = arg_text[j + 1]
                            if j_char == '*' and j_next_char == '/':
                                comment_end_in_arg = j + 1  # 包含 */
                                break
                        break

                if comment_start_in_arg != -1 and comment_end_in_arg != -1:
                    # 计算注释在整行中的位置
                    arg_start_byte = node.start_point[1]
                    arg_start_char = byte_offset_to_char_offset(line_text, arg_start_byte)

                    # 找到注释在参数中的字符位置
                    arg_prefix = arg_text[:comment_start_in_arg]
                    comment_start_char = arg_start_char + len(arg_prefix.encode('utf-8').decode('utf-8'))

                    comment_part = arg_text[:comment_end_in_arg + 1]  # 包含 */
                    comment_end_char = arg_start_char + len(comment_part.encode('utf-8').decode('utf-8'))

                    if line_no not in comments_by_line:
                        comments_by_line[line_no] = []

                    comments_by_line[line_no].append({
                        'start_line': line_no,
                        'end_line': line_no,
                        'start_col': comment_start_char,
                        'end_col': comment_end_char,
                        'text': arg_text[comment_start_in_arg:comment_end_in_arg + 1]
                    })

        for child in node.children:
            collect_comments(child)

    collect_comments(tree.root_node)

    # 手动检测未闭合的多行注释（tree-sitter可能无法识别）
    def detect_unclosed_multiline_comments():
        in_comment = False
        comment_start_line = -1
        comment_start_col = -1

        for line_idx, line in enumerate(lines):
            i = 0
            while i < len(line):
                # 跳过字符串内容
                if not in_comment and line[i] in ['"', "'"]:
                    quote = line[i]
                    i += 1
                    while i < len(line) and line[i] != quote:
                        if line[i] == '\\' and i + 1 < len(line):
                            i += 2
                        else:
                            i += 1
                    if i < len(line):
                        i += 1
                    continue

                # 检查多行注释开始
                if not in_comment and i < len(line) - 1 and line[i:i+2] == '/*':
                    in_comment = True
                    comment_start_line = line_idx
                    comment_start_col = i
                    i += 2
                    continue

                # 检查多行注释结束
                if in_comment and i < len(line) - 1 and line[i:i+2] == '*/':
                    in_comment = False
                    i += 2
                    continue

                i += 1

        # 如果仍在注释中，说明有未闭合的多行注释
        if in_comment:
            if comment_start_line not in comments_by_line:
                comments_by_line[comment_start_line] = []

            # 添加从注释开始到文件结束的虚拟注释
            comments_by_line[comment_start_line].append({
                'start_line': comment_start_line,
                'end_line': len(lines) - 1,
                'start_col': comment_start_col,
                'end_col': len(lines[-1]) if lines else 0,
                'text': '/* unclosed comment',
                'unclosed': True
            })

    detect_unclosed_multiline_comments()

    # 首先处理所有多行注释
    all_comments = []
    for line_idx, line_comments in comments_by_line.items():
        all_comments.extend(line_comments)

    # 先处理多行注释（按开始位置排序，从后往前处理）
    multiline_comments = [c for c in all_comments if c['start_line'] != c['end_line']]
    multiline_comments.sort(key=lambda x: (x['start_line'], x['start_col']), reverse=True)

    for comment in multiline_comments:
        # 处理开始行
        start_line_idx = comment['start_line']
        if start_line_idx < len(result_lines):
            original_line = result_lines[start_line_idx]
            # 保留注释前的内容
            before_comment = original_line[:comment['start_col']]
            # 如果注释前只有空白字符，则变成完全空行
            if before_comment.strip() == "":
                result_lines[start_line_idx] = ""
            else:
                result_lines[start_line_idx] = before_comment

        # 处理中间行 - 变成空行
        for i in range(comment['start_line'] + 1, comment['end_line']):
            if i < len(result_lines):
                result_lines[i] = ""

        # 处理结束行
        end_line_idx = comment['end_line']
        if end_line_idx < len(result_lines):
            original_line = result_lines[end_line_idx]
            # 对于未闭合的注释，需要特殊处理
            if comment.get('unclosed', False):
                # 未闭合的多行注释，将结束行也变成空行（整个内容都是注释）
                result_lines[end_line_idx] = ""
            else:
                # 正常的多行注释，保留注释后的内容
                result_lines[end_line_idx] = original_line[comment['end_col']:]

    # 然后处理每一行的单行注释
    for line_idx in range(len(lines)):
        if line_idx in comments_by_line:
            line = result_lines[line_idx]  # 使用已经处理过多行注释的行
            new_line = line

            # 只处理单行注释
            single_line_comments = [c for c in comments_by_line[line_idx]
                                  if c['start_line'] == c['end_line']]

            # 按列位置从后往前处理注释（避免位置偏移）
            single_line_comments.sort(key=lambda x: x['start_col'], reverse=True)

            for comment in single_line_comments:
                # 对于被多行注释影响的行，需要重新在原始行中查找注释位置
                if line_idx in [mc['end_line'] for mc in multiline_comments]:
                    # 这一行是某个多行注释的结束行
                    # 在原始行中找到注释，然后在修改后的行中找到对应位置
                    original_line = lines[line_idx]
                    comment_text = comment['text']

                    # 在当前行中查找注释文本
                    comment_pos = new_line.find(comment_text)
                    if comment_pos != -1:
                        # 找到了，直接删除
                        new_line = new_line[:comment_pos] + new_line[comment_pos + len(comment_text):]
                    else:
                        # 没找到，可能注释在多行注释范围内已经被删除了
                        pass
                else:
                    # 正常处理单行注释
                    if comment['start_col'] < len(new_line) and comment['end_col'] <= len(new_line):
                        before = new_line[:comment['start_col']]
                        after = new_line[comment['end_col']:]
                        new_line = before + after

            result_lines[line_idx] = new_line

    # 创建行号映射
    for i in range(len(lines)):
        line_mapping[i + 1] = i + 1

    return '\n'.join(result_lines), line_mapping

def is_2d_list(obj):
    """验证是否为非空二维列表"""
    if not isinstance(obj, list) or len(obj) == 0:
        return False

    return all(isinstance(item, list) for item in obj)


def is_conventional_macro_name(name):
    """
    判断是否符合C语言宏的约定规范

    约定规则：
    1. 全大写字母
    2. 使用下划线分隔单词
    3. 不以数字开头
    4. 避免双下划线开头（编译器保留）
    """
    if not name or not isinstance(name, str):
        return False

    # 避免双下划线开头（编译器保留）
    if name.startswith('__'):
        return True

    # 避免连续多个下划线
    if '__' in name:
        return True

    # 不能以下划线结尾
    if name.endswith('_'):
        return True

    # 检查是否全大写 + 下划线 + 数字
    if not re.match(r'^[A-Z_][A-Z0-9_]*$', name):
        return False



    return True

def list_all_files_pathlib(directory):
    """使用pathlib遍历所有文件"""
    path = Path(directory)

    if not path.exists():
        print(f"目录 {directory} 不存在")
        return []

    # 递归获取所有文件
    all_files = [str(file) for file in path.rglob('*') if file.is_file()]
    return all_files


def list_files_in_directory_without_sub_dir(directory_path):
    """列举指定路径下的所有文件（不包括子文件夹）"""
    files = []
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        if os.path.isfile(item_path):
            files.append(item)
    return files


def get_relative_path(absolute_path, base_path):
    """计算相对路径"""
    abs_path = Path(absolute_path)
    base = Path(base_path)

    try:
        relative_path = abs_path.relative_to(base)
        return str(relative_path)
    except ValueError as e:
        print(f"无法计算相对路径: {e}")
        return None

def is_only_uppercase_letters_with_underscore(text):
    return bool(re.match(r'^[A-Z_0-9]+$', text))



def read_file_content_get_tree_node(filename):

    if not os.path.exists(filename):
        return ''

    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 使用tree-sitter解析C代码
    parser,C_LANGUAGE = get_c_parser()
    tree = parser.parse(content.encode('utf-8'))

    return tree

class CMockFunctionParser:
    """解析和识别CMock生成的函数"""

    # CMock函数后缀模式
    CMOCK_PATTERNS = {
        # 基本Expect模式
        r'_Expect$': 'expect',
        r'_ExpectAndReturn$': 'expect_return',
        r'_ExpectWithArray$': 'expect_array',
        r'_ExpectAnyArgs$': 'expect_any_args',

        # Ignore模式
        r'_Ignore$': 'ignore',
        r'_IgnoreAndReturn$': 'ignore_return',
        r'_IgnoreArg_(\w+)$': 'ignore_arg',

        # Return模式
        r'_ReturnThruPtr_(\w+)$': 'return_thru_ptr',
        r'_ReturnArrayThruPtr_(\w+)$': 'return_array_thru_ptr',
        r'_ReturnMemThruPtr_(\w+)$': 'return_mem_thru_ptr',

        # Stub模式
        r'_StubWithCallback$': 'stub_callback',

        # 其他
        r'_CallInstance$': 'call_instance',
        r'_CallOriginal$': 'call_original',
    }

    def __init__(self):
        # 编译所有正则表达式
        self.compiled_patterns = {
            pattern: re.compile(pattern)
            for pattern in self.CMOCK_PATTERNS.keys()
        }

    def is_cmock_function(self, function_name: str) -> bool:
        """判断是否是CMock生成的函数"""
        for pattern in self.compiled_patterns.values():
            if pattern.search(function_name):
                return True
        return False

    def parse_cmock_function(self, function_name: str) -> Dict[str, str]:
        """解析CMock函数，提取原始函数名和类型"""
        for pattern_str, pattern in self.compiled_patterns.items():
            match = pattern.search(function_name)
            if match:
                # 获取CMock类型
                # cmock_type = self.CMOCK_PATTERNS[pattern_str]

                # 提取原始函数名
                original_name = pattern.sub('', function_name)

                return original_name

        return None

def change_function_name_by_line(function_info):
    return f"{function_info.name}::{function_info.start_line}-{function_info.end_line}"



@dataclass
class FunctionInfo:
    """函数信息数据类"""
    name: str
    start_line: int
    end_line: int
    return_type: str
    parameters: str
    is_func_macro: bool = False
    other_function_definitions: List[dict] = field(default_factory=list)
    def __str__(self):
        # return f"{self.name}:{self.start_line},{self.end_line}"
        return f"{self.name}"
