import os
import sys
from pathlib import Path

import arrow
import fire

import ai_agents.lib.tracing  # noqa: F401
from ai_agents.lib.smolagents import LogLevel, new_agent_logger
from ai_agents.tools.vendor_tools import (
    ensure_all_tools,
    add_tools_to_path,
)
from ai_agents.core.runtime import runtime
from ai_agents.supervisor_agents.swebench import run_agent


runtime.app = "SWEBench"

def solve_issue(working_dir: str,
                instance_id: str = None,
                issue_text: str = None,
                file: str = None,
                log_to_file=True,
                patch_path: str=None):
    if file and issue_text:
        print("Error: Cannot specify both --file and issue_text")
        return False

    if file:
        file_path = Path(file)
        if not file_path.exists():
            print(f"Error: Problem statement file '{file}' does not exist")
            return False
        issue_text = file_path.read_text()

    if not issue_text:
        print("Error: Must provide either issue_text or --file argument")
        return False

    repo_path = Path(working_dir).resolve()
    if not repo_path.exists():
        print(f"Error: Path '{working_dir}' does not exist")
        return False

    if not repo_path.is_dir():
        print(f"Error: Path '{working_dir}' is not a directory")
        return False

    now = arrow.now()
    if log_to_file:
        time_str = now.format('YYYY-MM-DD_HH_mm')
        logs_dir = Path('./logs')
        logs_dir.mkdir(exist_ok=True)
        if instance_id:
            log_filename = f'task_{instance_id}_{time_str}'
        else:
            log_filename = f'task_{time_str}'
        log_file_path = logs_dir / f'{log_filename}.log'
        log_file_path.write_text('\n')
    else:
        log_file_path = None

    agent_logger = new_agent_logger(log_file_path, level=LogLevel.DEBUG)

    print("=" * 80)
    print("SWE-Bench Issue Solver")
    print("=" * 80)
    print(f"Target repo: {repo_path}")
    print(f"Current directory: {os.getcwd()}")

    try:
        result = run_agent(agent_logger, issue_text,
                           project_path=repo_path, patch_path=patch_path)

        print("\n" + "=" * 80)
        print("Issue resolution completed!")
        print("=" * 80)
        print(result)

        return True

    except KeyboardInterrupt:
        print("\n\nIssue resolution interrupted by user")
        return False
    except Exception as e:
        print(f"\nError during resolution: {e}")
        import traceback
        traceback.print_exc()
        return False


def cli_solve_issue(working_dir: str,
                    instance_id: str = None,
                    issue_text: str = None,
                    file: str = None,
                    patch_path: str = None,
                    **kwargs):
    runtime.biz_id = instance_id

    success = solve_issue(
        working_dir,
        instance_id=instance_id,
        issue_text=issue_text,
        file=file,
        patch_path=patch_path)

    if success:
        print("\nIssue resolved successfully!")
    else:
        print("\nIssue resolution failed")
        sys.exit(1)


if __name__ == "__main__":
    ensure_all_tools()
    add_tools_to_path()
    fire.Fire(cli_solve_issue)
