# -*- coding: utf-8 -*-
"""
根据内容判定issue是否存在

实现judge_issues_existed函数，用于判断指定的issue是否存在于给定的错误列表中。
"""

import json
import os
from typing import Tuple

def concat_hash_key(stripped_main_event_filepathname,main_event_line_number_in,checkerName,work_dir):
    code_filepath=os.path.join(work_dir,stripped_main_event_filepathname)
    # if os.path.exists(code_filepath):
    with open(code_filepath, 'r') as f:
        lines = f.readlines()
        try:
            dest_code_line=lines[main_event_line_number_in-1]
        except IndexError:
            raise ValueError(f'concat_hash_key mainEventLineNumber={main_event_line_number_in},code_filepath={code_filepath}')
        content_hash_key=stripped_main_event_filepathname+'-'+dest_code_line+'-'+checkerName
        content_hash_key=content_hash_key.replace('\n','').replace('\r','').replace('\t','').replace(' ','')
    return content_hash_key

def get_content_hash_key_2_issue_dict(all_errors_jsonpath,work_dir):
    """
    从JSON文件加载issues列表

    Args:
        filepath: JSON文件路径

    Returns:
        list: issues列表，如果文件不存在或解析失败则返回空列表
    """
    if not os.path.exists(all_errors_jsonpath):
        # return []
        raise ValueError(f'all_errors_jsonpath={all_errors_jsonpath}不存在')

    # try:
    with open(all_errors_jsonpath, 'r') as f:
        data = json.load(f)
    issues=data.get('issues', [])
    content_hash_key_2_issue_dict={}
    for issue in issues:
        stripped_main_event_filepathname=issue['strippedMainEventFilePathname']
        checkerName=issue['checkerName']
        main_event_line_number_in=issue['mainEventLineNumber']
        extra=issue['extra']
        # mergeKey=issue['mergeKey']
        code_filepath=os.path.join(work_dir,stripped_main_event_filepathname)
        ##todo modify 临时方案
        if '_fixed' in code_filepath.replace('.c','').replace('.h',''):
            continue
        if not os.path.exists(code_filepath):
            print(f'code_filepath={code_filepath}不存在')
        # if os.path.exists(code_filepath):
        ## for check begin
        with open(code_filepath, 'r') as f:
            lines = f.readlines()
            # print(f'mainEventLineNumber={mainEventLineNumber},code_filepath={code_filepath}')
            try:
                dest_code_line=lines[main_event_line_number_in-1]
            except IndexError:
                raise ValueError(f'IndexError mainEventLineNumber={main_event_line_number_in},code_filepath={code_filepath}')
            try:
                assert extra in dest_code_line
            except AssertionError:
                # print_msg=f'code_filepath={code_filepath},\nmergeKey={mergeKey},\nmainEventLineNumber={mainEventLineNumber},extra={extra},dest_code_line={dest_code_line}'
                # # print(print_msg)
                pass
        ## for check end
        content_hash_key=concat_hash_key(stripped_main_event_filepathname=stripped_main_event_filepathname,
                                         main_event_line_number_in=main_event_line_number_in,
                                         checkerName=checkerName,
                                         work_dir=work_dir)
        content_hash_key_2_issue_dict[content_hash_key]=issue
    return content_hash_key_2_issue_dict

