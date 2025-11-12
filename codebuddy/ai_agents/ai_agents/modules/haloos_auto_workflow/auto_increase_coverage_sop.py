import os
import litellm
import time
from ai_agents.modules.haloos_auto_workflow.utils import safe_modify_with_git
from ai_agents.modules.haloos_auto_workflow.report_parse.get_coverage import get_current_coverage
from clis.testcase_common_utils.haloos_unit_test_demo import cli_create_tests_run_task
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config

litellm.request_timeout = 180  # 5分钟

# 关注覆盖率是否连续N次没有提升，关注存在上升趋势
def check_coverage_no_stagnation(lst, N):

    if not lst:
        return True
    count = 1
    for i in range(1, len(lst)):
        if lst[i] == lst[i-1]:
            count += 1
            if count >= N:
                return False
        else:
            count = 1
    return True

#从最大值首次出现后数数，如果连续N次都没出现更大的数，则False。
def check_coverage_no_increase_after_max(lst, N):
    if not lst or N <= 0:
        return True

    max_val = max(lst)
    first_max_index = lst.index(max_val)
    count = 0

    for num in lst[first_max_index + 1:]:
        if num > max_val:
            # 出现比最大值更大的，重置最大值和计数
            max_val = num
            count = 0
        else:
            count += 1
            if count >= N:
                return False
    return True

def validation_function(last_coverage):
    """验证函数

    Args:
        last_coverage: 修改前的覆盖率

    Returns:
        bool: 如果覆盖率没有降低返回True，否则返回False
    """
    now_coverage = get_current_coverage()

    # 如果覆盖率变小了，则回撤更改
    if last_coverage > now_coverage:
        return False
    else:
        return True

def run_test_task(test_repo_path,log_to_file=False):
    """运行测试任务的通用方法

    Args:
        task_template: 任务描述模板
        **kwargs: 传递给任务模板的参数
    """
    os.chdir(test_repo_path)


    ''' 执行测试用例生成 '''


    def run_unit_test_agent():
        result = cli_create_tests_run_task(test_repo_path,log_to_file)
        return result

    # 获取修改前的覆盖率
    last_coverage = get_current_coverage()

    # todo: 利用上次agent返回结果，吸取教训？
    unit_test_agent_modify_flag, unit_test_agent_result = safe_modify_with_git(
        modify_function=run_unit_test_agent,
        validation_function=validation_function,
        validation_args=(last_coverage,),  # 只传入last_coverage，now_coverage会在验证时获取
        commit_message=f"Run test task from coverage {last_coverage}",
        project_path=test_repo_path
    )

    '''执行工程检测'''

    return unit_test_agent_modify_flag, unit_test_agent_result

def create_testcase_by_haloos_ai_agent(max_iterations, target_coverage, continue_fail_to_increase_times):
    '''
        1. 循环执行agnet的控制流，直到达到覆盖率或最大循环次数或多次连续覆盖率未提升
        2. 每次测试用例生成后做git报错，保证每次循环后有备份
    '''

    test_repo_path = haloos_global_env_config.TEST_REPO_PATH

    continue_fail_to_increase = 0
    # coverage_results_list = []
    check_coverage_results_list = []

    base_time = time.time()
    print(">>>>>>>>>>>>>>>>>>>>>>>>>")
    for i in range(max_iterations):

        current_coverage = get_current_coverage()
        iteration_time_start = time.time()
        check_coverage_results_list.append(current_coverage)
        print(f">>>>> 第{i}次循环<<<<<<")
        print(f">>>>>> 当前覆盖率{current_coverage}% <<<<<<")
        print(f">>>>>> 历史覆盖率{check_coverage_results_list} <<<<<<")

        # 达到覆盖率
        if current_coverage >= target_coverage:
            print(f">>>>>> 达到目标覆盖率{target_coverage}% <<<<<<")
            break

        if not check_coverage_no_stagnation(check_coverage_results_list, continue_fail_to_increase_times):
            print(f">>>>>> 连续{continue_fail_to_increase}次覆盖率未提升，退出 <<<<<<")
            break

        if not check_coverage_no_increase_after_max(check_coverage_results_list, continue_fail_to_increase_times):
            print(f">>>>>> 连续{continue_fail_to_increase}次覆盖率未提升，退出 <<<<<<")
            break

        unit_test_agent_modify_flag, unit_test_agent_result = run_test_task(test_repo_path)

        iteration_time_end = time.time()

        print("iteration time: ", iteration_time_end - iteration_time_start)

    end_time = time.time()
    print("total time: ", end_time - base_time)

if __name__ == "__main__":
    # debug
    create_testcase_by_haloos_ai_agent(max_iterations=1, target_coverage=100, continue_fail_to_increase_times=4)
