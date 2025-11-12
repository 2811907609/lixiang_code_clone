import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict


# 默认排除模式
DEFAULT_EXCLUDE_PATTERNS = [
    # 依赖目录
    "node_modules/", "site-packages/", ".venv/", "venv/", "env/",
    # 版本控制
    ".git/", ".svn/", ".hg/",
    # 缓存目录
    "__pycache__/", ".pytest_cache/", ".mypy_cache/", ".tox/",
    # 构建目录
    "target/", "build/", "dist/", "out/", "bin/", "obj/",
    # IDE目录
    ".vscode/", ".idea/", ".vs/",
    # 临时文件
    "tmp/", "temp/", "coverage/",
    # 编译文件
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.dylib",
    "*.class", "*.jar", "*.war", "*.ear",
    # 系统文件
    ".DS_Store", "Thumbs.db", "desktop.ini",
    # 日志文件
    "*.log", "*.log.*",
    # 大型数据文件
    "*.db", "*.sqlite", "*.sqlite3",
]

# 重要文件模式（优先显示）
IMPORTANT_FILE_PATTERNS = [
    "README*", "readme*", "CHANGELOG*", "LICENSE*", "CONTRIBUTING*",
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile",
    "Dockerfile", "docker-compose.yml", ".gitignore"
]


def should_exclude_path(path: Path, exclude_patterns: List[str]) -> bool:
    """
    检查路径是否应该被排除

    Args:
        path: 要检查的路径
        exclude_patterns: 排除模式列表

    Returns:
        bool: 如果应该排除返回True
    """
    import os
    import fnmatch

    path_str = str(path)
    name = path.name

    for pattern in exclude_patterns:
        # 目录模式（以/结尾）
        if pattern.endswith('/'):
            pattern_name = pattern.rstrip('/')
            if name == pattern_name:
                return True
            # 跨平台路径检查
            if path_str.endswith(os.sep + pattern_name) or path_str.endswith('/' + pattern_name):
                return True
        # 文件模式（通配符）
        elif '*' in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        # 精确匹配
        else:
            if name == pattern:
                return True

    return False


def is_important_file(path: Path) -> bool:
    """
    检查文件是否为重要文件

    Args:
        path: 文件路径

    Returns:
        bool: 如果是重要文件返回True
    """
    import fnmatch
    name = path.name

    for pattern in IMPORTANT_FILE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True

    return False


def count_items_with_timeout(directory: Path, timeout_seconds: float = 2.0) -> str:
    """
    在超时限制内计算目录中的文件数量

    Args:
        directory: 目录路径
        timeout_seconds: 超时时间（秒）

    Returns:
        str: 文件数量字符串，超时返回"?"
    """
    start_time = time.time()

    try:
        file_count = 0
        dir_count = 0

        for item in directory.iterdir():
            if time.time() - start_time > timeout_seconds:
                return "?"

            if item.is_file():
                file_count += 1
            elif item.is_dir():
                dir_count += 1

        if file_count == 0 and dir_count == 0:
            return "empty"
        elif file_count == 0:
            return f"{dir_count}d"
        elif dir_count == 0:
            return f"{file_count}f"
        else:
            return f"{file_count}f,{dir_count}d"

    except (PermissionError, OSError):
        return "?"


def get_file_size_category(size_bytes: int) -> str:
    """
    获取文件大小类别

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 大小类别标识
    """
    if size_bytes < 1024:
        return ""  # 小文件不显示
    elif size_bytes < 1024 * 1024:
        return f"({size_bytes // 1024}K)"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"({size_bytes // (1024 * 1024)}M)"
    else:
        return f"({size_bytes // (1024 * 1024 * 1024)}G)"


def get_file_type_prefix(path: Path) -> str:
    """
    根据文件类型获取简单的前缀标识

    Args:
        path: 文件路径

    Returns:
        str: 文件类型前缀
    """
    if path.is_dir():
        return "[DIR]"
    else:
        return "[FILE]"


def collect_directory_items(
    directory: Path,
    max_depth: int,
    exclude_patterns: List[str],
    include_hidden: bool = False
) -> List[Tuple[Path, str]]:
    """
    收集目录中的项目，平铺显示所有文件和目录

    Args:
        directory: 目录路径
        max_depth: 最大深度
        exclude_patterns: 排除模式
        include_hidden: 是否包含隐藏文件

    Returns:
        List: 项目列表，每个项目包含(绝对路径, 相对路径)
    """
    all_items = []

    def collect_items(current_dir: Path, current_depth: int):
        if current_depth > max_depth:
            return

        try:
            # 获取当前目录的所有项目
            dir_items = list(current_dir.iterdir())

            # 过滤项目
            filtered_items = []
            for item in dir_items:
                # 跳过隐藏文件（除非明确要求包含）
                if not include_hidden and item.name.startswith('.'):
                    continue

                # 跳过排除的项目
                if should_exclude_path(item, exclude_patterns):
                    continue

                filtered_items.append(item)

            # 分类并排序
            directories = [item for item in filtered_items if item.is_dir()]
            files = [item for item in filtered_items if item.is_file()]

            # 重要文件优先
            important_files = [f for f in files if is_important_file(f)]
            regular_files = [f for f in files if not is_important_file(f)]

            # 排序
            directories.sort(key=lambda x: x.name.lower())
            important_files.sort(key=lambda x: x.name.lower())
            regular_files.sort(key=lambda x: x.name.lower())

            # 添加到结果中
            for item in directories + important_files + regular_files:
                if current_depth == 0:
                    relative_path = item.name
                else:
                    relative_path = str(item.relative_to(directory))
                all_items.append((item, relative_path))

            # 递归处理子目录
            if current_depth < max_depth:
                for subdir in directories:
                    collect_items(subdir, current_depth + 1)

        except (PermissionError, OSError) as e:
            logging.warning(f"无法访问目录 {current_dir}: {e}")

    collect_items(directory, 0)
    return all_items


