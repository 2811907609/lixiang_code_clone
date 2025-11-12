
import os
import math
import fire
from ai_agents.modules.haloos_auto_workflow.auto_create_repo import get_testcase_repo_dir_name
from ai_agents.modules.haloos_auto_workflow.utils import get_c_files_list_from_give_dir
from ai_agents.modules.haloos_auto_workflow.auto_create_repo import use_source_file_create_empty_ceedling_repo
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config
from ai_agents.supervisor_agents.haloos_unit_test.c_function_locator import get_all_functions_info_list
from ai_agents.modules.haloos_auto_workflow.auto_increase_coverage_sop import create_testcase_by_haloos_ai_agent


def verify_send_parameters_value(source_file_full_path, testcase_repo_output_parent_path, human_set_sop_round):
    '''
        1. 检测source_file_full_path
        2. 检测testcase_repo_output_parent_path是否合法
    '''
    if not os.path.isabs(source_file_full_path):
        return False, 'source_file_full_path参数不是绝对路径'

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
    sop_round = math.ceil(len(function_list) / 10)

    return sop_round


def haloos_create_testcase_cli(source_file_full_path:str, testcase_repo_output_parent_path:str, human_set_sop_round:int = -1):

    human_set_sop_round = int(human_set_sop_round)

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

    # step 4: 设置环境变量，后续工具和agent使用
    haloos_global_env_config.TEST_REPO_PATH = testcase_repo_dir
    haloos_global_env_config.SOURCE_FILE_NAME = source_file_name

    # step 5: 生成测试用例
    create_testcase_by_haloos_ai_agent(max_iterations=sop_circle_round, target_coverage=100, continue_fail_to_increase_times=3)

    print("Run haloos sop done")


def main():
    fire.Fire(haloos_create_testcase_cli)

if __name__ == "__main__":
    main()
