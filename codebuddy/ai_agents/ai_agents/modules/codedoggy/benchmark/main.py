import os
import random
from typing import Any, Dict

import ai_agents.modules.codedoggy.benchmark.data_loader as data_loader
from ai_agents.modules.codedoggy.benchmark.benchmark import (
    save_benchmark_summary,
)
from ai_agents.modules.codedoggy.benchmark.data_loader import (
    get_data_file_path,
    load_and_store_global_data,
)
from ai_agents.modules.codedoggy.client.gerrit import GerritClient
from ai_agents.modules.codedoggy.server.api import (
    extract_gerrit_repo_url,
    start_review_server,
)
from ai_agents.modules.codedoggy.server.workflow import Event
from ai_agents.modules.codedoggy.utils.repo import (
    repo_basename,
    repo_url2clone_url,
)


def build_event(case: Dict[str, Any]) -> Event:
    input_context = case.get('input_context', {})
    event_id = input_context.get('event_id', '')
    server = input_context.get('server', '')
    source_commit = input_context.get('source_commit', '')
    target_commit = input_context.get('target_commit', '')
    web_url = input_context.get('web_url', '')
    repo_web_url = extract_gerrit_repo_url(web_url)
    repo_name = ''
    if web_url:
        repo_name = repo_basename(repo_web_url)
    clone_url = repo_url2clone_url(server, repo_web_url)
    return Event(
        repo_url=clone_url,
        source_commit=source_commit,
        target_commit=target_commit,
        repo_name=repo_name,
        server=server,
        change_num=event_id,
        revision_id=input_context.get('patchset', 1),
        gerrit_client=GerritClient(),
        web_url=web_url,
        project_name=input_context.get('repo_name',''),
    )

def process_quick_cases_with_env_setup(file_path: str, num_cases: int = 5) -> None:
    """
    Process random sample of cases by setting environment variables for each case

    Args:
        file_path: Path to the JSON file
        num_cases: Number of random cases to process (default: 5)
    """
    # Load data into global variable
    load_and_store_global_data(file_path)

    # Collect all cases from all repos
    all_cases = []
    for repo_name, case_list in data_loader.CLASSIFIED_CASES.items():
        for case in case_list:
            case['repo_name'] = repo_name  # Add repo name for reference
            all_cases.append(case)

    # Randomly select cases
    selected_cases = random.sample(all_cases, min(num_cases, len(all_cases)))

    print(f'Selected {len(selected_cases)} random cases out of {len(all_cases)} total cases')

    # Process selected cases
    for i, case in enumerate(selected_cases):
        repo_name = case.get('repo_name', 'unknown')
        case_id = case.get('case_id', 'unknown')

        print(f'\nProcessing case {i + 1}/{len(selected_cases)} - repo: {repo_name}, case_id: {case_id}')

        # Set environment variables for each case
        event = build_event(case)
        try:
            start_review_server(event)
        except Exception as e:
            print(f'  Error starting server for case {case_id}: {e}')
            continue


def process_all_cases_with_env_setup(file_path: str) -> None:
    """
    Process all cases by setting environment variables for each case

    Args:
        file_path: Path to the JSON file
    """
    # Load data into global variable
    load_and_store_global_data(file_path)
    # should_break_all=False
    # Traverse outer map (repo_name -> case list)
    for repo_name, case_list in data_loader.CLASSIFIED_CASES.items():
        print(f'\nProcessing repo: {repo_name}')

        # Inner loop through list of cases
        for i, case in enumerate(case_list):
            print(
                f'  Processing case {i + 1}/{len(case_list)} - case_id: {case.get("case_id", "unknown")}'
            )
            # if case.get('case_id', 2) == 2:
            # Set environment variables for each case
            event = build_event(case)
            try:
                start_review_server(event)
            except Exception as e:
                print(f'  Error starting server for case {case.get("case_id", "unknown")}: {e}')
                continue

def env_perpare():
    os.environ['benchmark'] = 'true'
    config = os.getenv('CODEDOGGY_BASE_CONFIG')
    if config:
        os.environ['config'] = config

if __name__ == '__main__':
    # Get the correct data file path
    data_file_path = get_data_file_path()
    env_perpare()
    # Check environment variable to determine execution mode
    if os.environ.get('CODEDOGGY_QUICK_BENCHMARK', '').lower() == 'true':
        num_cases = int(os.environ.get('QUICK_NUM_CASES', '5'))
        print(f'Running quick benchmark with {num_cases} random cases')
        process_quick_cases_with_env_setup(data_file_path, num_cases)
    else:
        print('Running full benchmark with all cases')
        process_all_cases_with_env_setup(data_file_path)
    save_benchmark_summary()