def format_directory_tree(
    items: List[Tuple[Path, str]],
    max_output_lines: int,
    show_file_counts: bool,
    show_file_info: bool,
    count_timeout: float
) -> Tuple[List[str], bool, Dict[str, int]]:
    """
    格式化目录树输出

    Args:
        items: 项目列表
        max_output_lines: 最大输出行数
        show_file_counts: 是否显示文件数量
        show_file_info: 是否显示文件信息
        count_timeout: 计数超时时间

    Returns:
        Tuple[List[str], bool, Dict[str, int]]: (输出行列表, 是否截断, 统计信息)
    """
    output_lines = []
    truncated = False
    stats = {"total_files": 0, "total_dirs": 0, "displayed_items": 0}

    # 预留空间给提示信息
    max_content_lines = max_output_lines - 15

    for item_path, relative_path in items:
        if len(output_lines) >= max_content_lines:
            truncated = True
            break

        # 获取类型前缀
        type_prefix = get_file_type_prefix(item_path)

        # 使用相对路径作为显示名称
        name = relative_path
        if item_path.is_dir():
            name += "/"
            stats["total_dirs"] += 1
        else:
            stats["total_files"] += 1

        # 添加文件数量信息
        count_info = ""
        if show_file_counts and item_path.is_dir():
            count = count_items_with_timeout(item_path, count_timeout)
            if count != "empty":
                count_info = f" ({count})"

        # 添加文件大小信息
        size_info = ""
        if show_file_info and item_path.is_file():
            try:
                size = item_path.stat().st_size
                size_info = get_file_size_category(size)
                if size_info:
                    size_info = f" {size_info}"
            except (OSError, PermissionError):
                pass

        # 组合输出行
        line = f"{type_prefix} {name}{count_info}{size_info}"
        output_lines.append(line)
        stats["displayed_items"] += 1

    return output_lines, truncated, stats


