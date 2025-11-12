#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数提取方法比较测试
直接比较 CFunctionLocator 和 TreeSitterFunctionExtractor 两种方法的提取结果
"""


import json
import argparse

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# 导入需要比较的两种函数提取方法
from ai_agents.supervisor_agents.haloos_unit_test.parse_c_file_get_function_info import CFunctionLocator
from ai_agents.supervisor_agents.haloos_unit_test.tree_sitter_function_extractor import TreeSitterFunctionExtractor



@dataclass
class ComparisonResult:
    """比较结果数据类"""
    file_path: str
    cfunctionlocator_count: int
    tree_sitter_count: int
    common_functions: List[str]
    only_in_cfunctionlocator: List[str]
    only_in_tree_sitter: List[str]
    line_range_differences: Dict[str, Dict[str, Any]]  # 函数名 -> {cfunctionlocator: range, tree_sitter: range}
    cfunctionlocator_functions: Dict[str, Dict[str, Any]]  # 原始函数信息
    tree_sitter_functions: Dict[str, Dict[str, Any]]  # 原始函数信息


class FunctionExtractionComparator:
    """函数提取方法比较器"""

    def __init__(self, base_path: str):
        """
        初始化比较器

        Args:
            base_path: 要搜索C文件的基础路径
        """
        self.base_path = base_path
        self.results: List[ComparisonResult] = []

    def find_c_files(self) -> List[str]:
        """
        递归查找指定路径下的所有C文件

        Returns:
            List[str]: C文件路径列表
        """
        c_files = []
        base_path = Path(self.base_path)

        if not base_path.exists():
            raise FileNotFoundError(f"路径不存在: {self.base_path}")

        # 使用 glob 递归查找所有 .c 文件
        for c_file in base_path.rglob("*.c"):
            c_files.append(str(c_file))

        return sorted(c_files)

    def extract_functions_with_cfunctionlocator(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        使用 CFunctionLocator 提取函数信息

        Args:
            file_path: C文件路径

        Returns:
            Dict[str, Dict[str, Any]]: 函数名 -> 函数信息
        """
        functions = {}
        try:
            # 创建 CFunctionLocator 实例
            locator = CFunctionLocator(file_path, use_clang=True, only_use_clang=True)
            functions_info = locator.functions_info

            for func_name, func_info in functions_info.items():
                functions[func_name] = {
                    'start_line': func_info.start_line,
                    'end_line': func_info.end_line,
                    'return_type': func_info.return_type,
                    'parameters': func_info.parameters,
                    'is_func_macro': getattr(func_info, 'is_func_macro', False),
                    'signature': f"{func_info.return_type} {func_name}({func_info.parameters})"
                }
        except Exception as e:
            print(f"CFunctionLocator 提取失败 {file_path}: {e}")

        return functions

    def extract_functions_with_tree_sitter(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        使用 TreeSitterFunctionExtractor 提取函数信息

        Args:
            file_path: C文件路径

        Returns:
            Dict[str, Dict[str, Any]]: 函数名 -> 函数信息
        """
        functions = {}
        try:
            # 使用 TreeSitterFunctionExtractor
            extractor = TreeSitterFunctionExtractor(file_path)
            all_functions = extractor.get_all_functions()

            for func_name, func_info in all_functions.items():
                functions[func_name] = {
                    'start_line': func_info.start_line,
                    'end_line': func_info.end_line,
                    'return_type': '',  # TreeSitter 提取器没有返回类型信息
                    'parameters': '',   # TreeSitter 提取器没有参数信息
                    'is_func_macro': False,  # TreeSitter 提取器没有宏标识
                    'signature': f"{func_name} [{func_info.start_line}-{func_info.end_line}]"
                }
        except Exception as e:
            print(f"TreeSitterFunctionExtractor 提取失败 {file_path}: {e}")

        return functions

    def compare_single_file(self, file_path: str) -> ComparisonResult:
        """
        比较单个文件的两种提取方法结果

        Args:
            file_path: C文件路径

        Returns:
            ComparisonResult: 比较结果
        """
        print(f"正在处理文件: {file_path}")

        # 使用两种方法提取函数
        cfunctionlocator_functions = self.extract_functions_with_cfunctionlocator(file_path)
        tree_sitter_functions = self.extract_functions_with_tree_sitter(file_path)

        # 获取函数名集合
        cfunctionlocator_names = set(cfunctionlocator_functions.keys())
        tree_sitter_names = set(tree_sitter_functions.keys())

        # 计算交集和差集
        common_functions = cfunctionlocator_names & tree_sitter_names
        only_in_cfunctionlocator = cfunctionlocator_names - tree_sitter_names
        only_in_tree_sitter = tree_sitter_names - cfunctionlocator_names

        # 比较共同函数的行号范围
        line_range_differences = {}
        for func_name in common_functions:
            cfunc_info = cfunctionlocator_functions[func_name]
            ts_info = tree_sitter_functions[func_name]

            if (cfunc_info['start_line'] != ts_info['start_line'] or
                cfunc_info['end_line'] != ts_info['end_line']):
                line_range_differences[func_name] = {
                    'cfunctionlocator': {
                        'start_line': cfunc_info['start_line'],
                        'end_line': cfunc_info['end_line'],
                        'signature': cfunc_info['signature']
                    },
                    'tree_sitter': {
                        'start_line': ts_info['start_line'],
                        'end_line': ts_info['end_line'],
                        'signature': ts_info['signature']
                    }
                }

        # 创建比较结果
        result = ComparisonResult(
            file_path=file_path,
            cfunctionlocator_count=len(cfunctionlocator_names),
            tree_sitter_count=len(tree_sitter_names),
            common_functions=sorted(list(common_functions)),
            only_in_cfunctionlocator=sorted(list(only_in_cfunctionlocator)),
            only_in_tree_sitter=sorted(list(only_in_tree_sitter)),
            line_range_differences=line_range_differences,
            cfunctionlocator_functions=cfunctionlocator_functions,
            tree_sitter_functions=tree_sitter_functions
        )

        return result

    def compare_all_files(self) -> List[ComparisonResult]:
        """
        比较所有C文件的提取结果

        Returns:
            List[ComparisonResult]: 所有文件的比较结果
        """
        c_files = self.find_c_files()
        print(f"找到 {len(c_files)} 个C文件")

        results = []
        for file_path in c_files:
            try:
                result = self.compare_single_file(file_path)
                results.append(result)
            except Exception as e:
                print(f"处理文件失败 {file_path}: {e}")
                # 继续处理其他文件

        self.results = results
        return results

    def generate_summary_report(self) -> Dict[str, Any]:
        """
        生成汇总报告

        Returns:
            Dict[str, Any]: 汇总报告
        """
        if not self.results:
            return {"error": "没有比较结果"}

        total_files = len(self.results)
        files_with_differences = 0

        # 统计
        cfunctionlocator_total_functions = 0
        tree_sitter_total_functions = 0
        total_common_functions = 0
        total_only_in_cfunctionlocator = 0
        total_only_in_tree_sitter = 0
        total_line_range_differences = 0

        files_with_function_differences = []
        files_with_line_differences = []

        for result in self.results:
            cfunctionlocator_total_functions += result.cfunctionlocator_count
            tree_sitter_total_functions += result.tree_sitter_count
            total_common_functions += len(result.common_functions)
            total_only_in_cfunctionlocator += len(result.only_in_cfunctionlocator)
            total_only_in_tree_sitter += len(result.only_in_tree_sitter)
            total_line_range_differences += len(result.line_range_differences)

            # 检查是否有差异
            has_function_differences = (len(result.only_in_cfunctionlocator) > 0 or
                                      len(result.only_in_tree_sitter) > 0)
            has_line_differences = len(result.line_range_differences) > 0

            if has_function_differences:
                files_with_differences += 1
                files_with_function_differences.append({
                    'file': result.file_path,
                    'only_in_cfunctionlocator': result.only_in_cfunctionlocator,
                    'only_in_tree_sitter': result.only_in_tree_sitter
                })

            if has_line_differences:
                files_with_line_differences.append({
                    'file': result.file_path,
                    'line_differences': result.line_range_differences
                })

        summary = {
            "total_files_processed": total_files,
            "files_with_function_differences_len": len(files_with_function_differences),
            "files_with_line_differences_len": len(files_with_line_differences),
            "statistics": {
                "cfunctionlocator": {
                    "total_functions": cfunctionlocator_total_functions,
                    "unique_functions": total_only_in_cfunctionlocator
                },
                "tree_sitter": {
                    "total_functions": tree_sitter_total_functions,
                    "unique_functions": total_only_in_tree_sitter
                },
                "common_functions": total_common_functions,
                "line_range_differences": total_line_range_differences
            },
            "files_with_function_differences": files_with_function_differences,
            "files_with_line_differences": files_with_line_differences
        }

        return summary

    def export_to_json(self, output_file: str = "function_extraction_comparison.json"):
        """
        导出比较结果到JSON文件

        Args:
            output_file: 输出文件路径
        """
        if not self.results:
            print("没有比较结果可导出")
            return

        # 转换为可序列化的格式
        results_dict = []
        for result in self.results:
            result_dict = asdict(result)
            results_dict.append(result_dict)

        # 添加汇总报告
        summary = self.generate_summary_report()

        export_data = {
            "summary": summary,
            "detailed_results": results_dict,
            "base_path": self.base_path
        }

        # 导出到JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"比较结果已导出到: {output_file}")

    def print_summary(self):
        """打印汇总信息"""
        summary = self.generate_summary_report()

        print("\n" + "="*80)
        print("函数提取方法比较汇总报告")
        print("="*80)
        print(f"基础路径: {self.base_path}")
        print(f"处理的文件总数: {summary['total_files_processed']}")
        print(f"有函数差异的文件数: {summary['files_with_function_differences']}")
        print(f"有行号差异的文件数: {summary['files_with_line_differences']}")
        print()

        stats = summary['statistics']
        print("CFunctionLocator (方法1):")
        print(f"  总函数数: {stats['cfunctionlocator']['total_functions']}")
        print(f"  独有函数数: {stats['cfunctionlocator']['unique_functions']}")
        print()

        print("TreeSitterFunctionExtractor (方法2):")
        print(f"  总函数数: {stats['tree_sitter']['total_functions']}")
        print(f"  独有函数数: {stats['tree_sitter']['unique_functions']}")
        print()

        print(f"共同函数数: {stats['common_functions']}")
        print(f"行号范围差异数: {stats['line_range_differences']}")

        # 显示详细差异
        if summary['files_with_function_differences']:
            print("\n函数差异详情:")
            print("-" * 40)
            for file_diff in summary['files_with_function_differences']:
                print(f"文件: {file_diff['file']}")
                if file_diff['only_in_cfunctionlocator']:
                    print(f"  仅CFunctionLocator发现: {file_diff['only_in_cfunctionlocator']}")
                if file_diff['only_in_tree_sitter']:
                    print(f"  仅TreeSitter发现: {file_diff['only_in_tree_sitter']}")
                print()

        if summary['files_with_line_differences']:
            print("行号差异详情:")
            print("-" * 40)
            for file_diff in summary['files_with_line_differences']:
                print(f"文件: {file_diff['file']}")
                for func_name, line_diff in file_diff['line_differences'].items():
                    print(f"  函数 {func_name}:")
                    cf_range = line_diff['cfunctionlocator']
                    ts_range = line_diff['tree_sitter']
                    print(f"    CFunctionLocator: {cf_range['start_line']}-{cf_range['end_line']}")
                    print(f"    TreeSitter: {ts_range['start_line']}-{ts_range['end_line']}")
                print()

        print("="*80)


def test_function_extraction_comparison(base_path: str, output_file: str = None):
    """
    测试函数提取方法比较

    Args:
        base_path: 要扫描的基础路径
        output_file: JSON输出文件路径（可选）
    """
    print(f"开始比较函数提取方法，基础路径: {base_path}")

    # 创建比较器
    comparator = FunctionExtractionComparator(base_path)

    # 执行比较
    results = comparator.compare_all_files()

    # 打印汇总信息
    comparator.print_summary()

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="函数提取方法比较测试")
    parser.add_argument('path', help='要扫描的C文件基础路径')
    parser.add_argument('-o', '--output', help='JSON输出文件路径（可选）', default=None)

    args = parser.parse_args()

    test_function_extraction_comparison(args.path, args.output)
