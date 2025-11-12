
import os
import subprocess

from sysutils.xos import change_dir
from ai_agents.lib.tracing import generate_task_id

from .agent import SWEBenchSupervisorAgent

def get_git_diff(project_path: str) -> str:
    """Get the git diff of the project."""
    pwd = os.getcwd()
    if not os.path.isdir(project_path):
        return ""
    os.chdir(project_path)
    try:
        stdout = subprocess.check_output(["git", "--no-pager", "diff"]).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        stdout = ""
    finally:
        os.chdir(pwd)
    return stdout

def run_agent(logger,
              issue_text,
              project_path: str = None,
              patch_path: str=None):
        task_id_for_run = generate_task_id()
        print(f"\nGenerated task ID: {task_id_for_run}")

        supervisor = SWEBenchSupervisorAgent(logger=logger)
        print(f'agent {supervisor}')

        print(f"\nStarting issue resolution..., task ID: {task_id_for_run}")
        with change_dir(project_path):
            print(f"New working directory: {os.getcwd()}")
            result = supervisor.run(issue_text, task_id=task_id_for_run)

        if patch_path:
            print("begin to write patch")
            with open(patch_path, "w") as patch_f:
                patch_f.write(get_git_diff(project_path))

        return result
