import os
import re
from typing import Optional
from urllib.parse import urlparse


def repo_basename(repo_url: str):
    return os.path.basename(repo_url)


def category_type(repo_url: str) -> Optional[str]:
    if "gerrit" in repo_url:
        return "gerrit"
    elif "gitlabee" in repo_url:
        return "gitlabee"
    elif "gitlab" in repo_url:
        return "gitlab"
    elif "github.com" in repo_url:
        return "github"


def repo_url2clone_url(server: str, repo_url: str) -> Optional[str]:
    """
    将仓库 URL 转换为 SSH 格式的 clone URL

    Args:
        server: 服务器类型，支持 'gerrit', 'gitlab', 'gitlabee'
        repo_url: 原始仓库 URL

    Returns:
        SSH 格式的 clone URL
        - Gerrit: ssh://username@hostname:29418/path/to/repo
        - GitLab/GitLabEE: git@hostname:path/to/repo.git
    """
    # 解析输入的 URL
    parsed = urlparse(repo_url)

    # 获取主机名（去除可能存在的端口号）
    hostname = parsed.netloc.split(":")[0]  # 只取主机名部分，去掉端口号
    path = parsed.path

    # 去除路径开头的斜杠
    if path.startswith("/"):
        path = path[1:]

    # 根据不同的服务器类型处理 SSH 格式
    if server == "gerrit":
        # Gerrit 使用 ssh://username@hostname:port/path 格式
        username = os.getenv("GERRIT_CLONE_USERNAME", "spapi0001")
        # Gerrit 的 SSH 端口通常是 29418
        gerrit_ssh_port = 29418

        # 移除 Gerrit 路径中的 "a/" 前缀（如果存在）
        if path.startswith("a/"):
            path = path[2:]  # 去掉 "a/"

        # 构造 Gerrit 的 SSH URL: ssh://username@hostname:port/path
        ssh_url = f"ssh://{username}@{hostname}:{gerrit_ssh_port}/{path}"
    elif server == "gitlab" or server == "gitlabee":
        # GitLab 使用 git@hostname:path.git 格式

        # 确保路径以 .git 结尾
        if not path.endswith(".git"):
            path = f"{path}.git"

        # 构造 GitLab 的 SSH URL: git@hostname:path/to/repo.git
        ssh_url = f"git@{hostname}:{path}"
    else:
        raise ValueError("server invalid")

    return ssh_url


def parse_project_from_url(url):
    """
    解析GitLab和Gerrit URL中的项目路径

    Args:
        url (str): 输入的URL

    Returns:
        str: 解析出的项目路径，如果解析失败返回None
    """

    # 解析URL
    parsed = urlparse(url)
    path = parsed.path

    # 判断是GitLab还是Gerrit
    if "gitlab" in parsed.netloc or "gitlabee" in parsed.netloc:
        # GitLab URL格式: /project/path/-/merge_requests/id
        # 使用正则表达式匹配项目路径
        match = re.match(r"^/(.+?)/-/", path)
        if match:
            return match.group(1)

    elif "gerrit" in parsed.netloc:
        # Gerrit URL格式: /c/project/path/+/id
        # 使用正则表达式匹配项目路径
        match = re.match(r"^/c/(.+?)/\+/", path)
        if match:
            return match.group(1)

    return None
