"""
基于 libclang 的 C 语言函数定位器
使用 libclang Python binding 进行准确的C代码解析
支持函数定义、调用和位置信息的完整获取
"""

import os
import signal
import clang.cindex as clang
from clang.cindex import Index, TranslationUnit, Cursor, CursorKind
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from ai_agents.supervisor_agents.haloos_unit_test.macro_extractor import analyze_function_internal_macro_combinations_from_file
from ai_agents.supervisor_agents.haloos_unit_test.haloos_common_utils import change_function_name_by_line,FunctionInfo
# 全局缓存字典，用于存储宏组合分析结果
# 格式：{(文件路径, 文件修改时间): 分析结果}
_macro_combinations_cache = {}

def _get_cache_key(file_path: str) -> Tuple[str, float]:
    """获取缓存键：(文件路径, 文件修改时间)"""
    try:
        mtime = os.path.getmtime(file_path)
        return (os.path.abspath(file_path), mtime)
    except OSError:
        # 如果文件不存在或无法获取修改时间，返回一个唯一的键
        return (os.path.abspath(file_path), -1)

def _clean_expired_cache():
    """清理已过期的缓存项"""
    expired_keys = []
    for (file_path, cached_mtime) in _macro_combinations_cache.keys():
        try:
            current_mtime = os.path.getmtime(file_path)
            if current_mtime != cached_mtime:
                expired_keys.append((file_path, cached_mtime))
        except OSError:
            # 文件不存在，标记为过期
            expired_keys.append((file_path, cached_mtime))

    for key in expired_keys:
        del _macro_combinations_cache[key]

def clear_macro_combinations_cache():
    """清空宏组合缓存"""
    global _macro_combinations_cache
    _macro_combinations_cache.clear()

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Function execution timed out")


@dataclass
class FunctionLocation:
    """函数位置信息"""
    file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __str__(self):
        return f"{self.file_path}:{self.start_line}:{self.start_column}-{self.end_line}:{self.end_column}"

@dataclass
class FunctionCall:
    """函数调用信息"""
    function_name: str
    location: FunctionLocation
    caller_function: str  # 调用者函数名

    def __str__(self):
        return f"{self.function_name} called from {self.caller_function} at {self.location}"


