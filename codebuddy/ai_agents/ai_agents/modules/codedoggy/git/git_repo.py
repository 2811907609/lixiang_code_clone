import logging
import shutil
import tempfile
from pathlib import Path
from git import Repo
import threading
from typing import Optional, Dict


class GitRepoManager:
    _instance = None
    _lock = threading.Lock()
    _repo_pool: Dict[str, Dict[str, any]] = (
        {})  # {repo_url: {"repo": GitTempRepo, "in_use": bool}}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_repo(self, repo_url: str,
                 repo_name: str) -> Optional["GitTempRepo"]:
        with self._lock:
            logging.info("get_repo %s", repo_url)
            # 调用添加默认仓库
            if repo_url not in self._repo_pool:
                repo = clone_base_repo_if_not_exist(repo_url, repo_name)
                self._repo_pool[repo_url] = {"repo": repo, "in_use": True}
                return repo
            # 有可用缓存仓库，使用可用缓存仓库
            if not self._repo_pool[repo_url]["in_use"]:
                self._repo_pool[repo_url]["in_use"] = True
                return self._repo_pool[repo_url]["repo"]
        return None

    def add_repo(self, repo_url: str, repo: "GitTempRepo"):
        with self._lock:
            self._repo_pool[repo_url] = {"repo": repo, "in_use": True}

    def release_repo(self, repo_url: str):
        with self._lock:
            if repo_url in self._repo_pool:
                self._repo_pool[repo_url]["in_use"] = False


def clone_base_repo_if_not_exist(repo_url, repo_name):
    cache_dir = Path.home() / ".cache" / "codeDoggy"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not Path.exists(cache_dir / repo_name):
        logging.info("正在克隆仓库 %s 到 %s", repo_url, cache_dir / repo_name)
        Repo.clone_from(repo_url, cache_dir / repo_name, depth=1)
    return GitTempRepo(repo_url=repo_url,
                       repo_name=repo_name,
                       repo_path=cache_dir / repo_name)


class GitTempRepo:

    def __init__(self, repo_url, repo_name, repo_path=None):
        """
        初始化Git临时仓库操作类

        :param repo_url: 要克隆的Git仓库URL
        """
        self.repo_url = repo_url
        self.repo_name = repo_name
        self.cache_dir = Path.home() / ".cache" / "codeDoggy"
        self.temp_dir = None
        self.repo = None

        if repo_path:
            self.repo = Repo(repo_path)
            self.repo_dir = repo_path

    def clone(self):
        """
        clone 仓库到临时目录
        """
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp(dir=self.cache_dir))
        repo_dir = self.temp_dir / "repo"
        self.repo_dir = repo_dir
        # 克隆仓库
        logging.info("正在克隆仓库 %s 到 %s", self.repo_url, repo_dir)
        self.repo = Repo.clone_from(self.repo_url, repo_dir, depth=1)
        return self

    def clean_repo(self):
        """上下文管理器退出，清理临时目录"""
        if self.temp_dir and self.temp_dir.exists():
            logging.info("清理临时目录 %s", self.temp_dir)
            shutil.rmtree(self.temp_dir)

    def checkout(self, branch_or_commit):
        """检出指定分支或提交"""
        self.repo.git.checkout(branch_or_commit)

    def fetch(self, remote="origin", commit=None):
        """从远程仓库获取更新"""
        logging.info("fetch %s %s", remote, commit)
        if commit:
            self.repo.remote(name=remote).fetch(commit)
        else:
            self.repo.remote(name=remote).fetch()

    def diff(self, ref1, ref2, name_only=False, name_status=False):
        """比较两个引用之间的差异"""
        self.repo.git.diff(ref1, ref2)
        if name_only:
            return self.repo.git.diff(ref1, ref2, name_only=True)
        if name_status:
            return self.repo.git.diff(ref1, ref2, name_status=True)
        return self.repo.git.diff(ref1, ref2)

    def diff_single_file(self, ref1, ref2, file_path):
        return self.repo.git.diff(ref1, ref2, "--", file_path)

    def show(self, commit_hash, file_path=None):
        if file_path is None:
            return self.repo.git.show(commit_hash)
        return self.repo.git.show(commit_hash + ":" + file_path)

    def diff_stats(self, ref1, ref2, file_path=None):
        result = self.repo.git.diff("--numstat", ref1, ref2, "--", file_path)
        file_stats = {}
        for line in result.split('\n'):
            if not line.strip():
                continue

            # 格式: 添加行数 删除行数 文件名
            parts = line.split('\t')
            if len(parts) >= 3:
                filename = parts[2]
                insertions = int(parts[0]) if parts[0] != '-' else 0
                deletions = int(parts[1]) if parts[1] != '-' else 0

                file_stats[filename] = {
                    'insertions': insertions,
                    'deletions': deletions
                }

        return file_stats