def browse_directory(
    directory_path: str,
    max_depth: int = 2,
    max_output_lines: int = 150,
    show_file_counts: bool = False,
    show_file_info: bool = True,
    include_hidden: bool = False,
    exclude_patterns: Optional[List[str]] = None,
    count_timeout_seconds: float = 2.0
) -> str:
    """
    Intelligently browse directory structure for large repository exploration

    Provides smart directory browsing functionality, especially suitable for understanding
    large code repository structures. Automatically excludes common non-user code directories
    (like node_modules, __pycache__, etc.) and provides helpful suggestions when output
    exceeds limits.

    Args:
        directory_path: Directory path to browse (relative or absolute path)
        max_depth: Maximum display depth, 1=current level only, 2=show subdirectory contents (default: 2, min: 1)
        max_output_lines: Maximum output lines, truncates and provides suggestions when exceeded (default: 150)
        show_file_counts: Whether to display file count statistics in directories (default: False, may be slow)
        show_file_info: Whether to display file size and other info (default: True)
        include_hidden: Whether to include hidden files and directories (default: False)
        exclude_patterns: Custom exclusion pattern list, merged with default patterns (default: None)
        count_timeout_seconds: Timeout for file counting to avoid hanging on large directories (default: 2.0)

    Returns:
        str: Formatted directory tree structure with file type icons and statistics

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If directory does not exist
        PermissionError: If access permissions are insufficient
        OSError: If directory access fails

    Examples:
        >>> browse_directory(".")  # Browse current directory
        >>> browse_directory("/path/to/project", max_depth=1)  # Show first level only
        >>> browse_directory("src", show_file_counts=True)  # Show file counts
        >>> browse_directory(".", exclude_patterns=["*.tmp", "cache/"])  # Custom exclusions
    """
    # 参数验证
    if not directory_path or not directory_path.strip():
        raise ValueError("directory_path 不能为空")

    if max_depth < 1:
        raise ValueError("max_depth 必须 >= 1")

    if max_output_lines < 10:
        raise ValueError("max_output_lines 必须 >= 10")

    if count_timeout_seconds <= 0:
        raise ValueError("count_timeout_seconds 必须 > 0")

    # 转换为Path对象
    directory = Path(directory_path)

    # 检查目录是否存在
    if not directory.exists():
        raise FileNotFoundError(f"目录 '{directory_path}' 不存在")

    if not directory.is_dir():
        raise ValueError(f"路径 '{directory_path}' 不是目录")

    try:
        # 合并排除模式
        all_exclude_patterns = DEFAULT_EXCLUDE_PATTERNS.copy()
        if exclude_patterns:
            all_exclude_patterns.extend(exclude_patterns)

        # 收集目录项目
        items = collect_directory_items(
            directory, max_depth, all_exclude_patterns, include_hidden
        )

        # 格式化输出
        output_lines, truncated, stats = format_directory_tree(
            items, max_output_lines,
            show_file_counts, show_file_info, count_timeout_seconds
        )

        # 构建最终输出
        result_lines = []

        # 添加标题
        result_lines.append(f"Directory: {directory.resolve()}")
        result_lines.append("=" * 60)

        # 添加目录树
        result_lines.extend(output_lines)

        # 添加统计信息
        result_lines.append("")
        result_lines.append("=" * 60)
        result_lines.append(f"Summary: {stats['displayed_items']} items displayed "
                          f"({stats['total_files']} files, {stats['total_dirs']} directories)")

        # 添加截断提示
        if truncated:
            result_lines.append("")
            result_lines.append("Output truncated - Suggestions:")
            result_lines.append(f"   • Reduce depth: browse_directory('{directory_path}', max_depth=1)")
            result_lines.append(f"   • Browse subdirectory: browse_directory('{directory_path}/subdir_name')")
            result_lines.append(f"   • Increase line limit: browse_directory('{directory_path}', max_output_lines=300)")
            if not show_file_counts:
                result_lines.append(f"   • Show file counts: browse_directory('{directory_path}', show_file_counts=True)")

        # 记录操作
        logging.info(f"浏览目录: {directory} (深度={max_depth}, 显示={stats['displayed_items']}项, 截断={truncated})")

        return '\n'.join(result_lines)

    except PermissionError as e:
        error_msg = f"访问目录 '{directory_path}' 权限不足: {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"访问目录 '{directory_path}' 失败: {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e


def quick_browse_directory(
    directory_path: str,
    show_only_dirs: bool = False,
    max_items: int = 50
) -> str:
    """
    快速浏览目录的第一层内容，适用于快速了解目录结构

    这是browse_directory的简化版本，只显示第一层内容，响应更快。
    特别适合在大型项目中快速了解顶层结构。

    Args:
        directory_path: 要浏览的目录路径
        show_only_dirs: 是否只显示目录，忽略文件（默认: False）
        max_items: 最大显示项目数（默认: 50）

    Returns:
        str: 简化的目录内容列表

    Examples:
        >>> quick_browse_directory(".")  # 快速查看当前目录
        >>> quick_browse_directory("/path/to/project", show_only_dirs=True)  # 只看目录
    """
    # 参数验证
    if not directory_path or not directory_path.strip():
        raise ValueError("directory_path 不能为空")

    if max_items < 1:
        raise ValueError("max_items 必须 >= 1")

    # 转换为Path对象
    directory = Path(directory_path)

    # 检查目录是否存在
    if not directory.exists():
        raise FileNotFoundError(f"目录 '{directory_path}' 不存在")

    if not directory.is_dir():
        raise ValueError(f"路径 '{directory_path}' 不是目录")

    try:
        # 获取目录内容
        all_items = list(directory.iterdir())

        # 过滤和分类
        directories = []
        files = []

        for item in all_items:
            # 跳过隐藏文件
            if item.name.startswith('.'):
                continue

            # 跳过排除的项目
            if should_exclude_path(item, DEFAULT_EXCLUDE_PATTERNS):
                continue

            if item.is_dir():
                directories.append(item)
            elif not show_only_dirs:
                files.append(item)

        # 排序
        directories.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())

        # 重要文件优先
        important_files = [f for f in files if is_important_file(f)]
        regular_files = [f for f in files if not is_important_file(f)]

        # 组合结果
        all_display_items = directories + important_files + regular_files

        # 限制数量
        display_items = all_display_items[:max_items]
        truncated = len(all_display_items) > max_items

        # 构建输出
        result_lines = []
        result_lines.append(f"Directory: {directory.resolve()}")
        result_lines.append("-" * 40)

        if not display_items:
            result_lines.append("(Empty directory or all items filtered)")
        else:
            for item in display_items:
                type_prefix = get_file_type_prefix(item)
                name = item.name
                if item.is_dir():
                    name += "/"
                result_lines.append(f"{type_prefix} {name}")

        # 添加统计
        total_dirs = len(directories)
        total_files = len(files)
        result_lines.append("-" * 40)
        result_lines.append(f"Summary: {len(display_items)} items displayed")
        if show_only_dirs:
            result_lines.append(f"   {total_dirs} directories")
        else:
            result_lines.append(f"   {total_dirs} directories, {total_files} files")

        if truncated:
            hidden_count = len(all_display_items) - max_items
            result_lines.append(f"   (+{hidden_count} items not shown)")
            result_lines.append(f"Tip: Use browse_directory('{directory_path}') for full structure")

        return '\n'.join(result_lines)

    except PermissionError as e:
        error_msg = f"访问目录 '{directory_path}' 权限不足: {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"访问目录 '{directory_path}' 失败: {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e
