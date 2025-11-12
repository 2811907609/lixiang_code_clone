#!/usr/bin/env python3
"""
HaloOS Ceedling 单元测试智能体使用示例

演示如何使用 HaloOSUnitTestSupervisorAgent 为 HaloOS 项目创建 Ceedling 单元测试工程。
该智能体会协调多个微智能体完成测试工程的创建和验证。
"""

import os
import sys
import json
import fire
from pathlib import Path
import arrow
import ai_agents.lib.tracing # noqa: F401
from sysutils.xos import change_dir
from ai_agents.lib.smolagents import new_agent_logger, LogLevel
from ai_agents.lib.tracing import generate_task_id
from ai_agents.supervisor_agents.detected_static_repair.agent import DetectedStaticRepairAgent
from ai_agents.tools.vendor_tools import ensure_all_tools
from ai_agents.supervisor_agents.detected_static_repair.judge_issue_existed import get_content_hash_key_2_issue_dict


LLM_API_BASE=os.environ['LLM_API_BASE']
LOG_DIRPATH=os.environ['LOG_DIRPATH']
print(f'LLM_API_BASE={LLM_API_BASE}')
log_to_file=True
now = arrow.now()
if log_to_file:
    # time_str = now.format('YYYY-MM-DD_HH_mm')
    time_str = now.format('YYYY-MM-DD_HH')
    ##todo
    # log_file_path = Path('./logs') / f'task_{time_str}.log'
    # logdirpath="/home/chehejia/programs/lixiang/code-complete/codebuddy/ai_agents/examples/logs"
    log_file_path = Path(LOG_DIRPATH) / f'tasks/task_{time_str}.log'
    log_file_path.write_text('\n')
else:
    log_file_path = None

agent_logger = new_agent_logger(log_file_path, level=LogLevel.DEBUG)

def create_static_detection_repair(workdir):
    # print(f'before chdir workdir={workdir}')
    # os.chdir(workdir)
    # print(f'after chdir workdir={workdir}')
    config = {
            "timeout_seconds": 1800.0,
            "validate_commands": True,
            "allow_dangerous_commands": True
        }
    ensure_all_tools()
    raw_content_hash_key_2_issue_dict_jsonpath=os.environ["RAW_CONTENT_HASH_KEY_2_ISSUE_DICT_JSONPATH"]
    raw_all_errors_jsonpath: str = os.environ["RAW_ALL_ERRORS_JSONPATH"]
    work_dir=os.environ["WORK_DIR"]
    print(f'before chdir workdir={workdir}')
    with change_dir(workdir):
        print(f'after chdir workdir={workdir}')
        raw_content_hash_key_2_issue_dict=get_content_hash_key_2_issue_dict(all_errors_jsonpath=raw_all_errors_jsonpath,work_dir=work_dir)
        with open(raw_content_hash_key_2_issue_dict_jsonpath, 'w', encoding='utf-8') as fw:
            json.dump(raw_content_hash_key_2_issue_dict, fw, indent=4, ensure_ascii=False)
            print(f'in create_static_detection_repair 写入raw_content_hash_key_2_issue_dict_jsonpath={raw_content_hash_key_2_issue_dict_jsonpath},写入数量={len(raw_content_hash_key_2_issue_dict)}')

        supervisor=DetectedStaticRepairAgent(logger=agent_logger,execution_env_config=config)
        PROMPT_PATH=os.environ['PROMPT_PATH']
        task_content=f"""Coverity warning info filepath:\n {PROMPT_PATH}"""
        task_id = generate_task_id()
        supervisor.run(task_content, task_id=task_id)
    print(f'after exit change workdir={workdir}')

    return True
def cli_create_task(workdir):
    """
    命令行接口函数，用于创建 HaloOS 单元测试工程。
    fire库会自动将此函数的参数映射为命令行参数。

    Args:
        haloos_path: HaloOS 项目路径 (位置参数)
        powerful: 是否使用强大模型 (例如 --powerful)
        task_id: 自定义任务ID (例如 --task-id "my_id")
    """
    # 调用核心创建逻辑
    success = create_static_detection_repair(workdir=workdir)

    # 根据创建结果打印提示信息
    if success:
        print("\n✅ 任务执行成功！")

    else:
        print("\n❌ 任务执行失败")
        sys.exit(1)


if __name__ == "__main__":
    fire.Fire(cli_create_task)
