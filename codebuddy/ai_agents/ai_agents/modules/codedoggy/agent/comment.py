import logging
import time

from ai_agents.modules.codedoggy.server.workflow import Event
from ai_agents.modules.codedoggy.utils.telemetry import (
    telemetry_suggestion_list,
)


def format_suggestion_message(
    improved_code: str,
    suggestion_content: str,
    label: str,
    score: int,
) -> str:
    """
    Suggestions for formatting the generated code platform
    Args:
      improvedCode : str
      suggestionContent :str
      label:str
      score:int
    Returns:
      str
    """
    result = f"""
**1. 建议**: {suggestion_content}
**2. 标签** : {label}
**3. 改进代码**:
```
{improved_code}
```
"""
    if score != -1:
        result += f"\n **4. 分数**: {score}"
    return result


def sort_suggestions_by_score(suggestion_list: list[dict]) -> list[dict]:
    """
    根据 score 从高到低对建议列表进行排序
    Args:
        suggestion_list: 建议列表
    Returns:
        排序后的建议列表
    """
    # 过滤掉 None 值，然后按 score 排序
    filtered_list = [s for s in suggestion_list if s is not None]
    return sorted(filtered_list, key=lambda x: x.get("score", 0), reverse=True)


def add_comment(
    event: Event, suggestion_list: list[dict], static_suggestion: list[dict]
) -> None:
    if not suggestion_list:
        return

    # 根据 score 从高到低排序
    if event.score_enable:
        sorted_suggestions = sort_suggestions_by_score(suggestion_list)
    else:
        sorted_suggestions = suggestion_list
    max_comments = event.repo_config.max_comments
    new_suggestion_list = []
    for suggestion in sorted_suggestions:
        # 达到最大评论数量限制时停止
        if len(new_suggestion_list) >= max_comments:
            break
        # 过滤低分建议
        if event.score_enable and suggestion.get("score", 0) < event.suggestion_min_score:
            continue

        suggestion["message"] = format_suggestion_message(
            suggestion.get("improvedCode", ""),
            suggestion.get("suggestionContent", ""),
            suggestion.get("label", ""),
            suggestion.get("score", -1),
        )
        new_suggestion_list.append(suggestion)
    new_suggestion_list.extend(static_suggestion)
    valid_comment = sync_comment_by_api(event, new_suggestion_list)
    telemetry_suggestion_list(event, valid_comment)
    return


def sync_comment_by_api(event: Event, suggestion_list: list) -> list:
    if event.server == "gerrit":
        return sync_comment_to_gerrit(event, suggestion_list)
    return sync_comment_to_gitlab(event, suggestion_list)


def sync_comment_to_gerrit(event: Event, suggestion_list: list) -> None:
    change_num = event.change_num
    revision_id = event.revision_id
    valid_comments = []
    for suggestion in suggestion_list:
        logging.info("suggestion: %s", suggestion)
        message = suggestion.get("message", "")
        line = suggestion.get("suggestionLine", "")
        path = suggestion.get("relevantFile", "")
        try:
            event.gerrit_client.create_draft(
                change_num,
                revision_id,
                {
                    "message": message,
                    "line": line,
                    "path": path,
                    "unresolved": True,
                },
            )
            valid_comments.append(suggestion)
        except Exception as e:
            logging.error("Failed to create draft: %s", e)
        time.sleep(1)
    event.gerrit_client.set_review(change_num, revision_id,
                                         {"drafts": "PUBLISH_ALL_REVISIONS"})
    return valid_comments


def sync_comment_to_gitlab(event: Event, suggestion_list: list) -> None:
    valid_comments = []
    for suggestion in suggestion_list:
        message = suggestion.get("message", "")
        line = suggestion.get("suggestionLine", "")
        path = suggestion.get("relevantFile", "")
        position = {
            "base_sha": event.base_sha,
            "start_sha": event.start_sha,
            "head_sha": event.head_sha,
            "position_type": "text",
            "new_path": path,
            "new_line": line,
        }
        try:
            event.gitlab_client.add_note_to_discussion(
                event.merge_request_id, event.project_id, message, position
            )
            valid_comments.append(suggestion)
        except Exception as e:
            logging.error("comment agent error: %s", e)
        time.sleep(1)
    return valid_comments