def judge_issues_existed(
    issue_in,
    raw_content_hash_key_2_issue_dict,
    new_content_hash_key_2_issue_dict,
    raw_mergeKey_list,
    new_mergeKey_list,
    work_dir="/home/chehejia/programs/lixiang/cov-evalution/mvbs"
)-> Tuple[bool,str]:
    """
    判定静态分析issue是否在修复后仍然存在

    通过比较修复前后的mergeKey和content_hash_key来判断特定issue是否已被修复。
    采用双重检查机制：首先检查mergeKey是否存在，然后检查content_hash_key是否存在。

    检查流程：
    1. 验证输入issue的mergeKey在原始列表中存在
    2. 检查mergeKey是否仍在新的扫描结果中存在
    3. 如果mergeKey不存在，进一步检查content_hash_key是否存在
    4. 返回判定结果和详细说明

    Args:
        issue_in (dict): 待检查的issue对象，包含mergeKey、strippedMainEventFilePathname、
                        mainEventLineNumber、checkerName等字段
        raw_content_hash_key_2_issue_dict (dict): 原始扫描结果的content_hash_key到issue的映射字典
        new_content_hash_key_2_issue_dict (dict): 新扫描结果的content_hash_key到issue的映射字典
        raw_mergeKey_list (list): 原始扫描结果中的mergeKey列表
        new_mergeKey_list (list): 新扫描结果中的mergeKey列表
        work_dir (str, optional): 工作目录路径，用于构建content_hash_key。
                                 默认为"/home/chehejia/programs/lixiang/cov-evalution/mvbs"

    Returns:
        Tuple[bool, str]: 返回判定结果和说明
            - bool: True表示issue仍然存在（未修复），False表示issue已修复
            - str: 详细说明，包含具体的检查结果和相关统计信息

    Raises:
        AssertionError: 当输入的mergeKey不在raw_mergeKey_list中时抛出
        KeyError: 当issue_in缺少必要字段时可能抛出

    Example:
        >>> issue = {
        ...     'mergeKey': 'ABC123',
        ...     'strippedMainEventFilePathname': 'src/main.c',
        ...     'mainEventLineNumber': 42,
        ...     'checkerName': 'NULL_RETURNS'
        ... }
        >>> exists, msg = judge_issues_existed(
        ...     issue, raw_dict, new_dict, raw_keys, new_keys
        ... )
        >>> print(f"Issue存在: {exists}, 说明: {msg}")

    Note:
        - 该函数是静态分析修复验证流程的核心组件
        - mergeKey检查优先级高于content_hash_key检查
        - content_hash_key基于文件路径、行号和检查器名称动态生成
        - 返回的说明信息包含中文描述，便于调试和日志记录
    """

    # mergeKey_list = [issue.get('mergeKey') for issue in issues_list if issue.get('mergeKey')]
    mergeKey_in=issue_in['mergeKey']
    stripped_main_event_filepathname=issue_in['strippedMainEventFilePathname']
    main_event_line_number_in=issue_in['mainEventLineNumber']
    checkerName_in=issue_in['checkerName']
    assert mergeKey_in in raw_mergeKey_list,print(f'AssertError mergeKey_in not in raw_mergeKey_list,mergeKey_in={mergeKey_in},raw_mergeKey_list数量={len(raw_mergeKey_list)}')
    if mergeKey_in in new_mergeKey_list:
        return True,f"not fix explain:mergeKey={mergeKey_in}仍然存在于扫描后的文件内，new_mergeKey_list数量={len(new_mergeKey_list)}"

    content_hash_key_in=concat_hash_key(stripped_main_event_filepathname=stripped_main_event_filepathname,
                                main_event_line_number_in=main_event_line_number_in,
                                checkerName=checkerName_in,
                                work_dir=work_dir)
    # 动态的content_hash_key_in随时变化，随着修改代码
    # assert content_hash_key_in in raw_content_hash_key_2_issue_dict.keys(),print(f'content_hash_key_in={content_hash_key_in},不在raw_content_hash_key_2_issue_dict，数量={len(raw_content_hash_key_2_issue_dict)},new_content_hash_key_2_issue_dict数量={len(new_content_hash_key_2_issue_dict)}')
    if content_hash_key_in in new_content_hash_key_2_issue_dict.keys():
        return True,f"not fix explain:content_hash_key_in={content_hash_key_in}仍然存在于扫描后的文件内,new_content_hash_key_2_issue_dict数量={len(new_content_hash_key_2_issue_dict)}"
    return False,f"fix explain:content_hash_key_in={content_hash_key_in}不存在于扫描后的文件内"



def load_issues_from_file(filepath):
    """
    从JSON文件加载issues列表

    Args:
        filepath: JSON文件路径

    Returns:
        list: issues列表，如果文件不存在或解析失败则返回空列表
    """
    if not os.path.exists(filepath):
        return []
    # try:
    with open(filepath, 'r') as f:
        data = json.load(f)
    issues=data.get('issues', [])
    print(f'load_issues_from_file读取路径={filepath},读取数量={len(issues)}')
    return issues
    # except Exception as e:
    #     print("加载文件 '{}' 错误: {}".format(filepath, e))
    #     return []


def get_issue_info_by_merge_key(mergeKey, filepath):
    """
    根据mergeKey从JSON文件中获取issue信息

    Args:
        mergeKey: 要查找的mergeKey
        filepath: JSON文件路径

    Returns:
        dict: issue信息，如果未找到则返回None
    """
    issues = load_issues_from_file(filepath)

    for issue in issues:
        if issue.get('mergeKey') == mergeKey:
            return issue

    return None


