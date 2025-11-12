def get_default_branch(repo_path: str) -> str:
    """
    获取Git仓库的默认分支名称

    使用git symbolic-ref命令来查询远程仓库的默认分支
    (通常由refs/remotes/origin/HEAD引用指向)

    Args:
        repo_path: 仓库路径（可操作的仓库路径），格式为'/xx/xx/xx'

    Returns:
        str: 默认分支名称，例如'main'或'master'
             如果无法确定默认分支，将抛出RuntimeError异常

    示例:
        >>> default_branch = get_default_branch('/path/to/repo')
        >>> 'main'  # 或 'master'等
    """
    import subprocess
    import logging

    if not repo_path:
        raise ValueError("repo_path is required")

    try:
        # 执行命令获取默认分支引用
        result = subprocess.run(
            ["git", "-C", repo_path, "symbolic-ref", "refs/remotes/origin/HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        # 提取分支名称，去除前缀"refs/remotes/origin/"
        ref_path = result.stdout.strip()
        if not ref_path:
            raise RuntimeError("无法获取默认分支：空引用")

        # 使用字符串操作提取分支名
        if ref_path.startswith("refs/remotes/origin/"):
            branch_name = ref_path.replace("refs/remotes/origin/", "", 1)
            logging.info("获取到默认分支: %s", branch_name)
            return branch_name
        else:
            raise RuntimeError(f"无法解析默认分支引用: {ref_path}")

    except subprocess.CalledProcessError as e:
        # 处理可能的错误
        error_message = e.stderr.strip() if e.stderr else "未知错误"
        raise RuntimeError(f"获取默认分支失败: {error_message}") from e
