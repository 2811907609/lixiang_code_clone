#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Union
import os


class CoverageParser:
    """Ceedling覆盖率HTML报告解析器"""

    def __init__(self):
        self.soup = None
        self.result = {}

    def parse_from_file(self, file_path: str, enhanced: bool = False) -> Dict[str, Any]:
        """
        从HTML文件解析覆盖率信息

        Args:
            file_path (str): HTML文件路径
            enhanced (bool): 是否使用增强模式解析

        Returns:
            Dict: 解析结果

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self.parse_from_string(html_content, enhanced)
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    html_content = f.read()
                return self.parse_from_string(html_content, enhanced)
            except UnicodeDecodeError:
                raise ValueError(f"无法解码文件: {file_path}")

    def parse_from_string(self, html_content: str, enhanced: bool = False) -> Dict[str, Any]:
        """
        从HTML字符串解析覆盖率信息

        Args:
            html_content (str): HTML内容
            enhanced (bool): 是否使用增强模式解析

        Returns:
            Dict: 解析结果
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')

        if enhanced:
            return self._enhanced_parse()
        else:
            return self._basic_parse()

    def _basic_parse(self) -> Dict[str, Any]:
        """基本解析模式"""
        result = {
            "summary": {},
            "functions": [],
            "files": []
        }

        # 解析总体覆盖率
        result["summary"] = self._parse_summary()

        # 解析函数覆盖率
        result["functions"] = self._parse_functions()

        # 解析文件名列表
        result["files"] = self._extract_file_list()

        print("result",result)

        return result

    def _enhanced_parse(self) -> Dict[str, Any]:
        """增强解析模式"""
        result = {
            "metadata": {},
            "summary": {},
            "functions": [],
            "function_statistics": {}
        }

        # 解析元数据
        result["metadata"] = self._parse_metadata()

        # 解析总体覆盖率（增强版）
        result["summary"] = self._parse_summary_enhanced()

        # 解析函数覆盖率（增强版）
        result["functions"] = self._parse_functions_enhanced()

        # 计算统计信息
        result["function_statistics"] = self._calculate_function_statistics(result["functions"])

        return result

    def _parse_metadata(self) -> Dict[str, str]:
        """解析元数据信息"""
        metadata = {}
        legend_table = self.soup.find('table', class_='legend')

        if legend_table:
            rows = legend_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().rstrip(':').lower()
                    value = cells[1].get_text().strip()
                    metadata[key] = value

        return metadata

    def _parse_summary(self) -> Dict[str, Dict[str, Union[int, str]]]:
        """解析总体覆盖率信息 - 兼容新旧格式"""
        summary = {}
        coverage_table = self.soup.find('table', class_='coverage')

        if coverage_table:
            rows = coverage_table.find_all('tr')[1:]  # 跳过表头

            # 检测格式类型
            is_new_format = self._detect_summary_format(coverage_table)

            for row in rows:
                cells = row.find_all(['th', 'td'])

                if is_new_format and len(cells) >= 5:
                    # 新格式 (GCovr): Coverage, Exec, Excl, Total
                    metric_name = cells[0].get_text().strip().rstrip(':').lower()
                    coverage_percent = cells[1].get_text().strip()
                    executed = self._safe_int_conversion(cells[2].get_text().strip())
                    excluded = self._safe_int_conversion(cells[3].get_text().strip())
                    total = self._safe_int_conversion(cells[4].get_text().strip())

                    summary[metric_name] = {
                        "executed": executed,
                        "excluded": excluded,
                        "total": total,
                        "coverage": coverage_percent
                    }

                elif not is_new_format and len(cells) >= 4:
                    # 旧格式 (Ceedling): Executed, Total, Coverage
                    metric_name = cells[0].get_text().strip().rstrip(':').lower()
                    executed = self._safe_int_conversion(cells[1].get_text().strip())
                    total = self._safe_int_conversion(cells[2].get_text().strip())
                    coverage_percent = cells[3].get_text().strip()

                    summary[metric_name] = {
                        "executed": executed,
                        "total": total,
                        "coverage": coverage_percent
                    }

        return summary

    def _safe_int_conversion(self, value_str: str) -> int:
        """
        安全地将字符串转换为整数
        处理百分比和其他特殊格式

        Args:
            value_str: 要转换的字符串

        Returns:
            int: 转换后的整数，转换失败返回0
        """
        try:
            # 移除百分号和其他非数字字符，只保留数字和小数点
            cleaned_str = re.sub(r'[^\d.]', '', value_str.strip())
            if not cleaned_str:
                return 0

            # 如果包含小数点，转换为浮点数后再转为整数
            if '.' in cleaned_str:
                return int(float(cleaned_str))
            else:
                return int(cleaned_str)
        except (ValueError, TypeError):
            return 0

    def _detect_summary_format(self, coverage_table) -> bool:
        """
        检测summary表格格式

        Returns:
            bool: True表示新格式(GCovr), False表示老格式(Ceedling)
        """
        # 检查表头来判断格式
        header_row = coverage_table.find('tr')
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
            header_text = ' '.join([cell.get_text().strip() for cell in header_cells])

            # 新格式包含 "Excl" 列
            if "Excl" in header_text:
                return True

        return False

    def _parse_summary_enhanced(self) -> Dict[str, Dict[str, Union[int, float, str]]]:
        """解析总体覆盖率信息（增强版）- 兼容新旧格式"""
        summary = {}
        coverage_table = self.soup.find('table', class_='coverage')

        if coverage_table:
            rows = coverage_table.find_all('tr')[1:]

            # 检测格式类型
            is_new_format = self._detect_summary_format(coverage_table)

            for row in rows:
                cells = row.find_all(['th', 'td'])

                if is_new_format and len(cells) >= 5:
                    # 新格式 (GCovr): Coverage, Exec, Excl, Total
                    metric_name = cells[0].get_text().strip().rstrip(':').lower()
                    coverage_text = cells[1].get_text().strip()
                    coverage_percent = self._parse_coverage_percentage(coverage_text)
                    executed = self._safe_int_conversion(cells[2].get_text().strip())
                    excluded = self._safe_int_conversion(cells[3].get_text().strip())
                    total = self._safe_int_conversion(cells[4].get_text().strip())

                    summary[metric_name] = {
                        "executed": executed,
                        "excluded": excluded,
                        "total": total,
                        "coverage_percent": coverage_percent,
                        "coverage_text": coverage_text
                    }

                elif not is_new_format and len(cells) >= 4:
                    # 旧格式 (Ceedling): Executed, Total, Coverage
                    metric_name = cells[0].get_text().strip().rstrip(':').lower()
                    executed = self._safe_int_conversion(cells[1].get_text().strip())
                    total = self._safe_int_conversion(cells[2].get_text().strip())
                    coverage_text = cells[3].get_text().strip()
                    coverage_percent = self._parse_coverage_percentage(coverage_text)

                    summary[metric_name] = {
                        "executed": executed,
                        "total": total,
                        "coverage_percent": coverage_percent,
                        "coverage_text": coverage_text
                    }

        return summary

    def _parse_functions(self) -> List[Dict[str, Union[str, int]]]:
        """解析函数覆盖率信息"""
        functions = []
        functions_table = self.soup.find('table', class_='listOfFunctions')

        if functions_table:
            rows = functions_table.find_all('tr')[1:]  # 跳过表头

            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    function_info = self._extract_function_info(cells)
                    if function_info:
                        functions.append(function_info)

        return functions

    def _parse_functions_enhanced(self) -> List[Dict[str, Union[str, int, float, bool]]]:
        """解析函数覆盖率信息（增强版）"""
        functions = []
        functions_table = self.soup.find('table', class_='listOfFunctions')

        if functions_table:
            rows = functions_table.find_all('tr')[1:]

            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    function_info = self._extract_function_info_enhanced(cells)
                    if function_info:
                        functions.append(function_info)

        return functions

    def _extract_function_info(self, cells: List) -> Optional[Dict[str, Union[str, int]]]:
        """提取基本函数信息"""
        function_cell = cells[0]
        function_link = function_cell.find('a')

        if function_link:
            function_text = function_link.get_text().strip()
            match = re.match(r'(.+?)\s+\((.+?):(\d+)\)', function_text)

            if match:
                return {
                    "name": match.group(1).strip(),
                    "file": match.group(2).strip(),
                    "line": int(match.group(3)),
                    "call_count": cells[1].get_text().strip(),
                    "coverage": cells[2].get_text().strip()
                }

        return None

    def _extract_function_info_enhanced(self, cells: List) -> Optional[Dict[str, Union[str, int, float, bool]]]:
        """提取增强函数信息"""
        function_cell = cells[0]
        function_link = function_cell.find('a')

        if function_link:
            function_text = function_link.get_text().strip()
            match = re.match(r'(.+?)\s+\((.+?):(\d+)\)', function_text)

            if match:
                function_name = match.group(1).strip()
                file_path = match.group(2).strip()
                line_number = int(match.group(3))

                call_count_text = cells[1].get_text().strip()
                call_count = self._parse_call_count(call_count_text)

                coverage_text = cells[2].get_text().strip()
                coverage_percent = self._parse_coverage_percentage(coverage_text)

                return {
                    "name": function_name,
                    "file": file_path,
                    "line": line_number,
                    "call_count": call_count,
                    "call_count_text": call_count_text,
                    "coverage_percent": coverage_percent,
                    "coverage_text": coverage_text,
                    "is_called": call_count > 0
                }

        return None

    def _parse_call_count(self, call_count_text: str) -> int:
        """解析调用次数"""
        if "not called" in call_count_text:
            return 0

        match = re.search(r'called (\d+) times?', call_count_text)
        if match:
            return int(match.group(1))

        return 0

    def _parse_coverage_percentage(self, coverage_text: str) -> float:
        """解析覆盖率百分比"""
        match = re.search(r'(\d+\.?\d*)%', coverage_text)
        if match:
            return float(match.group(1))
        return 0.0

    def _calculate_function_statistics(self, functions: List[Dict]) -> Dict[str, Union[int, float]]:
        """计算函数统计信息"""
        if not functions:
            return {}

        total_functions = len(functions)
        called_functions = len([f for f in functions if f.get("is_called", False)])
        uncalled_functions = total_functions - called_functions

        coverage_sum = sum(f.get("coverage_percent", 0) for f in functions)
        average_coverage = coverage_sum / total_functions if total_functions > 0 else 0.0

        return {
            "total_functions": total_functions,
            "called_functions": called_functions,
            "uncalled_functions": uncalled_functions,
            "average_coverage": round(average_coverage, 2)
        }

    def _extract_file_list(self) -> List[str]:
        """
        从覆盖率报告中提取文件名列表

        Returns:
            List[str]: 去重后的文件名列表
        """
        files = set()  # 使用set来自动去重

        # 从函数表格中提取文件名
        functions_table = self.soup.find('table', class_='listOfFunctions')

        if functions_table:
            rows = functions_table.find_all('tr')[1:]  # 跳过表头

            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 1:
                    function_cell = cells[0]
                    function_link = function_cell.find('a')

                    if function_link:
                        function_text = function_link.get_text().strip()
                        # 使用正则表达式提取文件名
                        match = re.match(r'.+?\s+\((.+?):(\d+)\)', function_text)
                        if match:
                            file_path = match.group(1).strip()
                            files.add(file_path)

        # 也可以从其他可能的位置提取文件名，比如页面标题或其他表格
        # 检查是否有文件覆盖率表格
        file_coverage_table = self.soup.find('table', class_='listOfFiles')
        if file_coverage_table:
            rows = file_coverage_table.find_all('tr')[1:]  # 跳过表头
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 1:
                    file_cell = cells[0]
                    file_link = file_cell.find('a')
                    if file_link:
                        file_name = file_link.get_text().strip()
                        files.add(file_name)
                    else:
                        # 如果没有链接，直接获取文本
                        file_name = file_cell.get_text().strip()
                        if file_name and not file_name.startswith('#'):
                            files.add(file_name)

        # 返回排序后的文件列表
        return sorted(list(files))


