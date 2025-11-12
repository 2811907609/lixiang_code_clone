#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coverity 静态分析工具模块。

该模块提供了完整的 Coverity 静态分析工作流，包括执行分析、问题比较和修复状态判定。
主要用于静态缺陷修复场景中的自动化分析和验证。

核心功能：
    - 执行 Coverity 静态分析命令
    - 比较修复前后的问题列表，识别新增、已修复和误修复的问题
    - 基于内容哈希和上下文信息准确判定特定问题的修复状态
    - 生成详细的分析报告和修复结果说明

主要组件：
    - execute_analyse_command(): 执行 Coverity 分析的主要接口
    - 集成 judge_issue_existed 模块进行问题状态判定
    - 集成 diff_issues 模块进行问题差异比较

环境依赖：
    - 需要设置相关环境变量（WORK_DIR, AGENT_DIR, RAW_ALL_ERRORS_JSONPATH 等）
    - 依赖外部 Coverity 分析脚本（默认 cov_improve_0928.sh）
    - 使用系统命令执行而非直接导入 subprocess 模块

注意事项：
    - 分析过程会切换工作目录，需要确保环境配置正确
    - 生成的分析结果会写入指定的 JSON 文件中
    - 支持超时控制和错误处理机制
"""

import json
import os
import time
from typing import Dict, Any
from sysutils.xos import change_dir
from ai_agents.supervisor_agents.detected_static_repair.judge_issue_existed import judge_issues_existed, diff_issues,load_issues_from_file,get_content_hash_key_2_issue_dict

def execute_analyse_command(
    mergeKey: str,
    # command: str = ". ./cov.sh",
    command: str = ". ./cov_improve_0928.sh",
    work_dir: str = os.environ["WORK_DIR"],
    agent_dir: str = os.environ["AGENT_DIR"],
    raw_all_errors_jsonpath: str = os.environ["RAW_ALL_ERRORS_JSONPATH"],
    timeout_seconds: float = 600.0
) -> Dict[str, Any]:
    """
    执行Coverity分析命令

    Args:
        mergeKey: 要分析的issue的mergeKey
        command: 执行的命令，默认 "./cov_improve_0928.sh"
        work_dir: 工作目录
        agent_dir: 智能体目录，执行command
        raw_all_errors_jsonpath: 修复前的Coverity扫描报警列表信息
        timeout_seconds: 命令执行超时时间

    Returns:
        Dict[str, Any]: 包含以下字段的字典
            - bool_cur_issue_fixed (bool): 当前mergeKey是否被解决，True表示已修复，False表示未修复
            - new_issue_list (List[str]): 新增issue的mergeKey列表，表示修复过程中引入的新问题
            - missing_issue_list (List[str]): 因解决当前mergeKey同时解决的其他mergeKey列表，表示一并修复的问题
            - execution_time (float): 命令执行时间，单位为秒
            - coverity_output_path (str): Coverity分析结果文件路径，指向new_errors_full.json
            - error_message (str): 错误信息，执行成功时为空字符串
            - explain_of_bool_issue_existed (str): 对issue是否存在判定结果的详细解释说明
    """
    # agent_dir = "/home/chehejia/programs/lixiang/cov-evalution/agent"
    raw_content_hash_key_2_issue_dict_jsonpath=os.environ["RAW_CONTENT_HASH_KEY_2_ISSUE_DICT_JSONPATH"]
    new_content_hash_key_2_issue_dict_jsonpath=os.environ["NEW_CONTENT_HASH_KEY_2_ISSUE_DICT_JSONPATH"]

    result = {
        "bool_cur_issue_fixed": False,
        "new_issue_list": [],
        "missing_issue_list": [],
        "execution_time": 0.0,
        "coverity_output_path": "",
        "error_message": "",
        "explain_of_bool_issue_existed": ""
    }

    start_time = time.time()
    print(f"Executing Coverity analysis in {agent_dir} with command: {command}")
    with change_dir(agent_dir):
        # 将命令的执行输出信息写到指定文件tmp.log
        # # os.system(f"{command} > /home/chehejia/programs/lixiang/cov-evalution/mvbs/logs/tmp.log 2>&1")
        # cov_dir=os.environ['COV_DIR']
        # os.system(f"rm -rf {work_dir}/out")
        # os.system(f"rm -rf {cov_dir}")

        os.system(f"{command} > {os.environ['COVERITY_ANALYSE_LOGPATH']} 2>&1")
    print(f'execute_analyse_command completed, output written to {os.environ["COVERITY_ANALYSE_LOGPATH"]}')
    # Coverity分析结果文件路径
    new_all_errors_jsonpath = os.path.join(work_dir, "new_errors_full.json")
    result["coverity_output_path"] = new_all_errors_jsonpath

    # 检查分析结果文件是否生成
    if not os.path.exists(new_all_errors_jsonpath):
        error_msg=f"Coverity analysis output file not found: {new_all_errors_jsonpath}"
        raise ValueError(error_msg)

    # # 判断当前mergeKey是否被修复
    # 加载原始错误文件和新错误文件的issues
    raw_issues = load_issues_from_file(filepath=raw_all_errors_jsonpath)
    new_issues = load_issues_from_file(filepath=new_all_errors_jsonpath)
    # print(f'raw_issues: {len(raw_issues)}')

    if os.path.exists(raw_content_hash_key_2_issue_dict_jsonpath):
        with open(raw_content_hash_key_2_issue_dict_jsonpath, 'r') as f:
            raw_content_hash_key_2_issue_dict = json.load(f)
    else:
        raw_content_hash_key_2_issue_dict=get_content_hash_key_2_issue_dict(all_errors_jsonpath=raw_all_errors_jsonpath,work_dir=work_dir)
    new_content_hash_key_2_issue_dict=get_content_hash_key_2_issue_dict(all_errors_jsonpath=new_all_errors_jsonpath,work_dir=work_dir)
    raw_mergeKey_list = [issue.get('mergeKey') for issue in raw_issues if issue.get('mergeKey')]
    new_mergeKey_list = [issue.get('mergeKey') for issue in new_issues if issue.get('mergeKey')]
    print(f'raw_mergeKey_list mergeKey数量={len(raw_mergeKey_list)},new_mergeKey_list mergeKey数量={len(new_mergeKey_list)}')
    # 获取原始issue的详细信息
    with open(raw_all_errors_jsonpath, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    target_issue = None
    for issue in raw_data.get('issues', []):
        if issue.get('mergeKey') == mergeKey:
            target_issue = issue
            break
    assert target_issue is not None, f"AssertError 未找到mergeKey={mergeKey}的issue"

    if target_issue:
        bool_issue_existed,explain_of_bool_issue_existed=judge_issues_existed(
            issue_in=target_issue,
            raw_content_hash_key_2_issue_dict=raw_content_hash_key_2_issue_dict,
            new_content_hash_key_2_issue_dict=new_content_hash_key_2_issue_dict,
            raw_mergeKey_list=raw_mergeKey_list,
            new_mergeKey_list=new_mergeKey_list,
            work_dir=work_dir
        )
        if not os.path.exists(raw_content_hash_key_2_issue_dict_jsonpath):
            with open(raw_content_hash_key_2_issue_dict_jsonpath, 'w', encoding='utf-8') as fw:
                json.dump(raw_content_hash_key_2_issue_dict, fw, indent=4, ensure_ascii=False)
            print(f'写入raw_content_hash_key_2_issue_dict_jsonpath={raw_content_hash_key_2_issue_dict_jsonpath},写入数量={len(raw_content_hash_key_2_issue_dict)}')
        with open(new_content_hash_key_2_issue_dict_jsonpath, 'w', encoding='utf-8') as fw:
            json.dump(new_content_hash_key_2_issue_dict, fw, indent=4, ensure_ascii=False)
        print(f'写入new_content_hash_key_2_issue_dict_jsonpath={new_content_hash_key_2_issue_dict_jsonpath},写入数量={len(new_content_hash_key_2_issue_dict)}')

        # 更新修复状态（True表示不存在即已修复，False表示存在即未修复）
        result["bool_cur_issue_fixed"] = not bool_issue_existed
        result["explain_of_bool_issue_existed"] = explain_of_bool_issue_existed

    # 获取新增和已解决的issues列表
    # try:
    print('on diff_issues')
    new_issues, missing_issues = diff_issues(
        raw_all_errors_jsonpath=raw_all_errors_jsonpath,
        new_all_errors_jsonpath=new_all_errors_jsonpath,
        raw_content_hash_key_2_issue_dict_jsonpath=raw_content_hash_key_2_issue_dict_jsonpath,
        work_dir=work_dir
    )
    # print(f'under diff_issues')

    result["new_issue_list"] = [issue.get('mergeKey', '') for issue in new_issues]
    result["missing_issue_list"] = [issue.get('mergeKey', '') for issue in missing_issues]


    result["execution_time"] = time.time() - start_time

    print(f"Analysis completed in {result['execution_time']:.2f}s")
    print(f"Current issue fixed: {result['bool_cur_issue_fixed']}")
    print(f"explain_of_bool_issue_existed: {result['explain_of_bool_issue_existed']}")
    print(f"New issues: {len(result['new_issue_list'])}")
    print(f"Missing issues: {len(result['missing_issue_list'])}")

    return result