class ClangCFunctionLocator:
    """基于 libclang 的 C 语言函数定位器"""

    def __init__(self, file_path: str, include_paths: List[str] = None,
                 compile_flags: List[str] = None, conditional_macros = None):
        """
        初始化C函数定位器

        Args:
            file_path: C源文件路径
            include_paths: 头文件搜索路径列表
            compile_flags: 编译标志列表
            conditional_macros: 条件编译宏定义，支持以下格式：
                - List[str]: 单一宏组合，如 ["MACRO1=1", "MACRO2=1"]
                - List[List[str]]: 多种宏组合，如 [["MACRO1=1"], ["MACRO2=1"], ["MACRO1=1", "MACRO2=1"]]
        """
        self.file_path = os.path.abspath(file_path)
        self.include_paths = include_paths or []
        self.compile_flags = compile_flags or []

        # 处理conditional_macros参数，支持多种格式
        self.conditional_macros_combinations = self._normalize_conditional_macros(conditional_macros)

        # 验证文件存在
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        # 初始化 clang
        self.index = Index.create()

        # 存储所有组合的解析结果
        self.all_functions: Dict[str, FunctionInfo] = {}  # 合并后的所有函数
        self.all_function_calls: List[FunctionCall] = []  # 合并后的所有函数调用
        self.all_function_definitions: Dict[str, FunctionInfo] = {}  # 合并后的函数定义
        self.all_function_declarations: Dict[str, FunctionInfo] = {}  # 合并后的函数声明

        # 存储每种组合的解析结果
        self.combinations_results: List[Dict] = []

        # 为了向后兼容，保留旧的属性名（指向合并后的结果）
        self.functions = self.all_functions  # 向后兼容
        self.function_calls = self.all_function_calls  # 向后兼容
        self.function_definitions = self.all_function_definitions  # 向后兼容
        self.function_declarations = self.all_function_declarations  # 向后兼容

        # 解析所有宏组合
        self._parse_all_combinations()


    def _normalize_conditional_macros(self, conditional_macros) -> List[List[str]]:
        """
        标准化条件编译宏定义，支持多种格式

        Args:
            conditional_macros: 可以是以下格式之一：
                - None: 返回空列表
                - List[str]: 单一宏组合，转换为 [List[str]]
                - List[List[str]]: 多种宏组合，直接返回

        Returns:
            List[List[str]]: 标准化后的宏组合列表
        """
        if conditional_macros is None:
            return [[]]  # 无宏定义的组合

        # 检查是否为字符串列表（单一组合）
        if all(isinstance(item, str) for item in conditional_macros):
            return [conditional_macros]

        # 检查是否为列表的列表（多种组合）
        if all(isinstance(item, list) for item in conditional_macros):
            return conditional_macros

        # 混合格式，尝试处理
        result = []
        for item in conditional_macros:
            if isinstance(item, str):
                result.append([item])
            elif isinstance(item, list):
                result.append(item)
            else:
                raise ValueError(f"不支持的宏定义格式: {type(item)}")

        return result

    def _parse_all_combinations(self):
        """解析所有宏组合"""
        for i, macro_combination in enumerate(self.conditional_macros_combinations):
            # 解析当前组合
            result = self._parse_single_combination(macro_combination)
            self.combinations_results.append(result)

            # 合并结果到总的结果中
            self._merge_results(result)

    def _parse_single_combination(self, macro_combination: List[str]) -> Dict:
        """解析单个宏组合"""
        # 临时设置当前宏组合
        current_macros = macro_combination

        # 创建临时的翻译单元
        compile_args = self._get_compile_args_for_macros(current_macros)

        try:
            parse_options = (
                TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                TranslationUnit.PARSE_INCOMPLETE
            )

            translation_unit = self.index.parse(
                self.file_path,
                args=compile_args,
                options=parse_options
            )

            if not translation_unit:
                translation_unit = self.index.parse(
                    self.file_path,
                    args=compile_args,
                    options=TranslationUnit.PARSE_INCOMPLETE
                )

            if not translation_unit:
                print(f"警告: 宏组合 {macro_combination} 解析失败")
                return {
                    'macros': macro_combination,
                    'functions': {},
                    'function_calls': [],
                    'function_definitions': {},
                    'function_declarations': {}
                }

            # 存储解析结果
            functions = {}
            function_calls = []
            function_definitions = {}
            function_declarations = {}

            # 遍历AST收集函数信息
            self._traverse_ast_for_combination(
                translation_unit.cursor,
                functions,
                function_calls,
                function_definitions,
                function_declarations
            )

            return {
                'macros': macro_combination,
                'functions': functions,
                'function_calls': function_calls,
                'function_definitions': function_definitions,
                'function_declarations': function_declarations
            }

        except Exception as e:
            print(f"解析宏组合 {macro_combination} 时出错: {e}")
            return {
                'macros': macro_combination,
                'functions': {},
                'function_calls': [],
                'function_definitions': {},
                'function_declarations': {}
            }

    def _get_compile_args_for_macros(self, macros: List[str]) -> List[str]:
        """为特定宏组合获取编译参数"""
        args = []

        # C语言标准和类型
        args.extend(["-std=c99", "-x", "c"])

        # 添加标准C库头文件路径
        standard_include_paths = [
            "/usr/include",
            "/usr/local/include",
            "/usr/include/x86_64-linux-gnu",
            "/usr/lib/gcc/x86_64-linux-gnu/7/include",
            "/usr/lib/gcc/x86_64-linux-gnu/9/include",
            "/usr/lib/gcc/x86_64-linux-gnu/11/include"
        ]

        for include_path in standard_include_paths:
            if os.path.exists(include_path):
                args.extend(["-I", include_path])

        # 添加用户指定的包含路径
        for include_path in self.include_paths:
            args.extend(["-I", include_path])

        # 添加用户指定的编译标志
        args.extend(self.compile_flags)

        # 添加通用标志
        args.extend([
            "-fparse-all-comments",
            "-Wno-pragma-once-outside-header",
            "-D__STDC_VERSION__=199901L",
            "-ferror-limit=0",
            "-fno-spell-checking",
            "-Wno-everything",
            "-fsyntax-only",
            "-Wno-unused-function",
            "-Wno-implicit-function-declaration",
        ])

        # 添加当前宏组合
        for macro in macros:
            if not macro.startswith("-D"):
                macro = f"-D{macro}"
            args.append(macro)

        return args

    def _traverse_ast_for_combination(self, cursor: Cursor, functions: Dict, function_calls: List,
                                    function_definitions: Dict, function_declarations: Dict,
                                    current_function: str = ""):
        """为特定组合遍历AST并收集函数信息"""
        # 只处理当前文件中的节点
        if cursor.location.file and cursor.location.file.name != self.file_path:
            return

        # 处理函数定义和声明
        if cursor.kind == CursorKind.FUNCTION_DECL:
            self._process_function_for_combination(cursor, functions, function_definitions, function_declarations)

        # 处理函数调用
        elif cursor.kind == CursorKind.CALL_EXPR:
            self._process_function_call_for_combination(cursor, current_function, function_calls)

        # 递归处理子节点
        func_name = current_function
        if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
            func_name = cursor.spelling

        for child in cursor.get_children():
            self._traverse_ast_for_combination(child, functions, function_calls,
                                             function_definitions, function_declarations, func_name)

    def _process_function_for_combination(self, cursor: Cursor, functions: Dict,
                                        function_definitions: Dict, function_declarations: Dict):
        """为特定组合处理函数定义或声明"""
        if not cursor.spelling:  # 跳过匿名函数
            return

        location = self._get_location_info(cursor)
        if not location:
            return

        # 检查是否为inline函数
        is_inline = cursor.is_inline_function() if hasattr(cursor, 'is_inline_function') else False
        is_static = cursor.storage_class == clang.StorageClass.STATIC
        is_definition = cursor.is_definition()

        # 对于inline函数的特殊处理
        if is_inline and not is_definition:
            has_body = any(child.kind == clang.CursorKind.COMPOUND_STMT for child in cursor.get_children())
            if has_body:
                is_definition = True

        # 对于static函数的额外检查
        if is_static and not is_definition:
            has_body = any(child.kind == clang.CursorKind.COMPOUND_STMT for child in cursor.get_children())
            if has_body:
                is_definition = True

        # 获取函数信息
        func_info = FunctionInfo(
            name=cursor.spelling,
            start_line=location.start_line,
            end_line=location.end_line,
            return_type=self._get_type_spelling(cursor.result_type),
            parameters=self._get_parameters(cursor),
            is_func_macro=False
        )

        # 保存额外的信息到对象属性中
        func_info.location = location
        func_info.is_definition = is_definition
        func_info.is_static = is_static
        func_info.is_inline = is_inline
        func_info.is_extern = cursor.storage_class == clang.StorageClass.EXTERN

        # 将函数添加到相应的字典中
        functions[func_info.name] = func_info

        if func_info.is_definition:
            function_definitions[func_info.name] = func_info
        else:
            function_declarations[func_info.name] = func_info

    def _process_function_call_for_combination(self, cursor: Cursor, caller_function: str, function_calls: List):
        """为特定组合处理函数调用"""
        # 获取被调用的函数名
        function_name = ""
        if cursor.spelling:
            function_name = cursor.spelling
        elif cursor.referenced:
            function_name = cursor.referenced.spelling
        else:
            # 尝试从子节点获取函数名
            for child in cursor.get_children():
                if child.kind == CursorKind.DECL_REF_EXPR:
                    function_name = child.spelling
                    break

        if not function_name or not caller_function:
            return

        location = self._get_location_info(cursor)
        if not location:
            return

        call_info = FunctionCall(
            function_name=function_name,
            location=location,
            caller_function=caller_function
        )

        function_calls.append(call_info)

    def _merge_results(self, combination_result: Dict):
        """合并单个组合的结果到总结果中"""
        # 合并函数（去重，优先保留定义）
        for func_name, func_info in combination_result['functions'].items():
            if func_name not in self.all_functions:
                # 新函数，直接添加
                self.all_functions[func_name] = func_info
            else:
                # 已存在的函数，检查是否需要更新
                existing_func = self.all_functions[func_name]

                # 如果新函数是定义而现有的是声明，则替换
                if (hasattr(func_info, 'is_definition') and func_info.is_definition and
                    hasattr(existing_func, 'is_definition') and not existing_func.is_definition):
                    self.all_functions[func_name] = func_info

                # 检测是否不同行，如果不同行则添加进入
                line_set = set()
                for line_info in existing_func.other_function_definitions:
                    for line_name, line_func_info in line_info.items():
                        line_set.add(line_name)
                line_name = change_function_name_by_line(func_info)
                if line_name not in line_set:
                    self.all_functions[func_name].other_function_definitions.append({line_name:func_info})

        # 合并函数定义（去重）
        for func_name, func_info in combination_result['function_definitions'].items():
            if func_name not in self.all_function_definitions:
                self.all_function_definitions[func_name] = func_info

        # 合并函数声明（去重，但不覆盖定义）
        for func_name, func_info in combination_result['function_declarations'].items():
            if func_name not in self.all_function_declarations and func_name not in self.all_function_definitions:
                self.all_function_declarations[func_name] = func_info

        # 合并函数调用（去重）
        for call_info in combination_result['function_calls']:
            # 简单的去重策略：基于调用者、被调用者和位置
            call_signature = (call_info.caller_function, call_info.function_name,
                            call_info.location.start_line, call_info.location.start_column)

            # 检查是否已存在相同的调用
            exists = any(
                (existing_call.caller_function, existing_call.function_name,
                 existing_call.location.start_line, existing_call.location.start_column) == call_signature
                for existing_call in self.all_function_calls
            )

            if not exists:
                self.all_function_calls.append(call_info)

    def _get_compile_args(self) -> List[str]:
        """获取C语言编译参数"""
        args = []

        # C语言标准和类型
        args.extend(["-std=c99", "-x", "c"])

        # 添加标准C库头文件路径（解决stdbool.h等标准头文件找不到的问题, 不添加也不影响正常其他解析）
        standard_include_paths = [
            "/usr/include",
            "/usr/local/include",
            "/usr/include/x86_64-linux-gnu",
            "/usr/lib/gcc/x86_64-linux-gnu/7/include",  # GCC内置头文件
            "/usr/lib/gcc/x86_64-linux-gnu/9/include",  # 不同版本的GCC
            "/usr/lib/gcc/x86_64-linux-gnu/11/include"
        ]

        for include_path in standard_include_paths:
            if os.path.exists(include_path):
                args.extend(["-I", include_path])

        # 添加用户指定的包含路径
        for include_path in self.include_paths:
            args.extend(["-I", include_path])

        # 添加用户指定的编译标志
        args.extend(self.compile_flags)

        # 添加一些常用的标志来提高解析的容错性
        args.extend([
            "-fparse-all-comments",  # 解析所有注释
            "-Wno-pragma-once-outside-header",  # 忽略某些警告
            "-D__STDC_VERSION__=199901L",  # 定义C99标准
            "-ferror-limit=0",  # 不限制错误数量
            "-fno-spell-checking",  # 禁用拼写检查
            "-Wno-everything",  # 忽略所有警告
            "-fsyntax-only",  # 只进行语法检查
            "-Wno-unused-function",  # 忽略未使用函数警告
            "-Wno-implicit-function-declaration",  # 忽略隐式函数声明警告
        ])

        # 添加用户指定的条件编译宏定义
        for macro in self.conditional_macros:
            if not macro.startswith("-D"):
                macro = f"-D{macro}"
            args.append(macro)

        return args

    def _parse_file_legacy(self):
        """解析C源文件"""
        compile_args = self._get_compile_args()

        try:
            # 尝试多种解析选项来提高容错性
            # 注意：不能使用PARSE_SKIP_FUNCTION_BODIES，否则无法区分函数定义和声明
            parse_options = (
                TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                TranslationUnit.PARSE_INCOMPLETE  # 允许不完整的解析
            )

            self.translation_unit = self.index.parse(
                self.file_path,
                args=compile_args,
                options=parse_options
            )

            if not self.translation_unit:
                # 如果第一次解析失败，尝试更宽松的选项
                print("第一次解析失败，尝试更宽松的解析选项...")
                self.translation_unit = self.index.parse(
                    self.file_path,
                    args=compile_args,
                    options=TranslationUnit.PARSE_INCOMPLETE
                )

            if not self.translation_unit:
                raise RuntimeError("解析文件失败")

            # 检查诊断信息
            diagnostics = list(self.translation_unit.diagnostics)
            errors = [d for d in diagnostics if d.severity >= clang.Diagnostic.Error]
            warnings = [d for d in diagnostics if d.severity == clang.Diagnostic.Warning]

            if errors:
                print(f"警告: 解析文件时发现 {len(errors)} 个错误:")
                for error in errors[:3]:  # 只显示前3个错误
                    print(f"  {error}")
                print("即使有错误，仍尝试继续解析...")

            if warnings:
                print(f"注意: 发现 {len(warnings)} 个警告")

            # 遍历 AST 收集函数信息
            self._traverse_ast(self.translation_unit.cursor)

            # 如果找到的函数很少，尝试提供建议
            if len(self.functions) < 10:
                print(f"提示: 只找到 {len(self.functions)} 个函数，可能需要:")
                print("  1. 添加正确的头文件搜索路径")
                print("  2. 检查条件编译宏是否正确设置")
                print("  3. 确保所有必要的宏定义都已包含")

        except Exception as e:
            raise RuntimeError(f"解析文件失败: {e}")

    def _traverse_ast(self, cursor: Cursor, current_function: str = ""):
        """递归遍历 AST"""
        # 只处理当前文件中的节点
        if cursor.location.file and cursor.location.file.name != self.file_path:
            return

        # 处理函数定义和声明
        if cursor.kind == CursorKind.FUNCTION_DECL:
            self._process_function(cursor)

        # 处理函数调用
        elif cursor.kind == CursorKind.CALL_EXPR:
            self._process_function_call(cursor, current_function)

        # 递归处理子节点
        func_name = current_function
        if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
            func_name = cursor.spelling

        for child in cursor.get_children():
            self._traverse_ast(child, func_name)

    def _process_function(self, cursor: Cursor):
        """处理函数定义或声明"""
        if not cursor.spelling:  # 跳过匿名函数
            return

        location = self._get_location_info(cursor)
        if not location:
            return

        # 检查是否为inline函数
        is_inline = cursor.is_inline_function() if hasattr(cursor, 'is_inline_function') else False
        is_static = cursor.storage_class == clang.StorageClass.STATIC
        is_definition = cursor.is_definition()

        # 对于inline函数（包括static inline）的特殊处理：
        # libclang有时会错误地将有函数体的inline函数标记为声明
        if is_inline and not is_definition:
            # 检查是否有函数体（复合语句）
            has_body = any(child.kind == clang.CursorKind.COMPOUND_STMT for child in cursor.get_children())
            if has_body:
                is_definition = True

        # 对于static函数的额外检查：static函数如果有函数体也应该是定义
        if is_static and not is_definition:
            # 检查是否有函数体
            has_body = any(child.kind == clang.CursorKind.COMPOUND_STMT for child in cursor.get_children())
            if has_body:
                is_definition = True

        # 获取函数信息
        func_info = FunctionInfo(
            name=cursor.spelling,
            start_line=location.start_line,
            end_line=location.end_line,
            return_type=self._get_type_spelling(cursor.result_type),
            parameters=self._get_parameters(cursor),
            is_func_macro=False  # clang解析的都是标准函数，不是FUNC宏
        )

        # 保存额外的信息到对象属性中
        func_info.location = location
        func_info.is_definition = is_definition
        func_info.is_static = is_static
        func_info.is_inline = is_inline
        func_info.is_extern = cursor.storage_class == clang.StorageClass.EXTERN

        # 将函数添加到相应的字典中
        self.functions[func_info.name] = func_info

        if func_info.is_definition:
            self.function_definitions[func_info.name] = func_info
        else:
            self.function_declarations[func_info.name] = func_info

    def _process_function_call(self, cursor: Cursor, caller_function: str):
        """处理函数调用"""
        # 获取被调用的函数名
        function_name = ""
        if cursor.spelling:
            function_name = cursor.spelling
        elif cursor.referenced:
            function_name = cursor.referenced.spelling
        else:
            # 尝试从子节点获取函数名
            for child in cursor.get_children():
                if child.kind == CursorKind.DECL_REF_EXPR:
                    function_name = child.spelling
                    break

        if not function_name or not caller_function:
            return

        location = self._get_location_info(cursor)
        if not location:
            return

        call_info = FunctionCall(
            function_name=function_name,
            location=location,
            caller_function=caller_function
        )

        self.function_calls.append(call_info)

    def _get_location_info(self, cursor: Cursor) -> Optional[FunctionLocation]:
        """获取位置信息"""
        start_loc = cursor.extent.start
        end_loc = cursor.extent.end

        if not start_loc.file or start_loc.file.name != self.file_path:
            return None

        return FunctionLocation(
            file_path=self.file_path,
            start_line=start_loc.line,
            start_column=start_loc.column,
            end_line=end_loc.line,
            end_column=end_loc.column
        )

    def _get_type_spelling(self, type_obj) -> str:
        """获取类型的字符串表示"""
        if hasattr(type_obj, 'spelling'):
            return type_obj.spelling
        return str(type_obj)

    def _get_parameters(self, cursor: Cursor) -> str:
        """获取函数参数信息"""
        parameters = []

        for arg in cursor.get_arguments():
            if not arg.spelling:  # 跳过匿名参数
                continue

            param_type = arg.type
            type_spelling = self._get_type_spelling(param_type)

            # 构建参数字符串: "type name"
            param_str = f"{type_spelling} {arg.spelling}"
            parameters.append(param_str)

        return ", ".join(parameters)

    # 公共接口方法

    def get_function_info(self, function_name: str) -> Optional[FunctionInfo]:
        """获取函数信息（来自所有宏组合的合并结果）"""
        return self.all_functions.get(function_name)

    def get_function_definition(self, function_name: str) -> Optional[FunctionInfo]:
        """获取函数定义信息（来自所有宏组合的合并结果）"""
        return self.all_function_definitions.get(function_name)

    def get_function_declaration(self, function_name: str) -> Optional[FunctionInfo]:
        """获取函数声明信息（来自所有宏组合的合并结果）"""
        return self.all_function_declarations.get(function_name)

    def get_function_location(self, function_name: str) -> Optional[FunctionLocation]:
        """获取函数位置信息"""
        func_info = self.get_function_info(function_name)
        return getattr(func_info, 'location', None) if func_info else None

    def get_function_line_range(self, function_name: str) -> Optional[Tuple[int, int]]:
        """获取函数行范围（与原始接口兼容）"""
        func_info = self.get_function_info(function_name)
        if func_info:
            return (func_info.start_line, func_info.end_line)
        return None

    def list_all_functions(self) -> List[str]:
        """列出所有函数名（来自所有宏组合的合并结果）"""
        return list(self.all_functions.keys())

    def list_function_definitions(self) -> List[str]:
        """列出所有函数定义（来自所有宏组合的合并结果）"""
        return list(self.all_function_definitions.keys())

    def list_function_declarations(self) -> List[str]:
        """列出所有函数声明（来自所有宏组合的合并结果）"""
        return list(self.all_function_declarations.keys())

    def get_function_calls_in_function(self, function_name: str) -> List[FunctionCall]:
        """获取指定函数内的所有函数调用（来自所有宏组合的合并结果）"""
        return [call for call in self.all_function_calls if call.caller_function == function_name]

    def get_calls_to_function(self, function_name: str) -> List[FunctionCall]:
        """获取对指定函数的所有调用（来自所有宏组合的合并结果）"""
        return [call for call in self.all_function_calls if call.function_name == function_name]

    def get_function_calls_simple(self, function_name: str) -> List[str]:
        """获取函数内调用的函数名列表（简单接口，与原始接口兼容）"""
        calls = self.get_function_calls_in_function(function_name)
        return [call.function_name for call in calls]

    def extract_function_calls(self, function_name: str) -> List[str]:
        """提取函数调用（与原始接口兼容）"""
        return self.get_function_calls_simple(function_name)

    def get_nested_function_calls(self, function_name: str, max_depth: int = 5, visited: Set[str] = None) -> Dict[str, List[str]]:
        """获取嵌套函数调用关系（来自所有宏组合的合并结果）"""
        if visited is None:
            visited = set()

        if function_name in visited or max_depth <= 0:
            return {}

        visited.add(function_name)
        result = {}

        # 获取直接调用的函数
        direct_calls = self.get_function_calls_simple(function_name)
        if direct_calls:
            result[function_name] = direct_calls

            # 递归获取每个被调用函数的调用关系
            for called_func in direct_calls:
                if called_func in self.all_functions:  # 只处理本文件中定义的函数
                    nested = self.get_nested_function_calls(called_func, max_depth - 1, visited.copy())
                    result.update(nested)

        return result


    def get_function_body_content(self, function_name: str) -> Optional[str]:
        """获取函数体内容"""
        func_info = self.get_function_definition(function_name)
        if not func_info:
            return None

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            start_line = func_info.start_line - 1  # 转换为0-based
            end_line = func_info.end_line - 1

            if start_line < 0 or end_line >= len(lines):
                return None

            return ''.join(lines[start_line:end_line + 1])

        except Exception as e:
            print(f"读取函数体失败: {e}")
            return None


