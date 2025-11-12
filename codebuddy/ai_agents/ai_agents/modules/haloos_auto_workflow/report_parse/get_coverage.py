import os
import subprocess
from ai_agents.modules.haloos_auto_workflow.report_parse.function_coverage_report_parse import parse_coverage_report, get_coverage_summary
from ai_agents.supervisor_agents.haloos_unit_test.global_env_config import haloos_global_env_config


def get_current_coverage(timeout=600): #timeout=600
    """获取当前覆盖率"""

    test_repo_path = haloos_global_env_config.TEST_REPO_PATH

    # 切换文件路径到test_repo_path
    os.chdir(test_repo_path)  # 替换为你的目标路径

    print(f"切换文件路径到{test_repo_path}")

    # 运行覆盖率测试
    try:

        _ = subprocess.run(['ceedling', 'clobber'],
                        timeout=timeout,
                        capture_output=True, text=True, check=True)

        _ = subprocess.run(['ceedling', 'gcov:all'],
                        timeout=timeout,
                        capture_output=True, text=True, check=True)

        # 解析覆盖率报告
        coverage_file = os.path.join(test_repo_path, 'build/artifacts/gcov/gcovr/GcovCoverageResults.functions.html')
        result = parse_coverage_report(coverage_file, enhanced=True)
        summary = get_coverage_summary(result)

        coverage = summary.get('lines', 0.0)
    except subprocess.TimeoutExpired as e:
        print(f"命令执行超时！超时时间: {e.timeout}秒")
        coverage = 0.0
    except Exception as e:
        print(f"获取覆盖率失败: {e}")
        coverage = 0.0
    # 返回总体覆盖率
    return coverage
