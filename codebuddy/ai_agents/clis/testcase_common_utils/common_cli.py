
import os
import math
import arrow
import subprocess
from typing import Dict
from ai_agents.modules.haloos_auto_workflow.auto_create_repo import get_testcase_repo_dir_name
from ai_agents.modules.haloos_auto_workflow.utils import get_c_files_list_from_give_dir
from ai_agents.modules.haloos_auto_workflow.auto_create_repo import use_source_file_create_empty_ceedling_repo
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import get_all_functions_info_list
from ai_agents.modules.haloos_auto_workflow.auto_increase_coverage_sop import create_testcase_by_haloos_ai_agent
from ai_agents.core.runtime import runtime
from ai_agents.core.hooks import HookContext, HookResult,register_pre_tool_hook


def check_git_config(check_local: bool = False) -> Dict[str, any]:
    """
    检测Git是否安装以及用户配置是否存在

    Args:
        check_local: 是否检查当前目录的本地配置，默认为True

    Returns:
        包含检测结果的字典
    """
    result = {
        'git_installed': False,
        'git_version': None,
        'global_config': {
            'user.name': None,
            'user.email': None,
            'configured': False
        },
        'local_config': {
            'user.name': None,
            'user.email': None,
            'configured': False
        },
        'is_git_repo': False,
        'errors': []
    }

    # 1. 检查Git是否安装
    try:
        version_output = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        result['git_installed'] = True
        result['git_version'] = version_output.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        result['errors'].append(f"Git未安装或不在系统PATH中: {str(e)}")
        return result

    # 2. 检查全局配置
    try:
        # 获取全局user.name
        name_output = subprocess.run(
            ['git', 'config', '--global', 'user.name'],
            capture_output=True,
            text=True
        )
        if name_output.returncode == 0:
            result['global_config']['user.name'] = name_output.stdout.strip()

        # 获取全局user.email
        email_output = subprocess.run(
            ['git', 'config', '--global', 'user.email'],
            capture_output=True,
            text=True
        )
        if email_output.returncode == 0:
            result['global_config']['user.email'] = email_output.stdout.strip()

        # 判断全局配置是否完整
        result['global_config']['configured'] = bool(
            result['global_config']['user.name'] and
            result['global_config']['user.email']
        )
    except subprocess.CalledProcessError as e:
        result['errors'].append(f"检查全局配置时出错: {str(e)}")

    # 3. 检查本地配置（如果需要）
    if check_local:
        try:
            # 检查当前目录是否是Git仓库
            repo_check = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            result['is_git_repo'] = (repo_check.returncode == 0)

            if result['is_git_repo']:
                # 获取本地user.name
                name_output = subprocess.run(
                    ['git', 'config', 'user.name'],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
                if name_output.returncode == 0:
                    result['local_config']['user.name'] = name_output.stdout.strip()

                # 获取本地user.email
                email_output = subprocess.run(
                    ['git', 'config', 'user.email'],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
                if email_output.returncode == 0:
                    result['local_config']['user.email'] = email_output.stdout.strip()

                # 判断本地配置是否完整
                result['local_config']['configured'] = bool(
                    result['local_config']['user.name'] and
                    result['local_config']['user.email']
                )
        except subprocess.CalledProcessError as e:
            result['errors'].append(f"检查本地配置时出错: {str(e)}")

    return result


# 保护源文件不被修改的pre-hook
def pre_tool_for_file_protection_hook(context: HookContext) -> HookResult:
    # tool_name = context.tool_name
    tool_input = context.tool_input
    source_file_name = haloos_global_env_config.SOURCE_FILE_NAME

    file_path = tool_input.get("file_path", "")
    # 保护重要文件
    protected_files = [source_file_name]
    protected_dirs = ["src"]

    if any(protected in file_path for protected in protected_files + protected_dirs):
        deny_reason = f"受保护的文件或目录: {file_path},不允许修改"
        return HookResult.deny_result(reason=deny_reason)
    return HookResult.success_result()


def setup_haloos_hooks():
    """Register demo hooks to show tool usage."""
    print("🪝 Setting up haloos hooks...")
    # Register hooks: 目前识别这两个会修改文件，但不确定模型是否会有其他办法绕过，比如: create("simple.c") and mv simple.c source_file.c
    register_pre_tool_hook("create_new_file|search_and_replace", pre_tool_for_file_protection_hook)

def verify_send_parameters_value(source_file_full_path, testcase_repo_output_parent_path, human_set_sop_round):
    '''
        1. 检测source_file_full_path
        2. 检测testcase_repo_output_parent_path是否合法
    '''
    if not os.path.exists(source_file_full_path):
        return False, 'source_file_full_path参数指向的文件不存在'

    if not source_file_full_path.endswith('.c'):
        return False, 'source_file_full_path不是c文件，暂不支持生成测试用例'

    if not os.path.isabs(testcase_repo_output_parent_path):
        return False, 'testcase_repo_output_parent_path参数不是绝对路径'

    if not isinstance(human_set_sop_round, int):
        return False, 'human_set_sop_round参数不是整数'

    if human_set_sop_round > 20:
        return False, 'human_set_sop_round设置过大，暂不期望设置大于20'

    return True, '参数检测通过'

# 验证如果testcase_repo_dir存在的情况下，是否是一个期望的ceedling项目
def validate_testcase_repo_structure(testcase_repo_dir, source_file_name):

    # 配置文件存在
    project_yaml_file = os.path.join(testcase_repo_dir, 'project.yml')
    if not os.path.exists(project_yaml_file):
        return False, f'{project_yaml_file}文件不存在，不是一个合法的ceedling项目'

    # src文件夹存在
    src_dir_path = os.path.join(testcase_repo_dir, 'src')
    if not os.path.exists(src_dir_path):
        return False, f'{src_dir_path}文件不存在，不是一个合法的ceedling项目'

    # src下文件名和传入相同
    src_file_list = get_c_files_list_from_give_dir(src_dir_path)
    if len(src_file_list) != 1:
        return False, f'{src_file_list}源文件不唯一，不是一个合法的ceedling项目'

    src_file_name = os.path.basename(src_file_list[0])

    if src_file_name != source_file_name:
        return False, f'项目内的{src_file_name}和传入的{source_file_name}不相同，请检查'

    # 文件内容对比

    # test/support文件存在
    support_path = os.path.join(testcase_repo_dir,'test','support')
    if not os.path.exists(support_path):
        return False, f'{support_path}不存在，不是一个合法的ceedling项目'

    return True, '判断合格'


def get_sop_agent_loop_rounds(human_set_sop_round, source_file_full_path):
    '''
        1. 人员设定循环次数。
        2. 基于文件内函数个数推测循环次数
        3. 基于当前覆盖率报告推测循环次数（暂时不实现，后续考虑是否需要）
    '''
    if human_set_sop_round > 0:
        return human_set_sop_round

    function_list = get_all_functions_info_list(source_file_full_path)
    sop_round = max(math.ceil(len(function_list) / 10), 1) #保底进行一次
    return sop_round

def get_testcase_sop_agent_user_instance_id(source_file_full_path, add_time=False):
    if add_time:
        # 基于输入的测试用例绝对路径 + 时间获取
        return f"{source_file_full_path}:{arrow.now().format('YYYY-MM-DD_HH_mm')}"
    else:
        return source_file_full_path

def create_testcase_cli(source_file_full_path:str, testcase_repo_output_parent_path:str, system_function_declarations_path:str, human_set_sop_round:int = -1):
    # 注册钩子函数 - 临时禁用以避免线程泄漏
    # setup_haloos_hooks()
    print("⚠️  钩子函数暂时禁用以避免线程泄漏问题")

    human_set_sop_round = int(human_set_sop_round)

    # 设置用户：instance_id
    instance_id = get_testcase_sop_agent_user_instance_id(source_file_full_path)
    runtime.biz_id = instance_id

    # step 0: 配置检测
    git_check_result = check_git_config()
    if len(git_check_result['errors']) > 0:
        error_msg = git_check_result['errors']
        raise RuntimeError(f"Git配置检测失败: {error_msg}")

    # step 1: 参数规范性检测
    verify_result_flag, verify_msg = verify_send_parameters_value(source_file_full_path, testcase_repo_output_parent_path, human_set_sop_round)
    print(verify_msg)
    if not verify_result_flag:
        return

    # step 2: 判断是否需要创建空工程，如果需要则创建，若存在则做一个简单的工程结构检测
    source_file_name = os.path.basename(source_file_full_path)
    testcase_repo_dir = get_testcase_repo_dir_name(testcase_repo_output_parent_path, source_file_full_path)

    if os.path.exists(testcase_repo_dir):
        # 如果存在做验证
        verify_testcase_repo_flag, verify_testcase_repo_msg =validate_testcase_repo_structure(testcase_repo_dir,source_file_name)
        print(verify_testcase_repo_msg)
        if not verify_testcase_repo_flag:
            return
    else:
        # 不存在则创建，创建失败退出
        try:
            testcase_repo_dir = use_source_file_create_empty_ceedling_repo(source_file_full_path, testcase_repo_output_parent_path)
            print("创建空ceedling测试工程成功")
        except Exception as e:
            print(f"报错{e}, use_source_file_create_empty_ceedling_repo创建工程失败，请检测定位问题")
            return

    # step 3: 获取sop循环的轮数
    sop_circle_round = get_sop_agent_loop_rounds(human_set_sop_round, source_file_full_path)

    print(f"****本次sop预计会{sop_circle_round}次循环****\n")
    # step 4: 设置环境变量，后续工具和agent使用
    haloos_global_env_config.TEST_REPO_PATH = testcase_repo_dir
    haloos_global_env_config.SOURCE_FILE_NAME = source_file_name
    haloos_global_env_config.SYSTEM_FUN_DECLARATION_PATH = system_function_declarations_path

    # step 5: 生成测试用例
    create_testcase_by_haloos_ai_agent(max_iterations=sop_circle_round, target_coverage=100, continue_fail_to_increase_times=2) # before is continue_fail_to_increase_times=3

    print("Run haloos sop done")