def diff_issues(raw_all_errors_jsonpath, new_all_errors_jsonpath, raw_content_hash_key_2_issue_dict_jsonpath,work_dir):
    """
    比较两个错误文件，找出新增和缺失的issues

    Args:
        raw_all_errors_jsonpath: 原始错误JSON文件路径
        all_errors_jsonpath: 新的错误JSON文件路径
        work_dir: 工作目录，默认为预定义路径
        raw_content_hash_key_2_issue_dict_jsonpath: 原始错误JSON文件中content_hash_key_2_issue_dict.json路径
    Returns:
        tuple: (new_issue_list, missing_issue_list)
            new_issue_list: 新增的issues列表
            missing_issue_list: 缺失的issues列表
    """
    new_issue_list = []
    missing_issue_list = []

    # 加载原始错误文件和新错误文件的issues
    raw_issues = load_issues_from_file(raw_all_errors_jsonpath)
    new_issues = load_issues_from_file(new_all_errors_jsonpath)
    print(f'raw_issues: {len(raw_issues)}')
    if os.path.exists(raw_content_hash_key_2_issue_dict_jsonpath):
        with open(raw_content_hash_key_2_issue_dict_jsonpath, 'r') as f:
            raw_content_hash_key_2_issue_dict = json.load(f)
    else:
        raw_content_hash_key_2_issue_dict=get_content_hash_key_2_issue_dict(all_errors_jsonpath=raw_all_errors_jsonpath,work_dir=work_dir)
    new_content_hash_key_2_issue_dict=get_content_hash_key_2_issue_dict(all_errors_jsonpath=new_all_errors_jsonpath,work_dir=work_dir)
    raw_mergeKey_list = [issue.get('mergeKey') for issue in raw_issues if issue.get('mergeKey')]
    new_mergeKey_list = [issue.get('mergeKey') for issue in new_issues if issue.get('mergeKey')]


    # 1. 检查原始issues中哪些在新文件中缺失了（已解决的issues）
    for raw_issue in raw_issues:
        mergeKey = raw_issue.get('mergeKey')
        stripped_file_pathname = raw_issue.get('strippedMainEventFilePathname')
        main_event_line_number = raw_issue.get('mainEventLineNumber')
        checker_name = raw_issue.get('checkerName')

        if not all([mergeKey, stripped_file_pathname, main_event_line_number, checker_name]):
            continue
        try:
            ## 使用judge_issues_existed判断原始issue是否在新文件中存在
            bool_issue_existed,explain_of_bool_issue_existed=judge_issues_existed(
                issue_in=raw_issue,
                raw_content_hash_key_2_issue_dict=raw_content_hash_key_2_issue_dict,
                new_content_hash_key_2_issue_dict=new_content_hash_key_2_issue_dict,
                raw_mergeKey_list=raw_mergeKey_list,
                new_mergeKey_list=new_mergeKey_list,
                work_dir=work_dir
            )

            if not bool_issue_existed:
                missing_issue_list.append(raw_issue)

        except Exception as e:
            # 如果判定过程中出现错误，跳过该issue
            print("判定issue '{}' 时出错: {}".format(mergeKey, e))
            continue

    # 2. 检查新issues中哪些是新增的
    for new_issue in new_issues:
        mergeKey = new_issue.get('mergeKey')
        stripped_file_pathname = new_issue.get('strippedMainEventFilePathname')
        main_event_line_number = new_issue.get('mainEventLineNumber')
        checker_name = new_issue.get('checkerName')

        if not all([mergeKey, stripped_file_pathname, main_event_line_number, checker_name]):
            continue
        if 'fixed' in new_issue['strippedMainEventFilePathname']:
            continue
        bool_issue_existed,explain_of_bool_issue_existed=judge_issues_existed(
                issue_in=new_issue,
                raw_content_hash_key_2_issue_dict=new_content_hash_key_2_issue_dict,
                new_content_hash_key_2_issue_dict=raw_content_hash_key_2_issue_dict,
                raw_mergeKey_list=new_mergeKey_list,
                new_mergeKey_list=raw_mergeKey_list,
                work_dir=work_dir
            )

        if not bool_issue_existed:
            new_issue_list.append(new_issue)
    return new_issue_list, missing_issue_list


