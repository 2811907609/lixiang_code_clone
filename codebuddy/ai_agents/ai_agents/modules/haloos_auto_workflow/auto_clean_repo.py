
import os
from ai_agents.supervisor_agents.haloos_unit_test.ceedling_test_runner import compile_ceedling_repo
from ai_agents.modules.haloos_auto_workflow.compile_log_analyzer_fail_testcase import has_test_failures,get_failed_files_and_functions
from ai_agents.modules.haloos_auto_workflow.remove_yaml_config import remove_test_config_by_name
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import get_function_line_range,get_all_functions_info_list
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config

def delete_single_file(path: str) -> None:
    """
    使用 os.remove 删除单个文件，并对常见异常进行捕获与提示。

    :param path: 待删除文件的路径
    """
    try:
        os.remove(path)
        print(f"已删除文件: {path}")
    except FileNotFoundError:
        print(f"[跳过] 文件不存在: {path}")
    except IsADirectoryError:
        print(f"[跳过] 指定路径是目录而非文件: {path}")
    except PermissionError as e:
        print(f"[跳过] 无权限删除文件: {path} ({e})")
    except OSError as e:
        # 捕获其他可能的 OSError（例如路径过长、设备未就绪等）
        print(f"[跳过] 删除失败: {path} ({e})")

def give_range_remove_content_from_file(file_path, start_line, end_line):
    """
    从C文件中删除指定行范围的函数。

    参数:
        file_path (str): C文件的路径。
        start_line (int): 函数的起始行号（包含）。
        end_line (int): 函数的结束行号（包含）。
    """
    try:
        # 读取文件的所有行
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 检查行号是否有效
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            print(f"错误：行号无效。文件共有 {len(lines)} 行。")
            return

        # 删除指定范围的行（注意：列表索引从0开始，行号从1开始）
        del lines[start_line - 1 : end_line]

        # 将修改后的内容写回文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        print(f"成功删除第 {start_line} 到 {end_line} 行的函数。")

    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 未找到。")
    except Exception as e:
        print(f"发生错误：{e}")


def tell_if_remove_file(function_final_list):
    if not function_final_list:
        return True

    if len(function_final_list) == 0:
        return True

    no_contain_testcase_flag = True

    for function_name in function_final_list:
        if 'test' in function_name:
            no_contain_testcase_flag = False
            return no_contain_testcase_flag
    return no_contain_testcase_flag

'''
    1. 调用compile_ceedling_repo获取报错日志
    2. 解析报错日志
    3. 一个一个文件删除。
        1. 文件内删除后是不是空文件了？
        2. 空文件也删除。
        3. 空文件删除要对应删除project里的配置。（比较难）
'''
def get_test_fail_testcase_file_function(sample_error):
    failure_info = get_failed_files_and_functions(sample_error)

    all_info = {}

    # 获取失败的错误信息
    for item_info in failure_info:
        # item_info = json.dumps(item_info, indent=4, ensure_ascii=False)
        file_name = item_info['file']

        if file_name in all_info.keys():
            all_info[file_name].append(item_info)
        else:
            all_info[file_name] = [item_info]

    return all_info


def clean_testcase_file(test_file_name, file_info):

    # 获取函数完整文件
    working_directory = haloos_global_env_config.TEST_REPO_PATH

    test_file_path = os.path.join(working_directory,test_file_name)
    project_file_path=os.path.join(working_directory,'project.yml')


    if not os.path.exists(test_file_path):
        return

    # 去除文件内函数体，一个个删除
    for function_remove_info in file_info:
        test_function = function_remove_info['test_function']
        function_file = function_remove_info['file']
        line_info = get_function_line_range(test_file_path,test_function)
        if line_info is None:
            continue

        start_line = line_info[0]
        end_line = line_info[1]
        give_range_remove_content_from_file(test_file_path, start_line, end_line)


    # 最后判断文件是否存在test函数
    function_final_list = get_all_functions_info_list(test_file_path)

    remove_flag = tell_if_remove_file(function_final_list)

    if not remove_flag:
        return
    else:
        # 为空触发文件删除以及配置文件内文件条件编译删除
        print("该文件内不包含测试用例，删除")
        delete_single_file(test_file_path)
        test_name_conditional = function_file.split('/')[1].replace('.c','')
        preserve_format=False
        remove_test_config_by_name(project_file_path, test_name_conditional, preserve_format)


def clean_repo_by_rule(is_git_commit=True):

    working_directory = haloos_global_env_config.TEST_REPO_PATH


    if working_directory is None:
        print("TEST_REPO_PATH not set" )
        return

    # git 备份
    is_git = os.path.isdir(os.path.join(working_directory, '.git'))
    if is_git and is_git_commit:
        use_git_commit_info = True
    else:
        use_git_commit_info = False
    if use_git_commit_info:
        os.system(f'cd {working_directory} && git add .')
        os.system(f'cd {working_directory} && git commit -m "feat: before clean repo"')

    # 编译
    compile_info = compile_ceedling_repo()

    # 删除1: 失败测试用例
    is_fail = has_test_failures(compile_info)
    if not is_fail:
        return
    failure_info_dict = get_test_fail_testcase_file_function(compile_info)
    for test_file_name,file_info in failure_info_dict.items():
        clean_testcase_file(test_file_name, file_info)

    # 最终git提交
    if use_git_commit_info:
        os.system(f'cd {working_directory} && git add .')
        os.system(f'cd {working_directory} && git commit -m "feat: after clean repo"')
