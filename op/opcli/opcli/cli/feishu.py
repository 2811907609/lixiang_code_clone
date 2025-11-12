"""
飞书相关命令行子命令
"""

import click
import json
import arrow
from typing import Optional
from opcli.components.im.feishu import search_groups_by_name, init_feishu_client
from opcli.components.im.feishu_group import get_group_info
from opcli.components.im.feishu_msg import get_all_messages, get_all_message_reactions


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def feishu_cmd():
    """
    飞书相关操作命令

    提供飞书平台的各种操作功能，包括群聊搜索、消息发送等。
    """
    pass


@feishu_cmd.command()
@click.argument('query', required=True)
@click.option('--max-results', '-n', default=10, help='最大结果数量，默认为10')
@click.option('--app-id', help='飞书应用 ID，可选，优先使用环境变量')
@click.option('--app-secret', help='飞书应用密钥，可选，优先使用环境变量')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='输出格式，默认为表格')
def search_groups(query: str, max_results: int, app_id: Optional[str], app_secret: Optional[str], output: str):
    """
    搜索飞书群聊

    QUERY: 搜索关键词，可以是群名称的一部分
    """
    try:
        # 初始化飞书客户端
        if app_id and app_secret:
            client = init_feishu_client(app_id=app_id, app_secret=app_secret)
        else:
            client = None  # 使用默认配置

        # 搜索群聊
        groups = search_groups_by_name(
            group_name=query,
            client=client,
            max_results=max_results
        )

        if not groups:
            click.echo(f"未找到匹配 '{query}' 的群聊")
            return

        # 根据输出格式显示结果
        if output == 'json':
            click.echo(json.dumps(groups, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            click.echo(f"找到 {len(groups)} 个匹配的群聊:")
            click.echo()

            for i, group in enumerate(groups, 1):
                click.echo(f"{i}. {group['name']}")
                if group.get('description'):
                    click.echo(f"   描述: {group['description']}")
                click.echo(f"   群ID: {group['chat_id']}")
                if group.get('member_count'):
                    click.echo(f"   成员数: {group['member_count']}")
                click.echo(f"   类型: {group['chat_type']}")
                click.echo()

    except Exception as e:
        click.echo(f"搜索群聊失败: {e}", err=True)
        raise click.Abort()


@feishu_cmd.command()
@click.argument('chat_id', required=True)
@click.option('--app-id', help='飞书应用 ID，可选，优先使用环境变量')
@click.option('--app-secret', help='飞书应用密钥，可选，优先使用环境变量')
@click.option('--user-id-type', default='open_id', help='用户ID类型，默认为 open_id')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='输出格式，默认为表格')
def get_group(chat_id: str, app_id: Optional[str], app_secret: Optional[str], user_id_type: str, output: str):
    """
    获取飞书群聊详细信息

    CHAT_ID: 群聊ID
    """
    try:
        # 初始化飞书客户端
        if app_id and app_secret:
            client = init_feishu_client(app_id=app_id, app_secret=app_secret)
        else:
            client = None  # 使用默认配置

        # 获取群聊信息
        group_info = get_group_info(
            chat_id=chat_id,
            client=client,
            user_id_type=user_id_type
        )

        # 根据输出格式显示结果
        if output == 'json':
            click.echo(json.dumps(group_info, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            click.echo("群聊详细信息:")
            click.echo()
            click.echo(f"群名称: {group_info.get('name', 'N/A')}")
            click.echo(f"群ID: {chat_id}")
            if group_info.get('description'):
                click.echo(f"描述: {group_info['description']}")
            click.echo(f"群类型: {group_info.get('chat_type', 'N/A')}")
            click.echo(f"群模式: {group_info.get('chat_mode', 'N/A')}")
            click.echo(f"成员数: {group_info.get('user_count', 'N/A')}")
            click.echo(f"机器人数: {group_info.get('bot_count', 'N/A')}")
            click.echo(f"群主ID: {group_info.get('owner_id', 'N/A')}")
            click.echo(f"是否外部群: {'是' if group_info.get('external') else '否'}")
            click.echo(f"群状态: {group_info.get('chat_status', 'N/A')}")

            # 权限信息
            click.echo()
            click.echo("权限设置:")
            click.echo(f"  添加成员权限: {group_info.get('add_member_permission', 'N/A')}")
            click.echo(f"  分享群名片权限: {group_info.get('share_card_permission', 'N/A')}")
            click.echo(f"  @所有人权限: {group_info.get('at_all_permission', 'N/A')}")
            click.echo(f"  编辑权限: {group_info.get('edit_permission', 'N/A')}")
            click.echo(f"  审核权限: {group_info.get('moderation_permission', 'N/A')}")
            click.echo(f"  入群审批: {group_info.get('membership_approval', 'N/A')}")

    except Exception as e:
        click.echo(f"获取群聊信息失败: {e}", err=True)
        raise click.Abort()


@feishu_cmd.command()
@click.argument('container_id', required=True)
@click.option('--container-type', '-t', default='chat', type=click.Choice(['chat', 'thread']),
              help='容器类型：chat（群聊/单聊）或 thread（话题），默认为 chat')
@click.option('--max-results', '-n', default=50, help='最大结果数量，默认为50')
@click.option('--start-date', help='起始日期（格式：YYYY-MM-DD，从当天00:00:00开始）')
@click.option('--end-date', help='结束日期（格式：YYYY-MM-DD，到当天23:59:59结束）')
@click.option('--sort', type=click.Choice(['asc', 'desc']), default='asc',
              help='排序方式：asc（升序）或 desc（降序），默认升序')
@click.option('--app-id', help='飞书应用 ID，可选，优先使用环境变量')
@click.option('--app-secret', help='飞书应用密钥，可选，优先使用环境变量')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='输出格式，默认为表格')
def get_messages(container_id: str, container_type: str, max_results: int,
                 start_date: Optional[str], end_date: Optional[str], sort: str,
                 app_id: Optional[str], app_secret: Optional[str], output: str):
    """
    获取会话历史消息

    CONTAINER_ID: 容器ID（群聊ID、单聊ID或话题ID）
    """
    try:
        # 初始化飞书客户端
        if app_id and app_secret:
            client = init_feishu_client(app_id=app_id, app_secret=app_secret)
        else:
            client = None  # 使用默认配置

        # 转换排序方式
        sort_type = "ByCreateTimeAsc" if sort == "asc" else "ByCreateTimeDesc"

        # 处理日期参数，转换为秒级时间戳
        start_time = None
        end_time = None

        if start_date:
            try:
                # 解析日期并设置为当天开始时间（00:00:00）
                start_arrow = arrow.get(start_date, 'YYYY-MM-DD')
                start_time = str(int(start_arrow.timestamp()))
            except Exception as e:
                click.echo(f"起始日期格式错误: {e}，请使用 YYYY-MM-DD 格式", err=True)
                raise click.Abort()

        if end_date:
            try:
                # 解析日期并设置为当天结束时间（23:59:59）
                end_arrow = arrow.get(end_date, 'YYYY-MM-DD').shift(days=1).shift(seconds=-1)
                end_time = str(int(end_arrow.timestamp()))
            except Exception as e:
                click.echo(f"结束日期格式错误: {e}，请使用 YYYY-MM-DD 格式", err=True)
                raise click.Abort()

        # 获取消息
        messages = get_all_messages(
            container_id=container_id,
            container_id_type=container_type,
            client=client,
            start_time=start_time,
            end_time=end_time,
            sort_type=sort_type,
            max_results=max_results
        )

        if not messages:
            click.echo("未找到消息")
            return

        # 根据输出格式显示结果
        if output == 'json':
            click.echo(json.dumps(messages, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            click.echo(f"找到 {len(messages)} 条消息:")
            click.echo()

            for i, msg in enumerate(messages, 1):
                # 格式化时间戳（毫秒转为可读格式）
                create_time = msg.get('create_time', '')
                if create_time:
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(int(create_time) / 1000)
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError, OverflowError):
                        time_str = create_time
                else:
                    time_str = 'N/A'

                # 发送者信息
                sender = msg.get('sender', {})
                sender_id = sender.get('id', 'N/A')
                sender_type = sender.get('sender_type', 'N/A')

                # 消息内容
                body = msg.get('body', {})
                content = body.get('content', '')

                # 尝试解析JSON内容
                try:
                    content_obj = json.loads(content)
                    if isinstance(content_obj, dict) and 'text' in content_obj:
                        content_display = content_obj['text']
                    else:
                        content_display = content[:100] + '...' if len(content) > 100 else content
                except (json.JSONDecodeError, TypeError, KeyError):
                    content_display = content[:100] + '...' if len(content) > 100 else content

                click.echo(f"{i}. [{time_str}] {sender_type}({sender_id})")
                click.echo(f"   消息ID: {msg.get('message_id', 'N/A')}")
                click.echo(f"   类型: {msg.get('msg_type', 'N/A')}")
                if msg.get('deleted'):
                    click.echo("   状态: 已删除")
                elif msg.get('updated'):
                    click.echo("   状态: 已编辑")
                if content_display:
                    click.echo(f"   内容: {content_display}")

                # 显示@提及信息
                mentions = msg.get('mentions', [])
                if mentions:
                    mention_names = [m.get('name', m.get('id', '')) for m in mentions]
                    click.echo(f"   @提及: {', '.join(mention_names)}")

                click.echo()

    except Exception as e:
        click.echo(f"获取消息失败: {e}", err=True)
        raise click.Abort()




@feishu_cmd.command()
@click.argument('chat_id', required=True)
@click.option('--start-date', help='起始日期（格式：YYYY-MM-DD）')
@click.option('--end-date', help='结束日期（格式：YYYY-MM-DD）')
@click.option('--max-messages', '-n', default=50, help='最大消息数量，默认为50')
@click.option('--no-reactions', is_flag=True, help='禁用获取表情回复统计')
@click.option('--app-id', help='飞书应用 ID，可选，优先使用环境变量')
@click.option('--app-secret', help='飞书应用密钥，可选，优先使用环境变量')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='输出格式，默认为表格')
def group_stats(chat_id: str, start_date: Optional[str], end_date: Optional[str],
                max_messages: int, no_reactions: bool, app_id: Optional[str], app_secret: Optional[str], output: str):
    """
    获取群聊统计信息

    包括：群聊基本信息、最近消息列表（含每条消息的表情回复数）、时间段内的总消息数和总表情回复数

    CHAT_ID: 群聊ID
    """
    try:
        # 初始化飞书客户端
        if app_id and app_secret:
            client = init_feishu_client(app_id=app_id, app_secret=app_secret)
        else:
            client = None  # 使用默认配置

        # 1. 获取群聊基本信息
        click.echo("正在获取群聊信息...")
        group_info = get_group_info(chat_id=chat_id, client=client)

        # 2. 处理日期参数
        start_time = None
        end_time = None

        if start_date:
            try:
                start_arrow = arrow.get(start_date, 'YYYY-MM-DD')
                start_time = str(int(start_arrow.timestamp()))
            except Exception as e:
                click.echo(f"起始日期格式错误: {e}，请使用 YYYY-MM-DD 格式", err=True)
                raise click.Abort()

        if end_date:
            try:
                end_arrow = arrow.get(end_date, 'YYYY-MM-DD').shift(days=1).shift(seconds=-1)
                end_time = str(int(end_arrow.timestamp()))
            except Exception as e:
                click.echo(f"结束日期格式错误: {e}，请使用 YYYY-MM-DD 格式", err=True)
                raise click.Abort()

        # 3. 获取消息列表
        click.echo("正在获取消息列表...")
        messages = get_all_messages(
            container_id=chat_id,
            container_id_type="chat",
            client=client,
            start_time=start_time,
            end_time=end_time,
            sort_type="ByCreateTimeDesc",
            max_results=max_messages
        )

        # 4. 统计话题数（standalone threads）
        thread_count = 0
        for msg in messages:
            # 如果消息有 thread_id 但没有 root_id，说明是独立话题的起始消息
            if msg.get('thread_id') and not msg.get('root_id'):
                thread_count += 1

        # 5. 获取每条消息的表情回复统计
        total_reactions = 0
        messages_with_reactions = []

        if no_reactions:
            # 跳过表情回复统计
            messages_with_reactions = [msg.copy() for msg in messages]
            for msg in messages_with_reactions:
                msg['reaction_count'] = None
        else:
            click.echo("正在统计表情回复...")
            for msg in messages:
                message_id = msg.get('message_id', '')
                if message_id:
                    try:
                        reactions = get_all_message_reactions(
                            message_id=message_id,
                            client=client,
                            max_results=1000
                        )
                        reaction_count = len(reactions)
                        total_reactions += reaction_count

                        msg_with_reaction = msg.copy()
                        msg_with_reaction['reaction_count'] = reaction_count
                        messages_with_reactions.append(msg_with_reaction)
                    except Exception as e:
                        # 如果获取表情失败，继续处理其他消息
                        click.echo(f"警告: 获取消息 {message_id} 的表情回复失败: {e}", err=True)
                        msg_with_reaction = msg.copy()
                        msg_with_reaction['reaction_count'] = 0
                        messages_with_reactions.append(msg_with_reaction)

        # 6. 输出结果
        if output == 'json':
            result = {
                "group_info": {
                    "chat_id": chat_id,
                    "name": group_info.get('name', 'N/A'),
                    "member_count": group_info.get('user_count', 'N/A')
                },
                "messages": messages_with_reactions,
                "statistics": {
                    "total_messages": len(messages),
                    "total_threads": thread_count,
                    "total_reactions": total_reactions if not no_reactions else None,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            click.echo()
            click.echo("=" * 60)
            click.echo("群聊基本信息")
            click.echo("=" * 60)
            click.echo(f"群名称: {group_info.get('name', 'N/A')}")
            click.echo(f"群ID: {chat_id}")
            click.echo(f"成员数: {group_info.get('user_count', 'N/A')}")
            click.echo()

            click.echo("=" * 60)
            click.echo("统计信息")
            click.echo("=" * 60)
            if start_date or end_date:
                period_str = f"{start_date or '开始'} 至 {end_date or '现在'}"
                click.echo(f"统计时间段: {period_str}")
            click.echo(f"消息总数: {len(messages)}")
            click.echo(f"话题总数: {thread_count}")
            if not no_reactions:
                click.echo(f"表情回复总数: {total_reactions}")
            click.echo()

            click.echo("=" * 60)
            click.echo("最近消息列表")
            click.echo("=" * 60)

            for i, msg in enumerate(messages_with_reactions, 1):
                # 格式化时间戳
                create_time = msg.get('create_time', '')
                if create_time:
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(int(create_time) / 1000)
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError, OverflowError):
                        time_str = create_time
                else:
                    time_str = 'N/A'

                # 发送者信息
                sender = msg.get('sender', {})
                sender_id = sender.get('id', 'N/A')

                # 消息内容
                body = msg.get('body', {})
                content = body.get('content', '')

                # 尝试解析JSON内容
                try:
                    content_obj = json.loads(content)
                    if isinstance(content_obj, dict) and 'text' in content_obj:
                        content_display = content_obj['text']
                    else:
                        content_display = content[:50] + '...' if len(content) > 50 else content
                except (json.JSONDecodeError, TypeError, KeyError):
                    content_display = content[:50] + '...' if len(content) > 50 else content

                reaction_count = msg.get('reaction_count')

                click.echo(f"\n{i}. [{time_str}] 发送者: {sender_id}")
                click.echo(f"   消息ID: {msg.get('message_id', 'N/A')}")
                click.echo(f"   类型: {msg.get('msg_type', 'N/A')}")

                # 显示话题信息
                if msg.get('thread_id') and not msg.get('root_id'):
                    click.echo(f"   话题ID: {msg.get('thread_id')} (独立话题)")
                elif msg.get('thread_id') and msg.get('root_id'):
                    click.echo(f"   话题ID: {msg.get('thread_id')} (回复)")

                if content_display:
                    click.echo(f"   内容: {content_display}")
                if reaction_count is not None:
                    click.echo(f"   表情回复数: {reaction_count}")

    except Exception as e:
        click.echo(f"获取群聊统计信息失败: {e}", err=True)
        raise click.Abort()