if __name__ == "__main__":
    # 示例用法
    import sys

    if len(sys.argv) < 3:
        print("用法:")
        print("  1. 判定单个issue是否存在:")
        print("     python judge_issue_existed.py judge <mergeKey> <raw_errors_json> <check_errors_json>")
        print("  2. 比较两个错误文件的差异:")
        print("     python judge_issue_existed.py diff <raw_errors_json> <new_errors_json>")
        print("")
        print("示例:")
        print("  python judge_issue_existed.py judge 'abc123' 'raw_errors.json' 'new_errors.json'")
        print("  python judge_issue_existed.py diff 'raw_errors.json' 'new_errors.json'")
        sys.exit(1)

    command = sys.argv[1]

    if command == "judge":
        if len(sys.argv) < 5:
            print("错误: judge命令需要4个参数")
            print("用法: python judge_issue_existed.py judge <mergeKey> <raw_errors_json> <check_errors_json>")
            sys.exit(1)

        mergeKey = sys.argv[2]
        raw_errors_file = sys.argv[3]
        check_errors_file = sys.argv[4]

        try:
            # 从原始错误文件获取issue信息
            raw_issue = get_issue_info_by_merge_key(mergeKey, raw_errors_file)

            if raw_issue is None:
                print("错误: 在文件 '{}' 中未找到mergeKey为 '{}' 的issue".format(raw_errors_file, mergeKey))
                sys.exit(1)

            # 获取必要的参数
            stripped_file_pathname = raw_issue.get('strippedMainEventFilePathname')
            main_event_line_number = raw_issue.get('mainEventLineNumber')
            checker_name = raw_issue.get('checkerName')

            if not all([stripped_file_pathname, main_event_line_number, checker_name]):
                print("错误: issue信息不完整")
                sys.exit(1)

            # 调用判定函数
            exists = judge_issues_existed(
                mergeKey,
                stripped_file_pathname,
                main_event_line_number,
                checker_name,
                raw_errors_file,
                check_errors_file
            )

            print("Issue存在性判定结果:")
            print("  mergeKey: {}".format(mergeKey))
            print("  文件路径: {}".format(stripped_file_pathname))
            print("  行号: {}".format(main_event_line_number))
            print("  检查器: {}".format(checker_name))
            print("  是否存在: {}".format("是" if exists else "否"))

        except Exception as e:
            print("执行判定时发生错误: {}".format(e))
            sys.exit(1)

    elif command == "diff":
        if len(sys.argv) < 4:
            print("错误: diff命令需要3个参数")
            print("用法: python judge_issue_existed.py diff <raw_errors_json> <new_errors_json>")
            sys.exit(1)

        raw_errors_file = sys.argv[2]
        new_errors_file = sys.argv[3]

        try:
            # 调用diff函数
            new_issues, missing_issues = diff_issues(raw_all_errors_jsonpath=raw_errors_file, new_all_errors_jsonpath=new_errors_file)

            print("错误文件差异分析结果:")
            print("原始错误文件: {}".format(raw_errors_file))
            print("新错误文件: {}".format(new_errors_file))
            print("")

            print("新增的issues ({}个):".format(len(new_issues)))
            for i, issue in enumerate(new_issues, 1):
                print("  {}. mergeKey: {} | 文件: {} | 行号: {} | 检查器: {}".format(
                    i,
                    issue.get('mergeKey', 'N/A'),
                    issue.get('strippedMainEventFilePathname', 'N/A'),
                    issue.get('mainEventLineNumber', 'N/A'),
                    issue.get('checkerName', 'N/A')
                ))

            print("")
            print("已解决的issues ({}个):".format(len(missing_issues)))
            for i, issue in enumerate(missing_issues, 1):
                print("  {}. mergeKey: {} | 文件: {} | 行号: {} | 检查器: {}".format(
                    i,
                    issue.get('mergeKey', 'N/A'),
                    issue.get('strippedMainEventFilePathname', 'N/A'),
                    issue.get('mainEventLineNumber', 'N/A'),
                    issue.get('checkerName', 'N/A')
                ))

        except Exception as e:
            print("执行差异分析时发生错误: {}".format(e))
            sys.exit(1)

    else:
        print("错误: 未知命令 '{}'".format(command))
        print("支持的命令: judge, diff")
        sys.exit(1)
