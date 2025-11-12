"""review agent"""

import logging
import json
import traceback
import os
from datetime import datetime

from ai_agents.core import runtime
from ai_agents.lib.tracing import generate_task_id, task_context
from ai_agents.lib.smolagents import new_agent_logger, LogLevel
from ai_agents.modules.codedoggy.agent.model import (
    create_model_config_from_env,
)
from ai_agents.modules.codedoggy.agent.prompts.prompt import load_prompt
from ai_agents.modules.codedoggy.agent.score import review_final_answer_check
from ai_agents.modules.codedoggy.agent.validation import validate_review_result_format
from ai_agents.modules.codedoggy.server.workflow import Event, FileReviewEvent
from ai_agents.supervisor_agents.codereview.agent import (
    CodeReviewSupervisorAgent,
)
from pathlib import Path

runtime.app="CodeDoggy"

def cleanup_review_files_by_task_id(sub_task_id: str):
    """
    根据sub_task_id清理agent生成的中间文件

    文件名格式: task_codedoggy:gerrit:1433260:review_18ac174f4f32_content.json

    Args:
        sub_task_id: 任务ID，用于匹配对应的文件进行清理
    """
    try:
        # 审查内容文件缓存目录
        cache_dir = Path.home() / ".cache" / "codeDoggy" / "review_content"

        if not cache_dir.exists():
            logging.debug("审查缓存目录不存在，无需清理")
            return

        cleaned_count = 0

        # 根据sub_task_id匹配文件进行清理
        # 文件名格式: {sub_task_id}_content.json
        target_pattern = f"{sub_task_id}_content.json"

        for file_path in cache_dir.iterdir():
            try:
                if file_path.is_file() and file_path.name == target_pattern:
                    # 删除文件
                    file_path.unlink()
                    cleaned_count += 1
                    logging.info(f"已清理审查文件: {file_path.name}")

            except Exception as file_error:
                logging.error(f"清理文件 {file_path.name} 时出错: {file_error}")

        if cleaned_count > 0:
            logging.info(f"清理完成: 删除了 {cleaned_count} 个文件")
        else:
            logging.debug(f"未找到需要清理的文件: {target_pattern}")

    except Exception as e:
        logging.error(f"执行审查文件清理时发生错误: {e}")

