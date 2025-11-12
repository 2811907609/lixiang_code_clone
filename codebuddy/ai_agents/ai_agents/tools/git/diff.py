
def get_git_diff_content(repo_path: str, source_commit: str,
                         target_commit: str) -> str:
    """
    获取两个Git提交之间的差异内容

    执行 'git diff' 命令比较两个提交之间的代码变更，返回完整的差异内容文本。
    差异内容包括添加、删除和修改的文件及其内容变更细节。
    Args:
        repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'
        source_commit: 源提交的标识符（可以是提交哈希、分支名、标签或HEAD引用）
        target_commit: 目标提交的标识符（可以是提交哈希、分支名、标签或HEAD引用）
    Returns:
        str: 包含完整差异信息的文本，使用统一差异格式(unified diff format)
             如果两个提交之间没有差异，将返回空字符串
    示例:
    >>> diff = get_git_diff_content('/path/to/repo', 'HEAD~1', 'HEAD')
    'diff --git a/file.txt b/file.txt\nindex abc123..def456 100644\n--- a/file.txt\n+++ b/file.txt\n@@ -1,3 +1,4'
    """
    import subprocess
    import logging

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "diff", source_commit, target_commit],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        logging.info("diff result stdout: %s", result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git diff统计命令执行失败: {e.stderr}") from e