# 兼容性函数，保持与原始接口一致
def get_function_line_range(file_path: str, function_name: str) -> Optional[Tuple[int, int]]:
    """获取函数行范围（兼容接口）"""
    try:
        locator = ClangCFunctionLocator(file_path)
        return locator.get_function_line_range(function_name)
    except Exception as e:
        print(f"获取函数行范围失败: {e}")
        return None


def get_function_calls_simple(file_path: str, function_name: str) -> List[str]:
    """获取函数调用列表（兼容接口）"""
    try:
        locator = ClangCFunctionLocator(file_path)
        return locator.get_function_calls_simple(function_name)
    except Exception as e:
        print(f"获取函数调用失败: {e}")
        return []


def get_function_calls_nested(file_path: str, function_name: str, max_depth: int = 5) -> Dict[str, List[str]]:
    """获取嵌套函数调用（兼容接口）"""
    try:
        locator = ClangCFunctionLocator(file_path)
        return locator.get_nested_function_calls(function_name, max_depth)
    except Exception as e:
        print(f"获取嵌套函数调用失败: {e}")
        return {}



def get_c_function_definition_info_by_clang(repo_path, c_file_name, is_print_clang_flag=False,timeout_seconds=30):

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)

    try:
        # 设置超时
        signal.alarm(timeout_seconds)

        if is_print_clang_flag:
            print("**use get function by clang**")
        include_path = os.path.join(repo_path,'test/support')
        c_file_path = os.path.join(repo_path,'src',c_file_name)

        # 首先清理过期的缓存
        _clean_expired_cache()

        # 检查缓存
        cache_key = _get_cache_key(c_file_path)
        if cache_key in _macro_combinations_cache:
            if is_print_clang_flag:
                print(f"✓ 使用缓存的宏组合分析结果：{c_file_path}")
                print(f"  缓存键: {cache_key}")
                print(f"  当前缓存大小: {len(_macro_combinations_cache)}")
            conditional_macros = _macro_combinations_cache[cache_key]
        else:
            # 缓存中没有，执行耗时的分析
            if is_print_clang_flag:
                print(f"⚠ 执行宏组合分析：{c_file_path}")
                print(f"  缓存键: {cache_key}")
                print(f"  当前缓存大小: {len(_macro_combinations_cache)}")
            conditional_macros = analyze_function_internal_macro_combinations_from_file(c_file_path)
            # 将结果保存到缓存
            _macro_combinations_cache[cache_key] = conditional_macros
            if is_print_clang_flag:
                print(f"✓ 已将结果保存到缓存，新缓存大小: {len(_macro_combinations_cache)}")

        include_paths = [include_path]
        locator = ClangCFunctionLocator(
            c_file_path,
            include_paths=include_paths,
            conditional_macros=conditional_macros
        )

        # 取消超时
        signal.alarm(0)

        return locator.all_function_definitions

    except TimeoutError:
        # print(f"分析文件 {c_file_path} 超时（{timeout_seconds}秒），跳过处理")
        return None

    except Exception:
        signal.alarm(0)  # 确保取消超时
        # print(f"分析文件时出错: {e}")
        return None
    finally:
        # 恢复原来的信号处理器
        signal.signal(signal.SIGALRM, old_handler)
