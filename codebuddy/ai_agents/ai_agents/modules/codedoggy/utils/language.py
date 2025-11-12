import os


def detect_language_by_path(file_path):
    """
    通过文件路径判断编程语言类型

    参数:
        file_path (str): 文件路径

    返回:
        str: 检测到的编程语言，如果无法识别则返回 'Unknown'
    """
    # 获取文件扩展名（小写形式）
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # 常见编程语言的文件扩展名映射
    language_map = {
        # 脚本语言
        '.py': 'Python',
        '.pyw': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript (React)',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript (React)',
        '.php': 'PHP',
        '.pl': 'Perl',
        '.rb': 'Ruby',
        '.sh': 'Shell',
        '.bash': 'Shell',
        '.zsh': 'Shell',
        '.ps1': 'PowerShell',
        '.bat': 'Batch',
        '.cmd': 'Batch',

        # 编译型语言
        '.c': 'C',
        '.h': 'C',
        '.cpp': 'C++',
        '.hpp': 'C++',
        '.cc': 'C++',
        '.cxx': 'C++',
        '.java': 'Java',
        '.class': 'Java',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',

        # 标记语言
        '.html': 'HTML',
        '.htm': 'HTML',
        '.xhtml': 'HTML',
        '.xml': 'XML',
        '.svg': 'SVG',
        '.css': 'CSS',
        '.scss': 'Sass',
        '.less': 'Less',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.md': 'Markdown',

        # 数据库相关
        '.sql': 'SQL',
        '.ddl': 'SQL',
        '.dml': 'SQL',

        # 配置文件
        '.ini': 'INI',
        '.cfg': 'INI',
        '.conf': 'INI',
        '.properties': 'Properties',

        # 其他
        '.lua': 'Lua',
        '.r': 'R',
        '.m': 'MATLAB',
        '.dart': 'Dart',
        '.jl': 'Julia',
        '.hs': 'Haskell',
        '.erl': 'Erlang',
        '.ex': 'Elixir',
        '.clj': 'Clojure',
        '.f': 'Fortran',
        '.f90': 'Fortran',
        '.v': 'Verilog',
        '.vhd': 'VHDL',
        '.asm': 'Assembly',
        '.s': 'Assembly',
        '.vue': 'Vue',
    }

    # 特殊文件名处理（如 Makefile, Dockerfile 等）
    filename = os.path.basename(file_path).lower()
    if filename == 'makefile':
        return 'Makefile'
    elif filename == 'dockerfile':
        return 'Dockerfile'
    elif filename.endswith('dockerfile'):
        return 'Dockerfile'
    elif filename == 'cmakelists.txt':
        return 'CMake'

    # 通过扩展名查找语言
    return language_map.get(ext, 'Unknown')


def get_mr_main_language(diff_path_list: list):
    """
    判断合并请求的主要编程语言

    参数:
        diff_path_list (list): 合并请求中修改的文件路径列表

    返回:
        str: 主要编程语言，如果无法识别或列表为空则返回 'Unknown'
    """
    if not diff_path_list:
        return "Unknown"

    # 统计各种语言的出现次数
    language_counts = {}
    for file_path in diff_path_list:
        path = file_path[1]
        lang = detect_language_by_path(path)
        language_counts[lang] = language_counts.get(lang, 0) + 1

    # 排除 'Unknown' 语言
    if "Unknown" in language_counts and len(language_counts) > 1:
        del language_counts["Unknown"]

    # 返回出现次数最多的语言
    if not language_counts:
        return "Unknown"

    main_language = max(language_counts.items(), key=lambda x: x[1])[0]
    return main_language
