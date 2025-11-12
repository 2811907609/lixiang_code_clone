
def git_grep_files(
    repo_path: str,
    commit: str,
    words: str,
) -> str:
    """
    在指定Git提交中全文搜索包含关键词的文件路径。

    使用 git grep 命令在仓库中执行全文搜索，返回包含指定关键词的文件列表。
    搜索结果不区分大小写，仅返回文件路径，不包含匹配内容。

    Args:
    repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'
    words: 搜索关键词（字符串），支持正则表达式，多个关键词可用空格分隔
    commit: 目标Git提交标识符（可以是提交哈希、分支名或标签）

    Returns:
        list[str]: 包含关键词的文件路径列表，按字母顺序排序
                如没有找到匹配文件，返回空列表
    示例:
        >>> git_grep_files('/path/to/repo', 'main', 'getUserInfo')
        ['src/auth.go', 'src/user/profile.js']
    """
    import subprocess
    import logging

    if not repo_path:
        raise ValueError("repo_path is required")
    if not commit:
        raise ValueError("commit is required")
    if not words:
        raise ValueError("words is required")
    cmd = [
        "git",
        "-C",
        repo_path,
        "grep",
        "--full-name",  # 显示相对仓库根目录的路径
        "--name-only",  # 只输出文件名，不输出匹配内容
        "-l",  # 只显示包含匹配的文件名
        words,
        commit,
    ]
    logging.info("git grep cmd: %s", cmd)
    try:
        # 执行命令并捕获输出
        result = subprocess.run(cmd,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        # 按行分割输出并去重
        files = set()
        for line in result.stdout.splitlines():
            # 分割格式示例：commit:path:line:content → 取 path 部分
            path = line.split(":", 2)[1]  # 分割两次，保留第二个部分
            files.add(path)
        return sorted(files)

    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # git grep 未找到匹配
            return ""
        raise RuntimeError(f"git grep 执行失败: {e.stderr}") from e


def is_path_in_repo(repo_path: str, file_path: str, commit: str) -> bool:
    """
    检查指定文件路径是否存在于特定Git提交中
    通过执行'git ls-files --with-tree={commit}'命令检查文件是否被Git跟踪

    Args:
        repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'
        file_path: 文件的相对路径（相对于仓库根目录），格式如'xx/xx/xx.go'
        commit: 目标Git提交标识符（可以是提交哈希、分支名或标签）
    Returns:
        bool: 若文件在指定提交中存在则返回True，否则返回False

    """

    from pathlib import Path
    import subprocess
    import logging

    if not repo_path:
        raise ValueError("repo_path is required")
    if not file_path:
        raise ValueError("file_path is required")
    if not commit:
        raise ValueError("commit is required")
    path = str(Path(file_path).as_posix())

    cmd_tracked = [
        "git",
        "-C",
        repo_path,
        "ls-files",
        f"--with-tree={commit}",
        "--",
        path,
    ]
    logging.info("cmd_tracked: %s", cmd_tracked)
    res = subprocess.run(
        cmd_tracked,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not res.stdout:
        return False
    return True
