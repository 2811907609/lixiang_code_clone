"""
路径合并工具模块

提供智能路径合并功能，类似于tree -L命令的层级控制效果。
当路径数量超过指定限制时，自动合并深层目录。
"""

from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict


def merge_paths_to_limit(paths: List[str], max_lines: int) -> List[Tuple[str, int]]:
    """
    合并路径列表直到结果数量不超过max_lines限制

    Args:
        paths: 路径列表
        max_lines: 最大行数限制

    Returns:
        合并后的路径列表，格式为 [(path, file_counts), ...]
        其中 file_counts 表示该路径下合并的原始路径数量

    Examples:
        >>> paths = ["./a/b/c/file1.py", "./a/b/c/file2.py", "./a/b/d/file3.py"]
        >>> merge_paths_to_limit(paths, 2)
        [("./a/b/c", 2), ("./a/b/d", 1)]

        >>> paths = ["./a/b/c", "./a/b/d", "./a/e/f"]
        >>> merge_paths_to_limit(paths, 2)
        [("./a/b", 2), ("./a/e", 1)]
    """
    if not paths:
        return []

    if len(paths) <= max_lines:
        return [(path, 1) for path in sorted(paths)]

    # 初始化：每个路径的计数为1
    path_counts = {path: 1 for path in paths}

    while len(path_counts) > max_lines:
        # 计算所有路径的最大深度
        max_depth = max(_get_path_depth(p) for p in path_counts.keys())

        if max_depth <= 1:
            # 已经到根目录级别，无法再合并
            break

        # 合并到更浅的层级，同时累计计数
        path_counts = _merge_to_depth_with_counts(path_counts, max_depth - 1)

    # 转换为排序的元组列表
    result = [(path, count) for path, count in path_counts.items()]
    return sorted(result)


def _get_path_depth(path: str) -> int:
    """获取路径深度，支持跨平台"""
    # 使用 Path 来处理跨平台路径
    p = Path(path)

    # 规范化路径
    if str(p) in [".", "./"]:
        return 0

    # 获取路径的 parts，这会自动处理不同操作系统的分隔符
    parts = p.parts

    # 过滤掉当前目录标识
    filtered_parts = [part for part in parts if part not in [".", "./"]]

    return len(filtered_parts)


def _merge_to_depth_with_counts(path_counts: Dict[str, int], target_depth: int) -> Dict[str, int]:
    """
    将路径合并到指定深度，同时累计计数

    Args:
        path_counts: 路径及其计数的字典
        target_depth: 目标深度

    Returns:
        合并后的路径计数字典
    """
    merged_counts = defaultdict(int)

    for path, count in path_counts.items():
        merged_path = _truncate_to_depth(path, target_depth)
        merged_counts[merged_path] += count

    return dict(merged_counts)


def _merge_to_depth(paths: List[str], target_depth: int) -> List[str]:
    """
    将路径合并到指定深度

    Args:
        paths: 原始路径列表
        target_depth: 目标深度

    Returns:
        合并后的路径列表
    """
    merged_paths = set()

    for path in paths:
        merged_path = _truncate_to_depth(path, target_depth)
        merged_paths.add(merged_path)

    return list(merged_paths)


def _truncate_to_depth(path: str, depth: int) -> str:
    """
    将单个路径截断到指定深度，支持跨平台

    Args:
        path: 原始路径
        depth: 目标深度

    Returns:
        截断后的路径
    """
    if depth <= 0:
        return "."

    # 使用 Path 处理跨平台路径
    p = Path(path)
    parts = p.parts

    # 过滤掉当前目录标识，保留有效部分
    filtered_parts = []
    for part in parts:
        if part not in [".", "./"]:
            filtered_parts.append(part)

    # 如果深度超过实际路径长度，返回原路径
    if depth >= len(filtered_parts):
        return str(p)

    # 截断到指定深度
    result_parts = filtered_parts[:depth]

    if not result_parts:
        return "."

    # 使用 Path 重建路径，确保跨平台兼容性
    result_path = Path(*result_parts)

    # 如果原路径是相对路径且以 . 开头，保持这个特性
    if str(p).startswith("./") or str(p).startswith(".\\"):
        result_path = Path(".") / result_path

    return str(result_path)


def analyze_path_structure(paths: List[str]) -> Dict[str, any]:
    """
    分析路径结构，提供合并建议

    Args:
        paths: 路径列表

    Returns:
        包含结构分析信息的字典
    """
    if not paths:
        return {
            "total_paths": 0,
            "max_depth": 0,
            "depth_distribution": {},
            "common_prefixes": []
        }

    # 计算深度分布
    depth_count = defaultdict(int)
    for path in paths:
        depth = _get_path_depth(path)
        depth_count[depth] += 1

    # 找出公共前缀
    common_prefixes = _find_common_prefixes(paths)

    return {
        "total_paths": len(paths),
        "max_depth": max(_get_path_depth(p) for p in paths),
        "depth_distribution": dict(depth_count),
        "common_prefixes": common_prefixes
    }


def _find_common_prefixes(paths: List[str]) -> List[str]:
    """找出路径的公共前缀"""
    if not paths:
        return []

    # 按深度分组
    depth_groups = defaultdict(list)
    for path in paths:
        depth = _get_path_depth(path)
        depth_groups[depth].append(path)

    prefixes = []

    # 对每个深度的路径进行前缀分析
    for depth, path_list in depth_groups.items():
        if depth <= 1:
            continue

        prefix_count = defaultdict(list)
        for path in path_list:
            # 获取父目录作为前缀
            parent = str(Path(path).parent)
            if parent != ".":
                prefix_count[parent].append(path)

        # 找出有多个子项的前缀
        for prefix, sub_paths in prefix_count.items():
            if len(sub_paths) > 1:
                prefixes.append(prefix)

    return sorted(list(set(prefixes)))


def preview_merge_levels(paths: List[str], max_lines: int) -> List[Dict[str, any]]:
    """
    预览不同合并级别的效果

    Args:
        paths: 原始路径列表
        max_lines: 目标行数限制

    Returns:
        每个合并级别的预览信息列表
    """
    if not paths:
        return []

    previews = []
    current_paths = paths[:]
    max_depth = max(_get_path_depth(p) for p in paths)

    # 显示原始状态
    previews.append({
        "level": max_depth,
        "path_count": len(current_paths),
        "paths": sorted(current_paths[:10]),  # 只显示前10个作为示例
        "truncated": len(current_paths) > 10
    })

    # 逐级合并预览
    for level in range(max_depth - 1, 0, -1):
        merged_paths = _merge_to_depth(paths, level)
        merged_paths = sorted(list(set(merged_paths)))

        previews.append({
            "level": level,
            "path_count": len(merged_paths),
            "paths": sorted(merged_paths[:10]),
            "truncated": len(merged_paths) > 10
        })

        if len(merged_paths) <= max_lines:
            break

    return previews
