import concurrent
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from ai_agents.modules.codedoggy.agent.comment import (
    add_comment,
)
from ai_agents.modules.codedoggy.agent.review_agent import review_agent
from ai_agents.modules.codedoggy.benchmark.benchmark import benchmark
from ai_agents.modules.codedoggy.rule.config import CodeReviewConfig
from ai_agents.modules.codedoggy.server.workflow import (
    Event,
    FileReviewEvent,
    ReviewWorkflow,
)
from ai_agents.modules.codedoggy.static_check.static_check import (
    parse_static_check_errors,
    static_check,
)
from ai_agents.modules.codedoggy.utils.diff import pr_generate_extended_diff
from ai_agents.modules.codedoggy.utils.language import (
    detect_language_by_path,
    get_mr_main_language,
)


def get_context(self: "ReviewWorkflow") -> None:
    diff_path_name_status = self.repo.diff(self.event.source_commit,
                                           self.event.target_commit,
                                           name_status=True)
    if not diff_path_name_status:
        raise Exception("diff_path_list is empty")
    diff_path_name_status_arr = diff_path_name_status.split("\n")
    diff_path_list = []
    for v in diff_path_name_status_arr:
        path = v.split("\t")
        diff_path_list.append(path)
    self.diff_path_list = diff_path_list
    diff_stats = self.repo.diff_stats(self.event.source_commit,
                                      self.event.target_commit)
    self.diff_stats = diff_stats
    logging.info("diff_stats: %s", self.diff_stats)


def should_review(path: str, config: CodeReviewConfig):
    review_patterns = config.should_review_patterns
    logging.info("should_review review_patterns: %s", review_patterns)
    for pattern in review_patterns:
        if re.fullmatch(pattern, path):
            logging.info("ignore_path (regex match): %s (pattern: %s)", path, pattern)
            return True
    return False


def review_agent_process(self: "ReviewWorkflow") -> None:
    process_files_parallel(self)


def comment_agent_process(self: "ReviewWorkflow") -> None:
    add_comment(self.event, self.suggestion_result, self.static_suggestion)


def approve_process(self: "ReviewWorkflow") -> None:
    if self.event.server == "gerrit":
        if self.event.repo_config.auto_code_review_score.get("enabled", False):
            self.event.gerrit_client.set_review(
                self.event.change_num,
                self.event.revision_id,
                {
                    "labels": {
                        "Code-Review": self.event.repo_config.auto_code_review_score.get("score", 0)
                    }
                },
            )


def process_file(p: tuple, self: "ReviewWorkflow") -> None:
    """处理单个文件的线程任务"""
    editType, path = p[0], p[1]

    if not should_review(path, self.event.repo_config):
        return []

    if editType == "D":
        return []

    diff_stats = self.diff_stats.get(path, None)
    if diff_stats is None or diff_stats["insertions"] == 0:
        return []

    # if path != "pkg/feishu/constant.go":
    #     return []

    # 获取文件差异和内容（原有逻辑）
    file_diff_content = self.repo.diff_single_file(self.event.source_commit,
                                                   self.event.target_commit,
                                                   path)
    try:
        file_new_content = self.repo.show(commit_hash=self.event.target_commit,
                                          file_path=path)
    except Exception:
        file_new_content = ""
    try:
        file_original_content = self.repo.show(
            commit_hash=self.event.source_commit, file_path=path)
    except Exception:
        file_original_content = ""

    # 生成差异内容
    diff_content = pr_generate_extended_diff(
        original_file_content_str=file_original_content,
        new_file_content_str=file_new_content,
        patch=file_diff_content,
        file_path=path,
        edit_type=editType,
    )

    mr_diff_content = self.repo.diff(self.event.source_commit,
                                     self.event.target_commit)

    self.mr_diff_content = mr_diff_content

    # 创建审核事件
    file_review_event = FileReviewEvent(
        repo_path=str(self.event.repo_path),
        source_commit=self.event.source_commit,
        target_commit=self.event.target_commit,
        file_path=os.path.join(str(self.event.repo_path), path),
        diff_content=diff_content,
        mr_diff_content=mr_diff_content,
        file_content=file_new_content,
        language=detect_language_by_path(path),
        server=self.event.server,
        project_id=self.event.project_id,
        repo_config=self.event.repo_config,
    )
    file_review_event.event_id = (
        self.event.change_num
        if self.event.server == "gerrit"
        else self.event.merge_request_id
    )
    logging.info("file_review_event: %s", file_review_event)
    agent_result = review_agent(self.event, file_review_event)
    logging.info("agent_result: %s", agent_result)
    try:
        parsed_result = (json.loads(agent_result) if isinstance(agent_result, str) else agent_result
        )
        if not isinstance(parsed_result, list):
            parsed_result = [parsed_result]
        return parsed_result
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON string: %s", e)
        return []
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        return []


