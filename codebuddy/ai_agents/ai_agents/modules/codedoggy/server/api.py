import logging
import sys
import time
import sentry_sdk

from ai_agents.modules.codedoggy.client.gerrit import GerritClient
from ai_agents.modules.codedoggy.client.gitlab import GitLabClient
from ai_agents.modules.codedoggy.server.env import get_current_env
from ai_agents.modules.codedoggy.server.handler import handler
from ai_agents.modules.codedoggy.server.workflow import Event
from ai_agents.modules.codedoggy.utils.repo import (
    parse_project_from_url,
    repo_basename,
    repo_url2clone_url,
)
from ai_agents.modules.codedoggy.utils.telemetry import telemetry_trigger_data, telemetry_execution_time
from sentry_sdk import set_extra
from sentry_sdk.integrations.logging import LoggingIntegration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



sentry_sdk.init(
    dsn="https://8d2035a77221496bb5b57080464fb7de@cfe-sentry.chehejia.com/101",
    environment="prod",
    traces_sample_rate=0.2,
    integrations=[LoggingIntegration(level=None, event_level=logging.ERROR)],
)


def extract_gerrit_repo_url(gerrit_url: str) -> str:
    gerrit_url = gerrit_url.replace("/c/", "/a/", 1)
    index = gerrit_url.find("/+/")
    if index == -1:
        return gerrit_url
    return gerrit_url[:index]


def handlerGerritEvent(env: dict[str, any]):
    # 检查基本环境变量
    if "gerritEventPayload" not in env:
        logger.error("缺少必要的环境变量: gerritEventPayload")
        sys.exit(1)

    if "server" not in env:
        logger.error("缺少必要的环境变量: server")
        sys.exit(1)

    if env["server"] != "gerrit":
        logger.error("服务器类型错误: 预期为 'gerrit'，实际为 '%s'", env["server"])
        sys.exit(1)

    if "eventId" not in env:
        logger.error("缺少必要的环境变量: eventId")
        sys.exit(1)

    if "config" not in env:
        logger.error("缺少必要的环境变量: config")
        sys.exit(1)

    # 检查 gerritEventPayload 中的必要字段
    required_gerrit_fields = ["url", "revisionId", "sourceCommit", "targetCommit"]
    for field in required_gerrit_fields:
        if field not in env["gerritEventPayload"]:
            logger.error("gerritEventPayload 中缺少必要字段: %s", field)
            sys.exit(1)

    # 获取必要的环境变量
    gerrit_url = env["gerritEventPayload"]["url"]
    revision_id = env["gerritEventPayload"]["revisionId"]
    source_commit = env["gerritEventPayload"]["sourceCommit"]
    target_commit = env["gerritEventPayload"]["targetCommit"]
    change_num = env["eventId"]

    project_name = parse_project_from_url(gerrit_url)

    # 处理 Gerrit URL 获取仓库 URL
    repo_url = extract_gerrit_repo_url(gerrit_url)
    server = "gerrit"
    repo_name = repo_basename(repo_url)
    clone_url = repo_url2clone_url(server, repo_url)

    # 创建 Gerrit 客户端
    client = GerritClient()

    # 创建并返回 Event 对象
    event = Event(
        repo_url=clone_url,
        source_commit=source_commit,
        target_commit=target_commit,
        repo_name=repo_name,
        server=server,
        change_num=change_num,
        revision_id=revision_id,
        gerrit_client=client,
        web_url=gerrit_url,
        project_name=project_name,
    )

    return event


def handlerGitlabEvent(env: dict[str, any]):
    # 检查基本环境变量
    if "gitlabEventPayload" not in env:
        logger.error("缺少必要的环境变量: gitlabEventPayload")
        sys.exit(1)

    if "server" not in env:
        logger.error("缺少必要的环境变量: server")
        sys.exit(1)

    if "eventId" not in env:
        logger.error("缺少必要的环境变量: eventId")
        sys.exit(1)

    if "config" not in env:
        logger.error("缺少必要的环境变量: config")
        sys.exit(1)

    # 检查 gitlabEventPayload 中的必要字段
    required_gitlab_fields = [
        "url",
        "cloneURL",
        "sourceCommit",
        "targetCommit",
        "repoName",
        "projectID",
        "baseSha",
        "startSha",
        "headSha",
    ]
    for field in required_gitlab_fields:
        if field not in env["gitlabEventPayload"]:
            logger.error("gitlabEventPayload 中缺少必要字段: %s", field)
            sys.exit(1)

    # 获取必要的环境变量
    clone_url = env["gitlabEventPayload"]["cloneURL"]
    source_commit = env["gitlabEventPayload"]["sourceCommit"]
    target_commit = env["gitlabEventPayload"]["targetCommit"]
    repo_name = env["gitlabEventPayload"]["repoName"]
    server = env["server"]
    project_id = env["gitlabEventPayload"]["projectID"]
    merge_request_id = env["eventId"]
    base_sha = env["gitlabEventPayload"]["baseSha"]
    start_sha = env["gitlabEventPayload"]["startSha"]
    head_sha = env["gitlabEventPayload"]["headSha"]
    url = env["gitlabEventPayload"]["url"]

    server_url = "https://gitlab.chehejia.com"

    # 检查访问令牌
    token_key = "gitlabAccessToken"
    if server == "gitlabee":
        server_url = "https://gitlabee.chehejia.com"
        token_key = "gitlabEEAccessToken"

    if token_key not in env["config"]:
        logger.error("config 中缺少必要的访问令牌: %s", token_key)
        sys.exit(1)

    access_token = env["config"][token_key]

    client = GitLabClient(
        server_url=server_url,
        private_token=access_token,
    )

    project_name = parse_project_from_url(url)

    event = Event(
        repo_url=clone_url,
        source_commit=source_commit,
        target_commit=target_commit,
        repo_name=repo_name,
        server=server,
        project_id=project_id,
        merge_request_id=merge_request_id,
        base_sha=base_sha,
        head_sha=head_sha,
        start_sha=start_sha,
        gitlab_client=client,
        web_url=url,
        project_name=project_name
    )
    return event

def _handle(event: Event):
    # 记录开始时间
    start_time = time.time()
    handler(event)
    # 记录结束时间并发送执行时间埋点
    end_time = time.time()
    execution_time_seconds = int(end_time - start_time)

    # 发送执行时间埋点数据
    telemetry_execution_time(event, execution_time_seconds)

def start_review_server(event:Event = None):
    env = get_current_env()
    if not event:
        server = env.get("server", None)
        if server is None:
            logger.error("缺少必要的环境变量: server")
            sys.exit(1)

        event = {}
        if server == "gerrit":
            event = handlerGerritEvent(env)
        else:
            event = handlerGitlabEvent(env)

        # 检查事件是否为空对象
        if not event:
            logger.error("生成的事件对象为空")
            sys.exit(1)

    set_extra("event_context", event.to_basic_dict())
    telemetry_trigger_data(event)
    _handle(event)



if __name__ == "__main__":
    start_review_server()