def create_agent_log_filename(task_id: str = None) -> str:
    """
    创建带时间戳和任务ID的agent日志文件名，保存在当前文件所在目录

    Args:
        task_id: 可选的任务ID，用于确保并行任务的日志文件唯一性

    Returns:
        str: 日志文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 包含毫秒，确保唯一性
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if task_id:
        # 使用任务ID的后8位作为文件名的一部分，确保并行任务的唯一性
        task_suffix = task_id.split("_")[-1][:8] if "_" in task_id else task_id[:8]
        log_filename = f"code_review_agent_{timestamp}_{task_suffix}.log"
    else:
        log_filename = f"code_review_agent_{timestamp}.log"

    return os.path.join(current_dir, log_filename)


def get_review_custom_rules(event: FileReviewEvent) -> list:
    """
    获取代码审查的自定义规则，包括默认规则和配置中的规则

    Args:
        event: 文件审查事件

    Returns:
        list: 合并后的自定义规则列表
    """
    # 默认规则
    default_rules = [
        "只对新增代码进行审查，不要审查未修改的代码，更不要解释代码！",
        "所有描述相关内容都使用中文输出"
    ]

    # 获取配置中的自定义规则
    config_rules = []
    if event.repo_config.custom_rules.get("enabled", False):
        config_rules = event.repo_config.custom_rules.get("rules", [])

    # 合并默认规则和配置规则
    all_rules = default_rules + config_rules
    return all_rules


def format_custom_rules_to_string(custom_rules: list) -> str:
    """
    将自定义规则列表格式化为字符串

    Args:
        custom_rules: 自定义规则列表

    Returns:
        str: 格式化后的规则字符串
    """
    if not custom_rules:
        return ""

    formatted_rules = []
    for i, rule in enumerate(custom_rules, 1):
        formatted_rules.append(f"{i}. {rule}")

    return "\n".join(formatted_rules)


def logic_review_agent(event: FileReviewEvent):
    model = create_model_config_from_env(event.repo_config.model)
    trace_name_arr = (
        ["codedoggy", event.server, event.event_id, "review"]
        if event.server == "gerrit"
        else ["codedoggy", event.server, event.project_id, event.event_id, "review"]
    )
    trace_name = ":".join(trace_name_arr)
    sub_task_id = generate_task_id(trace_name)
    custom_rules = get_review_custom_rules(event)

    # 创建带文件日志的AgentLogger
    log_file_path = None
    if os.getenv('DRY_RUN'):
        log_file_path = create_agent_log_filename(sub_task_id)
    agent_logger = new_agent_logger(log_file_path=log_file_path, level=LogLevel.INFO)

    with task_context(sub_task_id):
        try:
            task = load_prompt(
                "review",
                repo_path=event.repo_path,
                file_path=os.path.join(event.repo_path, event.file_path),
                source_commit=event.source_commit,
                target_commit=event.target_commit,
                diff_content=event.diff_content,
                mr_diff_content=event.mr_diff_content,
                file_content=event.file_content,
                suggestion_count=event.suggestion_count,
                custom_rule=custom_rules,
            )

            agent = CodeReviewSupervisorAgent(
                project_path=event.repo_path,
                model=model,
                logger=agent_logger,  # 传递文件日志记录器
                agent_tool_template_vars={
                    "rules" : format_custom_rules_to_string(custom_rules),
                },
                final_answer_checks=[validate_review_result_format]
            )
            res = agent.run(task=task, task_id=sub_task_id)
            logging.info("review agent raw: %s", res)
            return res
        finally:
            # 任务完成后清理对应的审查内容文件
            try:
                cleanup_review_files_by_task_id(sub_task_id)
            except Exception as cleanup_error:
                # 清理失败不影响主要业务流程，只记录错误日志
                logging.warning(f"清理审查文件时出错: {cleanup_error}")


def process_relevant_file_paths(review_result, repo_path: str):
    """
    处理审查结果中的 relevantFile 字段，将绝对路径转换为相对路径
    支持处理JSON字符串格式和list格式的输入

    Args:
        review_result: 审查结果，可能是list或JSON字符串
        repo_path: 仓库路径

    Returns:
        处理后的审查结果，保持原有格式
    """

    if not review_result or not repo_path:
        return review_result

    # 判断输入格式并解析
    if isinstance(review_result, str):
        try:
            parsed_result = json.loads(review_result)
        except (json.JSONDecodeError, TypeError):
            return review_result
    else:
        # 已经是list格式
        parsed_result = review_result

    # 处理结果
    if not isinstance(parsed_result, list):
        return review_result

    processed_result = []
    for item in parsed_result:
        if isinstance(item, dict) and "relevantFile" in item:
            relevant_file = item.get("relevantFile", "")
            if relevant_file and relevant_file.startswith(repo_path):
                # 移除 repo_path 前缀，保留相对路径
                relative_path = relevant_file[len(repo_path):].lstrip("/\\")
                item = item.copy()  # 创建副本避免修改原始数据
                item["relevantFile"] = relative_path
        processed_result.append(item)
    return processed_result


def review_agent(event: Event, review_event: FileReviewEvent) -> list:
    result = []
    try:
        review_result = logic_review_agent(review_event)

        if review_result and len(review_result) > 0:
            if event.score_enable:
                result = review_final_answer_check(review_result, review_event)
            else:
                result = review_result

            result = process_relevant_file_paths(result, review_event.repo_path)

        logging.info("review agent result: %s", result)
    except Exception as e:
        # 获取完整的异常信息，包括具体的错误位置
        exc_info = traceback.format_exc()
        logging.error("review agent error: %s", e)
        logging.error("详细错误堆栈:\n%s", exc_info)
    return result
