#!/usr/bin/env python3
"""
HaloOS Ceedling 单元测试智能体使用示例

演示如何使用 HaloOSUnitTestSupervisorAgent 为 HaloOS 项目创建 Ceedling 单元测试工程。
该智能体会协调多个微智能体完成测试工程的创建和验证。
"""

import os
import sys
import fire
import ai_agents.lib.tracing # noqa: F401
import arrow

from pathlib import Path
from ai_agents.lib.smolagents import new_agent_logger, LogLevel
from ai_agents.supervisor_agents.haloos_unit_test.agent import HaloOSUnitTestSupervisorAgent
from ai_agents.lib.tracing import generate_task_id


def create_unit_tests(haloos_path: str, log_to_file=False):
    """
    为 HaloOS 项目创建 Ceedling 单元测试工程

    Args:
        haloos_path: HaloOS 项目路径
        powerful: 是否使用强大模型（默认使用自动选择）
        task_id: 自定义任务ID，用于追踪所有LLM调用
    """
    # 验证路径
    haloos_path = Path(haloos_path).resolve()
    if not haloos_path.exists():
        print(f"错误: 路径 '{haloos_path}' 不存在")
        return False

    if not haloos_path.is_dir():
        print(f"错误: 路径 '{haloos_path}' 不是目录")
        return False

    now = arrow.now()
    if log_to_file:
        time_str = now.format('YYYY-MM-DD_HH_mm')
        log_file_path = Path('./.logs') / f'task_{time_str}.log'
        log_file_path.write_text('\n')
    else:
        log_file_path = None

    agent_logger = new_agent_logger(log_file_path, level=LogLevel.DEBUG)

    print("=" * 80)
    print("HaloOS Ceedling 单元测试智能体演示")
    print("=" * 80)
    print(f"目标项目: {haloos_path}")
    print(f"当前工作目录: {os.getcwd()}")

    try:
        # 切换到目标项目目录
        print(f"\n切换工作目录到: {haloos_path}")
        os.chdir(haloos_path)
        print(f"新的工作目录: {os.getcwd()}")


        task_id_for_run = generate_task_id()
        print(f"\n生成任务ID: {task_id_for_run}")

        # 创建监督智能体
        print("\n初始化 HaloOS 单元测试监督智能体...")
        supervisor = HaloOSUnitTestSupervisorAgent(logger=agent_logger)

        # 构建测试任务
        task_content = """
请为当前目录的 HaloOS 项目创建完整的 Ceedling 单元测试工程。

你当前已切换到该目录，请给 src 目录下面的 xxx.c 文件生单测。
"""

        print("\n开始创建测试工程...")
        print(f"任务ID: {task_id_for_run}")
        print("-" * 60)

        # 执行测试工程创建，传入任务ID进行追踪
        result = supervisor.run(task_content, task_id=task_id_for_run)

        print("\n" + "=" * 80)
        print("测试工程创建完成！")
        print("=" * 80)
        print(result)

        return True

    except KeyboardInterrupt:
        print("\n\n测试工程创建被用户中断")
        return False
    except Exception as e:
        print(f"\n创建过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def cli_create_tests_run_task(haloos_path: str,log_to_file=False):
    """
    命令行接口函数，用于创建 HaloOS 单元测试工程。
    fire库会自动将此函数的参数映射为命令行参数。

    Args:
        haloos_path: HaloOS 项目路径 (位置参数)
        powerful: 是否使用强大模型 (例如 --powerful)
        task_id: 自定义任务ID (例如 --task-id "my_id")
    """
    # 调用核心创建逻辑
    success = create_unit_tests(haloos_path,log_to_file)

    # 根据创建结果打印提示信息
    if success:
        print("\n✅ 测试工程创建成功！")
        print("\n💡 提示:")
        print("   - 可以运行 'ceedling test:all' 验证测试工程")

    else:
        print("\n❌ 测试工程创建失败")
        sys.exit(1)


if __name__ == "__main__":
    fire.Fire(cli_create_tests_run_task)