# 便捷函数
def parse_coverage_report(input_source: str, enhanced: bool = False, is_file: bool = True) -> Dict[str, Any]:
    """
    解析覆盖率报告的便捷函数

    Args:
        input_source (str): 输入源（文件路径或HTML字符串）
        enhanced (bool): 是否使用增强模式
        is_file (bool): 输入源是否为文件路径

    Returns:
        Dict: 解析结果
    """
    parser = CoverageParser()

    if is_file:
        return parser.parse_from_file(input_source, enhanced)
    else:
        return parser.parse_from_string(input_source, enhanced)


def save_coverage_result(result: Dict[str, Any], output_file: str, pretty: bool = True) -> None:
    """
    保存解析结果到JSON文件

    Args:
        result (Dict): 解析结果
        output_file (str): 输出文件路径
        pretty (bool): 是否格式化输出
    """
    json_kwargs = {'ensure_ascii': False}
    if pretty:
        json_kwargs.update({'indent': 2, 'sort_keys': True})

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, **json_kwargs)


def get_coverage_summary(result: Dict[str, Any]) -> Dict[str, float]:
    """
    获取覆盖率摘要信息

    Args:
        result (Dict): 解析结果

    Returns:
        Dict: 覆盖率摘要
    """
    summary = {}

    if 'summary' in result:
        for metric_name, metric_data in result['summary'].items():
            if 'coverage_percent' in metric_data:
                summary[metric_name] = metric_data['coverage_percent']
            elif 'coverage' in metric_data:
                # 基本模式，需要从字符串中提取百分比
                coverage_text = metric_data['coverage']
                match = re.search(r'(\d+\.?\d*)%', coverage_text)
                if match:
                    summary[metric_name] = float(match.group(1))

    return summary


