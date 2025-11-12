
import fire
from ai_agents.core.runtime import runtime
from clis.testcase_common_utils.common_cli import create_testcase_cli

# 设置当前任务类型
runtime.app = "haloos"

def main():
    fire.Fire(create_testcase_cli)

if __name__ == "__main__":
    main()