def process_files_parallel(self) -> List[Dict]:
    # 创建线程池，限制最大并发数为4
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 提交所有文件处理任务到线程池
        future_to_path = {
            executor.submit(process_file, p, self): p for p in self.diff_path_list
        }

        # 收集结果
        suggestion_result = []
        for future in concurrent.futures.as_completed(future_to_path):
            try:
                result = future.result()
                if result:
                    suggestion_result.extend(result)
            except Exception as e:
                path = future_to_path[future]
                logging.error("处理文件 %s 时发生错误: %s", path, e)

        self.suggestion_result = suggestion_result
        return suggestion_result


def workspace_prepare(self):
    """
    将仓库替换为target commit，为grep工具提供搜索环境
    """
    try:
        self.repo.checkout(self.event.target_commit)
        os.chdir(self.event.repo_path)
    except Exception as e:
        logging.error("workspace_prepare error: %s", e)
        self.repo.checkout("origin")
    return


def static_check_process(self: "ReviewWorkflow"):
    """
    基于 diff 文件判断主要语言
    对其 diff 进行静态检查
    """
    language = get_mr_main_language(self.diff_path_list)
    logging.info("language %s", language)
    static_err = static_check(
        language,
        self.event.repo_path,
        self.event.source_commit,
        self.event.target_commit,
    )
    logging.info("static check error %s", static_err)
    err_list = parse_static_check_errors(language, static_err)
    logging.info("static check error list %s", err_list)
    if err_list:
        self.static_suggestion = err_list
    else:
        self.static_suggestion = []

def brench_mark_process(self: "ReviewWorkflow"):
    new_suggestion_list = []
    for suggestion in self.suggestion_result:
        if self.event.score_enable and suggestion.get("score", 0) <  self.event.suggestion_min_score:
            continue
        new_suggestion_list.append(suggestion)

    benchmark(self.event, new_suggestion_list , self.mr_diff_content)


workflow_steps = [
    workspace_prepare,
    get_context,
    static_check_process,
    review_agent_process,
    comment_agent_process,
    approve_process,
]

benchmark_steps = [
    workspace_prepare,
    get_context,
    static_check_process,
    review_agent_process,
    brench_mark_process,
]


def generate_code_review_suggestions_count(diff_stat: str):
    insertions, deletions, _ = diff_stat.split("\t", 2)
    total_changes = int(insertions) + int(deletions)
    return total_changes // 100 + 1


def handler(event: Event) -> None:
    """
    处理事件的异步函数，使用ReviewWorkflow执行工作流

    由于workflow.execute_workflow是异步方法，这里使用异步上下文管理器
    确保正确处理同步和异步工作流步骤
    """
    benchmark = os.getenv('benchmark')
    review_workflow_steps = workflow_steps if not benchmark else benchmark_steps
    with ReviewWorkflow(event=event, workflow_steps=review_workflow_steps) as workflow:
        workflow.execute_workflow()
