"""
opcli 主命令行入口
"""

import click
from .feishu import feishu_cmd


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version="0.0.1", prog_name="opcli")
@click.pass_context
def main(ctx):
    """
    Operation CLI - 运维命令行工具

    一个用于处理各种运维任务的命令行工具，支持飞书等平台的集成操作。
    """
    # 确保上下文对象存在
    ctx.ensure_object(dict)


# 注册 feishu 子命令
main.add_command(feishu_cmd, name='feishu')


if __name__ == '__main__':
    main()
