import json
import os
import traceback

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.modules.codedoggy.benchmark.data_loader import (
    get_case_by_web_url,
)
from ai_agents.modules.codedoggy.server.workflow import Event
from ai_agents.supervisor_agents.codereview.benchmark.agent import (
    CodeReviewBenchMarkAgent,
)
from smolagents import LogLevel

# 全局变量用于累计统计数据
_benchmark_stats = {
    'total_cases': 0,
    'total_recognized_known_issues': 0,
    'total_known_issues': 0,
    'total_valid_ai_issues': 0,
    'total_ai_generated_issues': 0
}

def load_task(
    work_path,
    source_commit,
    target_commit,
    expect_suggestions,
    ai_suggestions,
    diff_content,
):
    """
    读取任务模板文件并填充变量

    Args:
        work_path: 工作目录路径
        source_commit: 源提交
        target_commit: 目标提交
        expect_suggestions: 期望建议字典
        ai_suggestions: AI 建议列表
        diff_content: diff 内容

    Returns:
        str: 填充后的任务内容
    """
    try:
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, 'task.md')

        # 读取模板文件
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        task_content = content.replace('{work_path}', str(work_path))
        task_content = task_content.replace('{source_commit}', str(source_commit))
        task_content = task_content.replace('{target_commit}', str(target_commit))
        task_content = task_content.replace('{expect_suggestions}', str(expect_suggestions))
        task_content = task_content.replace('{ai_suggestions}', str(ai_suggestions))
        task_content = task_content.replace('{diff_content}', str(diff_content))

        return task_content

    except Exception as e:
        print(f'Error loading task template: {str(e)}')
        # 如果读取失败，返回空字符串或默认内容
        return ''


def append_result_to_json(result, filename='benchmark_results.json'):
    """
    将结果追加到JSON文件中

    Args:
        result: 要追加的结果数据
        filename: 目标文件名（默认: 'benchmark_results.json'）
    """
    if result is None:
        return

    try:
        # 从环境变量获取输出目录
        output_dir = os.environ.get('CODEDOGGY_BENCHMARK_OUTPUT_DIR', '.')

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构造完整的文件路径
        file_path = os.path.join(output_dir, filename)

        # 尝试读取现有文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except (FileNotFoundError, json.JSONDecodeError):
            # 文件不存在或格式错误，创建新列表
            data = []

        # 添加新数据
        data.append(result)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f'Error appending result to JSON file: {e}')


def _accumulate_stats(res):
    """
    累计每个case的统计数据到全局变量中

    Args:
        res: benchmark agent的执行结果
    """
    global _benchmark_stats

    if res is None:
        return

    _benchmark_stats['total_cases'] += 1
    _benchmark_stats['total_recognized_known_issues'] += res.get('recognized_known_issues_count', 0)
    _benchmark_stats['total_known_issues'] += res.get('known_issues_total', 0)
    _benchmark_stats['total_valid_ai_issues'] += res.get('valid_ai_issues_count', 0)
    _benchmark_stats['total_ai_generated_issues'] += res.get('ai_generated_issues_total', 0)



def get_benchmark_summary():
    """
    获取当前累计的benchmark汇总统计

    Returns:
        dict: 包含汇总统计的字典
    """
    global _benchmark_stats

    # 计算汇总的coverage和accuracy
    overall_coverage = 0.0
    overall_accuracy = 0.0

    if _benchmark_stats['total_known_issues'] > 0:
        overall_coverage = (_benchmark_stats['total_recognized_known_issues'] /
                          _benchmark_stats['total_known_issues'] * 100)

    if _benchmark_stats['total_ai_generated_issues'] > 0:
        overall_accuracy = (_benchmark_stats['total_valid_ai_issues'] /
                          _benchmark_stats['total_ai_generated_issues'] * 100)

    summary = {
        "coverage": f"{overall_coverage:.2f}%",
        "accuracy": f"{overall_accuracy:.2f}%",
        "recognized_known_issues_count": _benchmark_stats['total_recognized_known_issues'],
        "known_issues_total": _benchmark_stats['total_known_issues'],
        "valid_ai_issues_count": _benchmark_stats['total_valid_ai_issues'],
        "ai_generated_issues_total": _benchmark_stats['total_ai_generated_issues'],
        "total_test_cases": _benchmark_stats['total_cases'],
    }

    return summary



def save_benchmark_summary(filename='benchmark_summary.json'):
    """
    保存benchmark汇总统计到文件

    Args:
        filename: 保存的文件名
    """
    summary = get_benchmark_summary()
    append_result_to_json(summary, filename)


def get_repo_name(case_data):
    """
    Extract the repository name from the repo_name field

    Args:
        case_data: Case data containing repo_name

    Returns:
        str: The repository name (last part after '/'), or 'unknown' if not found
    """
    if not case_data or not isinstance(case_data, dict):
        return 'unknown'

    if 'input_context' not in case_data:
        return 'unknown'

    input_context = case_data['input_context']
    if not isinstance(input_context, dict):
        return 'unknown'

    repo_name = input_context.get('repo_name', '').strip()
    if not repo_name:
        return 'unknown'

    # Extract the last part after '/'
    parts = repo_name.split('/')
    return parts[-1] if parts[-1] else 'unknown'


def benchmark(event: Event, new_data: list, diff_content=''):
    """
    Benchmark function to print event and new_data as JSON

    Args:
        event: Event data
        new_data: New data to benchmark
        diff_content: Git diff content
    """
    try:
        if not event or not hasattr(event, 'web_url'):
            print('Warning: Invalid event object, skipping benchmark')
            return

        web_url = event.web_url
        if not web_url:
            print('Warning: No web_url in event, skipping benchmark')
            return

        data_case = get_case_by_web_url(web_url)
        if not data_case:
            print(f'Warning: No case data found for web_url: {web_url}')
            return

        # Extract repository name
        repo_name = get_repo_name(data_case)
        # Extract expect_suggestions as a list
        if (
            data_case
            and 'input_context' in data_case
            and 'change_context' in data_case['input_context']
        ):
            expect_suggestions_dict = data_case['input_context'][
                'change_context'
            ].get('expect_suggestions', {})

            # Expand the ~ path to absolute path
            work_path = os.path.expanduser(f'~/.cache/codeDoggy/{repo_name}')

            # Check if directory exists, if not, skip this case
            if not os.path.exists(work_path):
                print(
                    f'Error: Work directory does not exist: {work_path}, skipping case'
                )
                return

            try:
                agent = CodeReviewBenchMarkAgent(
                    project_path=work_path,
                    logger=AgentLogger(level=LogLevel.ERROR),
                )

                # 使用模板文件加载任务内容
                task_content = load_task(
                    work_path=work_path,
                    source_commit=event.source_commit,
                    target_commit=event.target_commit,
                    expect_suggestions=expect_suggestions_dict,
                    ai_suggestions=new_data,
                    diff_content=diff_content,
                )

                res = agent.run(task=task_content)

                if isinstance(res, str):
                    try:
                        res = json.loads(res)
                    except json.JSONDecodeError:
                        print('Warning: Failed to parse res as JSON, creating new dict')
                        res = {'raw_result': res}
                res['ai_suggestion_list'] = new_data
                res['case_id'] = data_case.get('case_id', -1)
                append_result_to_json(res)


                # 累计统计数据
                _accumulate_stats(res)
            except Exception as e:
                print(f'Error running benchmark agent: {str(e)}')
                traceback.print_exc()
                return
        else:
            print(
                'Warning: No change_context found in case data, skipping benchmark'
            )

    except Exception as e:
        print(f'Error in benchmark function: {str(e)}')