def filter_functions_by_coverage(result: Dict[str, Any], max_coverage: float = 100.0) -> List[Dict]:
    """
    根据覆盖率过滤函数

    Args:
        result (Dict): 解析结果
        max_coverage (float): 最大覆盖率

    Returns:
        List: 过滤后的函数列表
    """
    if 'functions' not in result:
        return []

    filtered_functions = []

    for func in result['functions']:
        coverage = 0.0

        if 'coverage_percent' in func:
            coverage = func['coverage_percent']
        elif 'coverage' in func:
            # 基本模式，需要从字符串中提取百分比
            coverage_text = func['coverage']
            match = re.search(r'(\d+\.?\d*)%', coverage_text)
            if match:
                coverage = float(match.group(1))

        if  coverage < max_coverage:
            filtered_functions.append(func)

    return filtered_functions

def format_low_coverage_functions(functions):
    """格式化低覆盖率函数信息

    Args:
        functions: 低覆盖率函数列表

    Returns:
        str: 格式化后的函数信息
    """
    # 添加表头
    result = ["函数名 | 文件 | 行号 | 覆盖率 | 调用次数"]
    result.append("-" * 20)  # 分隔线

    for func in functions:
        # 只显示数据，不显示字段名
        func_info = f"{func['name']} | {func['file']} | {func['line']} | {func['coverage_text']} | {func['call_count_text']}"
        result.append(func_info)

    # 添加总结信息
    result.append(f"\n总计: {len(functions)} 个函数需要提高覆盖率\n")
    result.append("-" * 20)  # 分隔线

    return "\n".join(result)
