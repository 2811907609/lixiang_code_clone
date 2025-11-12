import os
import time
from venv import logger
import requests
from ai_agents.modules.codedoggy.server.workflow import Event

TELEMETRY_URL = "https://portal-k8s-prod.ep.chehejia.com/webhook-receiver/v1.0/invoke/webhook-receiver/method/webhook-receiver?uuid=d9000b78-4571-11ef-9190-32b8cfa558c5&name=codebuddy-telemetry-events-01"


def build_telemetry_data(session_id, data, name):
    ret = {
        "module": "codedoggy",
        "session_id": session_id,
        "seq": 1,
    }
    ret["details"] = data.format()
    ret["name"] = name
    if "time" not in ret:
        ret["time"] = time_in_milliseconds()
    ret["date_utc"] = int(time.strftime("%Y%m%d", time.gmtime(ret["time"] / 1000)))
    ret["hour_utc"] = time.gmtime(ret["time"] / 1000).tm_hour
    ret["uniq_id"] = f'{ret["session_id"]}:{ret["name"]}:{ret["time"]}:{ret["seq"]}'
    logger.info(f"build_telemetry_data: {ret}")
    return ret


def telemetry_trigger_data(event: Event):
    data = get_telemetry_data_by_server(event)
    ret = build_telemetry_data(event.session_id, data, "codedoggy:review.trigger")
    send_to_kafka(ret)


def telemetry_suggestion_list(event: Event, suggestion_list: list):
    data = get_telemetry_data_by_server(event)
    data.suggestion_list = suggestion_list
    ret = build_telemetry_data(
        event.session_id, data, "codedoggy:review.suggestion_list"
    )
    send_to_kafka(ret)


def telemetry_full_suggestion_list(event: Event, suggestion_list: list):
    data = get_telemetry_data_by_server(event)
    data.suggestion_list = suggestion_list
    ret = build_telemetry_data(
        event.session_id, data, "codedoggy:review.full.suggestion_list"
    )
    send_to_kafka(ret)


def telemetry_execution_time(event: Event, execution_time_s: int):
    """记录代码审查执行时间的埋点

    Args:
        event: Event对象，包含基本上下文信息
        execution_time_ms: 执行时间（毫秒）
    """
    data = get_telemetry_data_by_server(event)
    # 直接添加执行时间属性到现有的遥测数据对象
    data.execution_time_s = execution_time_s
    ret = build_telemetry_data(
        event.session_id, data, "codedoggy:review.execution_time"
    )
    send_to_kafka(ret)


def get_telemetry_data_by_server(event: Event):
    event.build_temetry_event()
    return (
        event.gerrit_telemetry_event
        if event.server == "gerrit"
        else event.gitlab_telemetry_event
    )


def time_in_milliseconds() -> int:
    return int(time.time() * 1000)


def send_to_kafka(data):
    logger.info("DRY_RUN: %s", os.environ.get("DRY_RUN"))
    logger.info("send to kafka: %s", data)
    if os.environ.get("DRY_RUN"):
        return
    try:
        requests.post(TELEMETRY_URL, json=data, timeout=5)
    except Exception as e:
        logger.error(f"send to kafka error: {e}")
