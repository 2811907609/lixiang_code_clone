#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCOV行级覆盖率报告解析器 - 改进版本
使用BeautifulSoup解析gcovr生成的HTML源文件覆盖率报告
相比正则表达式方法更稳定、更易维护
"""

import re
from typing import List, Dict, NamedTuple
from pathlib import Path
from bs4 import BeautifulSoup




class LineCoverageInfo(NamedTuple):
    """行覆盖率信息数据结构"""
    line_number: int           # 行号
    is_covered: bool          # 是否被覆盖
    execution_count: int      # 执行次数（覆盖次数）
    content: str              # 代码内容
    coverage_class: str       # 覆盖率CSS类别 (coveredLine, uncoveredLine, partialCoveredLine)


class GcovLineCoverageParserImproved:
    """GCOV行级覆盖率报告解析器 - 改进版本"""

    def __init__(self, html_file_path: str):
        """
        初始化解析器

        Args:
            html_file_path: HTML覆盖率报告文件路径
        """
        self.html_file_path = Path(html_file_path)

    def parse(self) -> List[LineCoverageInfo]:
        """
        解析行级覆盖率报告文件

        Returns:
            List[LineCoverageInfo]: 行覆盖率信息列表
        """
        if not self.html_file_path.exists():
            return []

        with open(self.html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._parse_with_bs4(content)

    def _parse_with_bs4(self, content: str) -> List[LineCoverageInfo]:
        """
        使用BeautifulSoup解析HTML内容

        Args:
            content: HTML内容

        Returns:
            List[LineCoverageInfo]: 行覆盖率信息列表
        """
        coverage_infos = []
        soup = BeautifulSoup(content, 'html.parser')

        # 查找所有源代码行
        source_rows = soup.find_all('tr', class_='source-line')

        for row in source_rows:
            try:
                # 提取行号
                line_cell = row.find('td', class_='lineno')
                if not line_cell:
                    continue

                line_link = line_cell.find('a')
                if not line_link:
                    continue

                line_number = int(line_link.get_text().strip())

                # 提取执行次数和覆盖状态
                count_cell = row.find('td', class_=re.compile(r'linecount'))
                if not count_cell:
                    continue

                count_text = count_cell.get_text().strip()
                count_class = ' '.join(count_cell.get('class', []))
                execution_count = self._parse_execution_count(count_text)

                # 提取源代码内容
                src_cell = row.find('td', class_=re.compile(r'src'))
                if not src_cell:
                    continue

                src_class = ' '.join(src_cell.get('class', []))
                # 获取源代码内容并清理HTML标签
                src_content = self._clean_source_content(src_cell)

                # 判断覆盖状态
                is_covered = self._determine_coverage_status(count_class, execution_count)

                # 确定覆盖率类别
                coverage_class = self._determine_coverage_class(count_class, src_class)

                coverage_info = LineCoverageInfo(
                    line_number=line_number,
                    is_covered=is_covered,
                    execution_count=execution_count,
                    content=src_content,
                    coverage_class=coverage_class
                )

                coverage_infos.append(coverage_info)

            except Exception as e:
                print(f"解析行时发生错误: {e}")
                continue

        return sorted(coverage_infos, key=lambda x: x.line_number)


    def _parse_execution_count(self, count_text: str) -> int:
        """
        解析执行次数
        基于HTML特征：
        - 覆盖行：包含数字 "15", "2" 等
        - 未覆盖行：包含 "&cross;" (HTML实体)
        - 空行：空字符串

        Args:
            count_text: 执行次数文本

        Returns:
            int: 执行次数
        """
        if not count_text:
            return 0

        # 如果是 &cross; 或类似的HTML实体，说明是未覆盖行
        if '&cross;' in count_text or '×' in count_text or '✗' in count_text:
            return 0

        # 直接提取数字
        numbers = re.findall(r'\d+', count_text)
        if numbers:
            return int(numbers[0])

        return 0

    def _determine_coverage_status(self, count_class: str, execution_count: int) -> bool:
        """
        判断是否被覆盖
        基于HTML特征：
        - 覆盖行：class="linecount coveredLine" 且有执行次数
        - 未覆盖行：class="linecount uncoveredLine" 且内容是 &cross;
        - 空行：class="linecount " (空类)

        Args:
            count_class: 计数CSS类别
            execution_count: 执行次数

        Returns:
            bool: 是否被覆盖
        """
        # 如果明确标记为未覆盖行，则未被覆盖
        if 'uncoveredLine' in count_class:
            return False

        # 如果有执行次数，则被覆盖
        if execution_count > 0:
            return True

        # 根据CSS类别判断
        if 'coveredLine' in count_class or 'partialCoveredLine' in count_class:
            return True

        # 空类的行（如括号行）也算未覆盖，但不是关键的未覆盖
        return False

    def _determine_coverage_class(self, count_class: str, src_class: str) -> str:
        """
        确定覆盖率类别
        基于HTML特征：
        - uncoveredLine: <td class="linecount uncoveredLine">&cross;</td> (显示✗)
        - coveredLine: <td class="linecount coveredLine">数字</td>
        - 空类: <td class="linecount "></td> (括号行等)

        Args:
            count_class: 计数CSS类别
            src_class: 源码CSS类别

        Returns:
            str: 覆盖率类别
        """
        if 'uncoveredLine' in count_class or 'uncoveredLine' in src_class:
            return 'uncoveredLine'
        elif 'coveredLine' in count_class or 'coveredLine' in src_class:
            return 'coveredLine'
        elif 'partialCoveredLine' in count_class or 'partialCoveredLine' in src_class:
            return 'partialCoveredLine'
        else:
            return 'empty_line'

    def _clean_source_content(self, src_cell) -> str:
        """
        清理源代码内容，去除HTML标签（BeautifulSoup版本）

        Args:
            src_cell: BeautifulSoup的td元素

        Returns:
            str: 清理后的源代码
        """
        # 使用BeautifulSoup的get_text()方法自动处理HTML实体
        return src_cell.get_text().strip()


    def _clean_source_content_text(self, src_content: str) -> str:
        """
        清理源代码内容，去除HTML标签（文本版本）

        Args:
            src_content: 原始源代码HTML内容

        Returns:
            str: 清理后的源代码
        """
        # 去除HTML标签
        clean_content = re.sub(r'<[^>]+>', '', src_content)

        # 解码HTML实体
        clean_content = clean_content.replace('&lt;', '<')
        clean_content = clean_content.replace('&gt;', '>')
        clean_content = clean_content.replace('&amp;', '&')
        clean_content = clean_content.replace('&quot;', '"')
        clean_content = clean_content.replace('&#39;', "'")

        return clean_content.strip()

    def get_summary(self, coverage_infos: List[LineCoverageInfo]) -> Dict:
        """
        获取覆盖率摘要信息

        Args:
            coverage_infos: 行覆盖率信息列表

        Returns:
            Dict: 摘要信息
        """
        total_lines = len(coverage_infos)
        covered_lines = sum(1 for info in coverage_infos if info.is_covered)
        uncovered_lines = total_lines - covered_lines

        # 按覆盖率类别统计
        covered_count = sum(1 for info in coverage_infos if info.coverage_class == 'coveredLine')
        partial_count = sum(1 for info in coverage_infos if info.coverage_class == 'partialCoveredLine')
        uncovered_count = sum(1 for info in coverage_infos if info.coverage_class == 'uncoveredLine')

        if total_lines > 0:
            overall_coverage = (covered_lines / total_lines) * 100
        else:
            overall_coverage = 0.0

        total_executions = sum(info.execution_count for info in coverage_infos)

        return {
            'total_lines': total_lines,
            'covered_lines': covered_lines,
            'uncovered_lines': uncovered_lines,
            'overall_coverage_percentage': overall_coverage,
            'total_executions': total_executions,
            'fully_covered_lines': covered_count,
            'partially_covered_lines': partial_count,
            'uncovered_lines_count': uncovered_count,
            'parser_method': 'BeautifulSoup'
        }

    def print_coverage_report(self, coverage_infos: List[LineCoverageInfo], show_details: bool = True):
        """
        打印覆盖率报告

        Args:
            coverage_infos: 行覆盖率信息列表
            show_details: 是否显示详细信息
        """
        print("=" * 80)
        print("GCOV 行级覆盖率报告 (改进版)")
        print("=" * 80)

        # 打印摘要
        summary = self.get_summary(coverage_infos)
        print(f"解析方法: {summary['parser_method']}")
        print(f"总行数: {summary['total_lines']}")
        print(f"已覆盖行数: {summary['covered_lines']}")
        print(f"未覆盖行数: {summary['uncovered_lines']}")
        print(f"整体覆盖率: {summary['overall_coverage_percentage']:.1f}%")
        print(f"总执行次数: {summary['total_executions']}")
        print(f"完全覆盖行数: {summary['fully_covered_lines']}")
        print(f"部分覆盖行数: {summary['partially_covered_lines']}")
        print(f"未覆盖行数: {summary['uncovered_lines_count']}")
        print()

        if show_details:
            # 打印详细信息
            print("详细信息:")
            print("-" * 80)
            print(f"{'行号':<6} {'状态':<6} {'执行次数':<8} {'覆盖类型':<15} {'代码内容'}")
            print("-" * 80)

            for info in coverage_infos:
                status = "✓" if info.is_covered else "✗"
                coverage_type = info.coverage_class
                # 截断过长的代码内容
                content = info.content[:50] + "..." if len(info.content) > 50 else info.content

                print(f"{info.line_number:<6} {status:<6} {info.execution_count:<8} {coverage_type:<15} {content}")

    def get_uncovered_lines(self, coverage_infos: List[LineCoverageInfo]) -> List[LineCoverageInfo]:
        """
        获取未覆盖的代码行

        Args:
            coverage_infos: 行覆盖率信息列表

        Returns:
            List[LineCoverageInfo]: 未覆盖的行信息
        """
        return [info for info in coverage_infos if not info.is_covered]

    def get_highly_executed_lines(self, coverage_infos: List[LineCoverageInfo], threshold: int = 10) -> List[LineCoverageInfo]:
        """
        获取高频执行的代码行

        Args:
            coverage_infos: 行覆盖率信息列表
            threshold: 执行次数阈值

        Returns:
            List[LineCoverageInfo]: 高频执行的行信息
        """
        return [info for info in coverage_infos if info.execution_count >= threshold]

    def get_line_range_coverage(self, coverage_infos: List[LineCoverageInfo], start_line: int, end_line: int) -> Dict[int, Dict]:
        """
        获取指定行号范围内每行的覆盖情况

        Args:
            coverage_infos: 行覆盖率信息列表
            start_line: 起始行号（包含）
            end_line: 结束行号（包含）

        Returns:
            Dict[int, Dict]: 行号到覆盖信息的映射
        """
        # 创建行号到覆盖信息的映射
        line_map = {info.line_number: info for info in coverage_infos}

        result = {}
        for line_num in range(start_line, end_line + 1):
            if line_num in line_map:
                info = line_map[line_num]
                result[line_num] = {
                    'is_covered': info.is_covered,
                    'execution_count': info.execution_count,
                    'content': info.content,
                    'coverage_class': info.coverage_class
                }
            else:
                # 如果该行不在覆盖率报告中，可能是空行或注释行
                result[line_num] = {
                    'is_covered': False,
                    'execution_count': 0,
                    'content': '',
                    'coverage_class': 'not_available'
                }

        return result


def get_line_range_coverage_from_file_improved(html_file_path: str, start_line: int, end_line: int) -> Dict[int, Dict]:
    """
    从覆盖率报告文件中获取指定行号范围内每行的覆盖情况 (改进版)

    Args:
        html_file_path: HTML覆盖率报告文件路径
        start_line: 起始行号（包含）
        end_line: 结束行号（包含）

    Returns:
        Dict[int, Dict]: 行号到覆盖信息的映射
    """
    parser = GcovLineCoverageParserImproved(html_file_path)
    coverage_infos = parser.parse()
    return parser.get_line_range_coverage(coverage_infos, start_line, end_line)


def format_code_with_coverage(coverage_dict: Dict[int, Dict]) -> str:
    """
    将覆盖率信息转换为带有覆盖状态标记的代码格式
    根据HTML中的实际特征来标记未覆盖行

    Args:
        coverage_dict: 行号到覆盖信息的映射

    Returns:
        str: 格式化后的代码字符串，每行开头标明覆盖状态
    """
    result_lines = []

    for line_num in sorted(coverage_dict.keys()):
        info = coverage_dict[line_num]
        coverage_class = info.get('coverage_class', '')

        # 根据HTML特征确定覆盖状态标记
        if coverage_class == 'uncoveredLine':
            # 对应HTML中 <td class="linecount uncoveredLine">&cross;</td>
            coverage_mark = "✗"
        elif info['is_covered'] and info['execution_count'] > 0:
            # 被覆盖，显示执行次数
            coverage_mark = f"{info['execution_count']}"
        elif coverage_class == 'empty_line':
            # 空行或括号行，不显示标记
            coverage_mark = ""
        else:
            # 其他情况
            coverage_mark = ""

        # 格式化代码行
        code_content = info['content'] if info['content'] else ""
        if coverage_mark:
            formatted_line = f"{coverage_mark}\t{code_content}"
        else:
            formatted_line = f"\t{code_content}"

        result_lines.append(formatted_line)

    return "\n".join(result_lines)


def identify_uncovered_lines_with_checkmark(coverage_dict: Dict[int, Dict]) -> List[Dict]:
    """
    识别所有带有✗标记的未覆盖行
    这些行在HTML中的特征是：class="linecount uncoveredLine" 且内容是 &cross;

    Args:
        coverage_dict: 行号到覆盖信息的映射

    Returns:
        List[Dict]: 未覆盖行信息列表，包含行号、内容等信息
    """
    uncovered_lines = []

    for line_num in sorted(coverage_dict.keys()):
        info = coverage_dict[line_num]

        # 检查是否是真正的未覆盖行（有✗标记的）
        if info.get('coverage_class') == 'uncoveredLine':
            uncovered_lines.append({
                'line_number': line_num,
                'content': info['content'],
                'coverage_class': info['coverage_class'],
                'has_checkmark': True  # 标记这行应该显示✗
            })

    return uncovered_lines


def get_formatted_code_with_coverage_improved(html_file_path: str, start_line: int, end_line: int):
    """
    从覆盖率报告文件中获取指定行号范围的代码，并标记覆盖状态 (改进版)

    Args:
        html_file_path: HTML覆盖率报告文件路径
        start_line: 起始行号（包含）
        end_line: 结束行号（包含）

    Returns:
        str: 格式化后的代码字符串，每行开头标明覆盖状态
    """
    coverage_dict = get_line_range_coverage_from_file_improved(html_file_path, start_line, end_line)
    return format_code_with_coverage(coverage_dict), identify_uncovered_lines_with_checkmark(coverage_dict)
