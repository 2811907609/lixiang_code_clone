import json
import logging
import os

from ai_agents.lib.tracing import litellm_tracing

env = None


def get_current_env():
    global env
    if env is None:
        # 懒加载模式
        return get_env()
    return env


def get_env():
    """获取环境变量中的关键信息"""
    # 获取基本环境变量
    event_id = os.environ.get("eventId", '')
    server = os.environ.get("server", '')

    # 获取并解析JSON格式的配置
    config_str = os.environ.get("config")
    config_data = {}
    if config_str:
        try:
            config_data = json.loads(config_str)
        except Exception as e:
            logging.error("解析config环境变量失败: %s", e)
    set_trace_env()
    # 获取并解析gitlabEventPayload
    gitlab_payload_str = os.environ.get("gitlabEventPayload")
    gitlab_payload = {}
    if gitlab_payload_str:
        try:
            gitlab_payload = json.loads(gitlab_payload_str)
        except Exception as e:
            logging.error("解析gitlabEventPayload环境变量失败: %s", e)

    # 获取gerritEventPayload
    gerrit_payload_str = os.environ.get("gerritEventPayload")
    gerrit_payload = {}
    if gerrit_payload_str:
        try:
            gerrit_payload = json.loads(gerrit_payload_str)
        except Exception as e:
            logging.error("解析gerritEventPayload环境变量失败: %s", e)

    global env
    env = {
        "eventId": event_id,
        "server": server,
        "config": config_data,
        "gitlabEventPayload": gitlab_payload,
        "gerritEventPayload": gerrit_payload,
    }
    return env


def set_trace_env():
    public_key = os.getenv("CODEDOGGY_LANGFUSE_PUBLIC_KEY", None)
    private_key = os.getenv("CODEDOGGY_LANGFUSE_PRIVATE_KEY", None)
    if public_key and private_key:
        os.environ["LANGFUSE_HOST"] = "https://liai-trace.chj.cloud"
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        os.environ["LANGFUSE_SECRET_KEY"] = private_key
        litellm_tracing()
