import logging
import traceback
import uuid
from dataclasses import dataclass, fields
from typing import Callable

from ai_agents.modules.codedoggy.client.gerrit import GerritClient
from ai_agents.modules.codedoggy.client.gitlab import GitLabClient
from ai_agents.modules.codedoggy.git.git_repo import (
    GitRepoManager,
    GitTempRepo,
)
from ai_agents.modules.codedoggy.rule.config import CodeReviewConfig
from ai_agents.modules.codedoggy.rule.config_manager import (
    get_repo_config_manager,
)
from ai_agents.modules.codedoggy.utils.telemetry_model import (
    TelemetryBaseEvent,
    TelemetryGerritBaseEvent,
    TelemetryGitlabBaseEvent,
)

BASIC_TYPES = (str, int, float, bool, type(None), dict, list)

@dataclass
class Event:
    repo_url: str
    source_commit: str
    target_commit: str
    repo_name: str
    project_name: str
    server: str
    repo_path: str = None
    web_url: str = None
    mr_owner: str = None

    # gerrit
    change_num: str = None
    revision_id: str = None
    gerrit_client: GerritClient = None

    # gitlab
    project_id: str = None
    merge_request_id: str = None
    base_sha: str = None
    head_sha: str = None
    start_sha: str = None
    gitlab_client: GitLabClient = None

    all_suggestion_count = 10
    suggestion_count: int = 2
    suggestion_min_score: int = 7
    score_enable: bool = True

    repo_config: CodeReviewConfig = None

    gitlab_telemetry_event: TelemetryGitlabBaseEvent = None
    gerrit_telemetry_event: TelemetryGerritBaseEvent = None
    session_id: str = None

    def build_temetry_event(self):
        # 只在第一次调用时生成session_id，确保整个Event生命周期内保持一致
        if self.session_id is None:
            self.session_id = uuid.uuid4().hex

        base_event = TelemetryBaseEvent(
            server=self.server,
            web_url=self.web_url,
            source_commit=self.source_commit,
            target_commit=self.target_commit,
            project_name=self.repo_name,
            mr_owner=self.mr_owner,
            model=self.repo_config.model if self.repo_config else "",
            execution_time_s=None  # 执行时间会在埋点时单独设置
        )
        if self.server == "gerrit":
            self.gerrit_telemetry_event = TelemetryGerritBaseEvent.from_base_event(
                base_event=base_event,
                revision_id=self.revision_id,
                iid=self.change_num,
            )
        else:
            self.gitlab_telemetry_event = TelemetryGitlabBaseEvent.from_base_event(
                base_event=base_event,
                base_sha=self.base_sha,
                head_sha=self.head_sha,
                start_sha=self.start_sha,
                iid=self.merge_request_id,
            )

    def format_server_info(self):
        if self.server == "gerrit":
            return f"change_num: {self.change_num},revision_id: {self.revision_id}"
        else:
            return f"project_id: {self.project_id},merge_request_id: {self.merge_request_id},base_sha: {self.base_sha},head_sha: {self.head_sha},start_sha: {self.start_sha}"

    def to_basic_dict(self) -> dict:
        """
        只保留 dataclass 中的基础类型字段，
        基础类型: str, int, float, bool, None, dict, list
        复杂对象会跳过
        """
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, BASIC_TYPES):
                result[f.name] = value
            else:
                continue
        return result

@dataclass
class FileReviewEvent:
    repo_path: str
    source_commit: str
    target_commit: str
    file_path: str
    diff_content: str
    mr_diff_content: str = None
    file_content: str = None
    language: str = None
    suggestion_count: int = 2
    server: str = None
    event_id : str = None
    project_id : str = None
    repo_config : CodeReviewConfig = None

class ReviewWorkflow:

    def __init__(
        self,
        event: Event,
        workflow_steps: list[Callable],
    ):
        self.workflow_steps = workflow_steps
        self.event = event
        self.repo_manager = GitRepoManager.get_instance()
        self.repo = None
        self.use_cached_repo = False

    def __enter__(self):
        # 尝试从缓存获取可用的 repo
        cached_repo = self.repo_manager.get_repo(self.event.repo_url, self.event.repo_name)
        logging.info("cached_repo: %s", cached_repo)

        if cached_repo:
            self.repo = cached_repo
            self.use_cached_repo = True
        else:
            # 创建新的临时仓库
            self.repo = GitTempRepo(self.event.repo_url, self.event.repo_name)
            self.use_cached_repo = False

        # 执行仓库操作
        logging.debug("event: %s", self.event)
        try:
            if not self.use_cached_repo:
                self.repo.clone()

            self.event.repo_path = self.repo.repo_dir
            # self.repo.fetch()
            self.repo.fetch(commit=self.event.source_commit)
            self.repo.fetch(commit=self.event.target_commit)
            self.add_repo_config()
            return self
        except Exception:
            if not self.use_cached_repo and self.repo:
                self.repo.clean_repo()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.repo:
            if self.use_cached_repo:
                self.repo_manager.release_repo(self.event.repo_url)
            else:
                logging.debug("clean repo")
                self.repo.clean_repo()
            self.event.repo_path = None
        return False

    def execute_workflow(self):
        """执行工作流步骤"""
        for step in self.workflow_steps:
            try:
                step(self)
            except Exception as e:
                error_traceback = traceback.format_exc()
                logging.error(
                    "执行步骤 %s 时发生错误 \n 异常类型: %s \n 错误信息: %s \n 异常位置: %s",
                    step.__name__,
                    type(e).__name__,
                    str(e),
                    error_traceback,
                )
                raise e

    def add_repo_config(self):
        repo_config_manager = get_repo_config_manager()
        config = repo_config_manager.get_config(
            repo_path=self.event.repo_path,
            project=self.event.project_name,
            server=self.event.server,
        )
        self.event.all_suggestion_count = config.max_comments
        self.event.suggestion_count = config.file_max_comment
        if config.scoring.get("enabled", False):
            self.event.suggestion_min_score = config.scoring.get("score", 7)
        else:
            self.event.score_enable = False
            self.event.suggestion_min_score = 0
        self.event.repo_config = config
