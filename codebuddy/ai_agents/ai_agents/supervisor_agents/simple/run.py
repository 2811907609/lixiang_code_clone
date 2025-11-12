
import os

from sysutils.xos import change_dir
from ai_agents.lib.tracing import generate_task_id

from .agent import SimpleSupervisorAgent


def run_agent(logger,
              task,
              project_path: str = None):
        task_id_for_run = generate_task_id()
        print(f"\nGenerated task ID: {task_id_for_run}")

        supervisor = SimpleSupervisorAgent(logger=logger)
        print(f'agent {supervisor}')

        print(f"\nStarting issue resolution..., task ID: {task_id_for_run}")
        with change_dir(project_path):
            print(f"New working directory: {os.getcwd()}")
            result = supervisor.run(task, task_id=task_id_for_run)

        return result
