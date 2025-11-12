import json
import logging
import re
from ai_agents.modules.codedoggy.agent.model import (create_model_config_from_env)
from ai_agents.modules.codedoggy.agent.prompts.prompt import load_prompt
from ai_agents.modules.codedoggy.server.workflow import Event
from sysutils.retry import retry


def filter_comment(event: Event, suggestion_list: list):
    if suggestion_list is None or len(suggestion_list) == 0:
        return
    exist_suggestion = []
    if event.server == "gerrit":
        exist_suggestion = get_gerrit_change_suggestion(event)
    else:
        exist_suggestion = get_gitlab_mr_suggestion(event)
    if not exist_suggestion:
        return suggestion_list

    new_suggestion_list = agent_filter_suggestion(exist_suggestion,
                                                  suggestion_list, event.repo_config.model)
    return new_suggestion_list


def get_gerrit_change_suggestion(event: Event):
    return []


def get_gitlab_mr_suggestion(event: Event):
    notes = event.gitlab_client.get_mr_discussion(event.merge_request_id,
                                                        event.project_id)
    if not notes or len(notes) == 0:
        return []
    comments = []
    for n in notes:
        note = n.get("notes", [])
        if not note:
            continue
        author = note[0].get("author", {})
        if author.get("username") != "codedoggy-gl-svc":
            continue
        body = note[0].get("body", "")
        path = note[0].get("position", {}).get("new_path", "")
        line = note[0].get("position", {}).get("new_line", 0)
        content = get_suggestion_content_for_server(body)

        comment = {
            "suggestionContent": content,
            "relevantFile": path,
            "suggestionLine": line,
        }
        comments.append(comment)
    return comments


def get_suggestion_content_for_server(suggestion: str):
    start_tag = "**1. 建议**:"
    end_tag = "**2. 标签**"

    start = suggestion.find(start_tag)
    end = suggestion.find(end_tag)
    suggestion_content = ""
    if start != -1 and end != -1:
        suggestion_content = suggestion[start + len(start_tag):end].strip()
    return suggestion_content


# 测试修改
@retry(n=2, delay=3)
def agent_filter_suggestion(
    exist_suggestion: list,
    suggestion_list: list,
    model : list,
):
    """
    过滤建议列表，调用LLM模型进行处理并解析返回的JSON结果

    Args:
        exist_suggestion: 已存在的建议列表
        suggestion_list: 需要过滤的新建议列表

    Returns:
        list: 解析后的建议列表
    """

    task = load_prompt(
        "filter_comment",
        exist_suggestion=exist_suggestion,
        suggestion_list=suggestion_list,
    )
    _model = create_model_config_from_env(model)
    response_stream = _model.generate_stream(
        messages=[{
            "role": "user",
            "content": task
        }],
        temperature=0,
    )
    logging.warning("response %s", response_stream)
    collected_content = ""
    for chunk in response_stream:
        if chunk.content:
            logging.warning(chunk.content)
            collected_content += chunk.content
    logging.warning("collected_content: %s", collected_content)
    if not collected_content:
        return suggestion_list
    try:
        # 使用正则表达式提取JSON部分（更稳健的方法）
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```",
                               collected_content)

        if json_match:
            # 提取JSON字符串并解析
            json_str = json_match.group(1)
            filtered_suggestions = json.loads(json_str)
            return filtered_suggestions
        else:
            # 尝试直接解析整个响应（以防没有Markdown包装）
            try:
                return json.loads(collected_content)
            except json.JSONDecodeError:
                logging.error("无法从响应中提取JSON内容")
                return suggestion_list
    except Exception as e:
        logging.error("解析建议时出错: %s", str(e))
        return suggestion_list
