import os

from ai_agents.lib.smolagents import new_agent
from ai_agents.lib.tracing import generate_task_id, task_context
from ai_agents.modules.codedoggy.agent.model import (
    create_model_config_from_env,
)
from ai_agents.modules.codedoggy.agent.prompts.prompt import load_prompt
from smolagents import LogLevel
from sysutils.retry import retry


@retry(n=2, delay=3)
def review_final_answer_check(final_answer, event):
    trace_name_arr = (
        ["codedoggy", event.server, event.event_id, "score"]
        if event.server == "gerrit"
        else ["codedoggy", event.server, event.project_id, event.event_id, "score"]
    )
    trace_name = ":".join(trace_name_arr)
    sub_task_id = generate_task_id(trace_name)
    model = create_model_config_from_env(event.repo_config.model)
    with task_context(sub_task_id):
        task = load_prompt(
            "score",
            final_answer=final_answer,
            diff_content=event.diff_content,
            file_content=event.file_content,
            file_path=event.file_path,
            mr_diff_content=event.mr_diff_content,
        )
        agent = new_agent(
            tools=[],
            model=model,
            additional_authorized_imports=["json"],
            verbosity_level=LogLevel.INFO if not os.getenv('benchmark') else LogLevel.ERROR,
            stream_outputs=True,
        )
        res = agent.run(task=task)
        return res
