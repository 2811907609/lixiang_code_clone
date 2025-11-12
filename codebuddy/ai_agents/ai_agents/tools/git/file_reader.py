

def get_git_file_content(repo_path: str, file_path: str, commit: str = "HEAD") -> str:
    """
    从Git仓库中读取指定文件的内容

    使用 'git show' 命令读取指定提交中某个文件的完整内容。
    支持读取任何提交、分支或标签中的文件内容。

    Args:
        repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'
        file_path: 文件的相对路径（相对于仓库根目录），格式如'xx/xx/xx.py'
        commit: Git提交标识符（可以是提交哈希、分支名、标签或HEAD引用），默认为HEAD

    Returns:
        str: 文件的完整内容文本
             如果文件不存在，将抛出RuntimeError异常

    示例:
        >>> content = get_git_file_content('/path/to/repo', '.codedoggy_config.yaml', 'HEAD')
        >>> 'review:\n  enabled: true\n  max_comments: 10'
    """
    import subprocess
    import logging

    if not repo_path:
        raise ValueError("repo_path is required")
    if not file_path:
        raise ValueError("file_path is required")
    if not commit:
        raise ValueError("commit is required")

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "show", f"{commit}:{file_path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        logging.info("Successfully read file %s from commit %s", file_path, commit)
        return result.stdout
    except subprocess.CalledProcessError as e:
        if "does not exist" in e.stderr or "Path" in e.stderr:
            raise RuntimeError(f"文件 {file_path} 在提交 {commit} 中不存在") from e
        else:
            raise RuntimeError(f"读取Git文件内容失败: {e.stderr}") from e


def check_git_file_exists(repo_path: str, file_path: str, commit: str = "HEAD") -> bool:
    """
    检查Git仓库中指定文件是否存在

    使用 'git cat-file' 命令检查指定提交中某个文件是否存在。

    Args:
        repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'
        file_path: 文件的相对路径（相对于仓库根目录），格式如'xx/xx/xx.py'
        commit: Git提交标识符（可以是提交哈希、分支名、标签或HEAD引用），默认为HEAD

    Returns:
        bool: 如果文件存在返回True，否则返回False

    示例:
        >>> exists = check_git_file_exists('/path/to/repo', '.codedoggy_config.yaml', 'HEAD')
        >>> True
    """
    import subprocess


    if not repo_path:
        raise ValueError("repo_path is required")
    if not file_path:
        raise ValueError("file_path is required")
    if not commit:
        raise ValueError("commit is required")

    try:
        subprocess.run(
            ["git", "-C", repo_path, "cat-file", "-e", f"{commit}:{file_path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
