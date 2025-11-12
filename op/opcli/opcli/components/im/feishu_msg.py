"""
飞书消息相关功能模块
"""

import json
from typing import Optional, List, Dict, Any
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    ListMessageRequest,
    ListMessageResponse,
    ListMessageReactionRequest,
    ListMessageReactionResponse,
)
from opcli.components.im.feishu import get_feishu_client


def get_messages(
    container_id: str,
    container_id_type: str = "chat",
    client: Optional[lark.Client] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    sort_type: str = "ByCreateTimeAsc",
    page_size: int = 20,
    page_token: str = ""
) -> Dict[str, Any]:
    """
    获取会话历史消息

    Args:
        container_id: 容器 ID（群聊ID、单聊ID或话题ID）
        container_id_type: 容器类型，可选值：chat（群聊/单聊）、thread（话题），默认为 chat
        client: 飞书客户端实例，如果不提供则使用全局客户端
        start_time: 起始时间，秒级时间戳
        end_time: 结束时间，秒级时间戳
        sort_type: 排序方式，可选值：ByCreateTimeAsc（升序）、ByCreateTimeDesc（降序），默认升序
        page_size: 每页结果数量，默认20，范围1-50
        page_token: 分页token，用于获取下一页结果

    Returns:
        Dict[str, Any]: 消息列表和分页信息

    Raises:
        ValueError: 当客户端未正确初始化时抛出
        Exception: 当API调用失败时抛出
    """
    # 获取客户端实例
    if client is None:
        client = get_feishu_client()

    # 构造请求对象
    request_builder = ListMessageRequest.builder() \
        .container_id_type(container_id_type) \
        .container_id(container_id) \
        .sort_type(sort_type) \
        .page_size(page_size)

    if start_time:
        request_builder.start_time(start_time)

    if end_time:
        request_builder.end_time(end_time)

    if page_token:
        request_builder.page_token(page_token)

    request: ListMessageRequest = request_builder.build()

    # 发起请求
    response: ListMessageResponse = client.im.v1.message.list(request)

    # 处理失败返回
    if not response.success():
        error_msg = f"获取消息失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        if response.raw:
            error_msg += f", resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        lark.logger.error(error_msg)
        raise Exception(error_msg)

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))

    result = {
        "success": True,
        "has_more": response.data.has_more if response.data else False,
        "page_token": response.data.page_token if response.data else "",
        "items": []
    }

    # 解析消息列表
    if response.data and response.data.items:
        for item in response.data.items:
            message_info = {
                "message_id": getattr(item, 'message_id', ''),
                "root_id": getattr(item, 'root_id', ''),
                "parent_id": getattr(item, 'parent_id', ''),
                "thread_id": getattr(item, 'thread_id', ''),
                "msg_type": getattr(item, 'msg_type', ''),
                "create_time": getattr(item, 'create_time', ''),
                "update_time": getattr(item, 'update_time', ''),
                "deleted": getattr(item, 'deleted', False),
                "updated": getattr(item, 'updated', False),
                "chat_id": getattr(item, 'chat_id', ''),
                "upper_message_id": getattr(item, 'upper_message_id', ''),
            }

            # 发送者信息
            sender = getattr(item, 'sender', None)
            if sender:
                message_info["sender"] = {
                    "id": getattr(sender, 'id', ''),
                    "id_type": getattr(sender, 'id_type', ''),
                    "sender_type": getattr(sender, 'sender_type', ''),
                    "tenant_key": getattr(sender, 'tenant_key', ''),
                }

            # 消息内容
            body = getattr(item, 'body', None)
            if body:
                message_info["body"] = {
                    "content": getattr(body, 'content', ''),
                }

            # @提及信息
            mentions = getattr(item, 'mentions', None)
            if mentions:
                message_info["mentions"] = []
                for mention in mentions:
                    message_info["mentions"].append({
                        "key": getattr(mention, 'key', ''),
                        "id": getattr(mention, 'id', ''),
                        "id_type": getattr(mention, 'id_type', ''),
                        "name": getattr(mention, 'name', ''),
                        "tenant_key": getattr(mention, 'tenant_key', ''),
                    })

            result["items"].append(message_info)

    return result


def get_all_messages(
    container_id: str,
    container_id_type: str = "chat",
    client: Optional[lark.Client] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    sort_type: str = "ByCreateTimeAsc",
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    获取所有历史消息的便捷函数（自动处理分页）

    Args:
        container_id: 容器 ID（群聊ID、单聊ID或话题ID）
        container_id_type: 容器类型，默认为 chat
        client: 飞书客户端实例
        start_time: 起始时间，秒级时间戳
        end_time: 结束时间，秒级时间戳
        sort_type: 排序方式，默认升序
        max_results: 最大结果数量

    Returns:
        List[Dict[str, Any]]: 消息列表
    """
    all_messages = []
    page_token = ""
    page_size = min(50, max_results)  # 每页最多50个

    while len(all_messages) < max_results:
        current_page_size = min(page_size, max_results - len(all_messages))

        try:
            result = get_messages(
                container_id=container_id,
                container_id_type=container_id_type,
                client=client,
                start_time=start_time,
                end_time=end_time,
                sort_type=sort_type,
                page_size=current_page_size,
                page_token=page_token
            )

            if result["items"]:
                all_messages.extend(result["items"])

            # 检查是否还有更多结果
            if not result.get("has_more", False) or not result.get("page_token"):
                break

            page_token = result["page_token"]

        except Exception as e:
            lark.logger.error(f"获取消息时发生错误: {e}")
            break

    return all_messages[:max_results]


def get_message_reactions(
    message_id: str,
    client: Optional[lark.Client] = None,
    reaction_type: Optional[str] = None,
    user_id_type: str = "open_id",
    page_size: int = 20,
    page_token: str = ""
) -> Dict[str, Any]:
    """
    获取消息表情回复

    Args:
        message_id: 消息ID
        client: 飞书客户端实例，如果不提供则使用全局客户端
        reaction_type: 表情类型（可选），如 SMILE、LAUGH 等
        user_id_type: 用户ID类型，可选值：open_id、union_id、user_id，默认为 open_id
        page_size: 每页结果数量，默认20，范围1-50
        page_token: 分页token，用于获取下一页结果

    Returns:
        Dict[str, Any]: 表情回复列表和分页信息

    Raises:
        ValueError: 当客户端未正确初始化时抛出
        Exception: 当API调用失败时抛出
    """
    # 获取客户端实例
    if client is None:
        client = get_feishu_client()

    # 构造请求对象
    request_builder = ListMessageReactionRequest.builder() \
        .message_id(message_id) \
        .user_id_type(user_id_type) \
        .page_size(page_size)

    if reaction_type:
        request_builder.reaction_type(reaction_type)

    if page_token:
        request_builder.page_token(page_token)

    request: ListMessageReactionRequest = request_builder.build()

    # 发起请求
    response: ListMessageReactionResponse = client.im.v1.message_reaction.list(request)

    # 处理失败返回
    if not response.success():
        error_msg = f"获取表情回复失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        if response.raw:
            error_msg += f", resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        lark.logger.error(error_msg)
        raise Exception(error_msg)

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))

    result = {
        "success": True,
        "has_more": response.data.has_more if response.data else False,
        "page_token": response.data.page_token if response.data else "",
        "items": []
    }

    # 解析表情回复列表
    if response.data and response.data.items:
        for item in response.data.items:
            reaction_info = {
                "reaction_id": getattr(item, 'reaction_id', ''),
                "action_time": getattr(item, 'action_time', ''),
            }

            # 操作人信息
            operator = getattr(item, 'operator', None)
            if operator:
                reaction_info["operator"] = {
                    "operator_id": getattr(operator, 'operator_id', ''),
                    "operator_type": getattr(operator, 'operator_type', ''),
                }

            # 表情类型
            reaction_type_obj = getattr(item, 'reaction_type', None)
            if reaction_type_obj:
                reaction_info["reaction_type"] = {
                    "emoji_type": getattr(reaction_type_obj, 'emoji_type', ''),
                }

            result["items"].append(reaction_info)

    return result


def get_all_message_reactions(
    message_id: str,
    client: Optional[lark.Client] = None,
    reaction_type: Optional[str] = None,
    user_id_type: str = "open_id",
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    获取所有表情回复的便捷函数（自动处理分页）

    Args:
        message_id: 消息ID
        client: 飞书客户端实例
        reaction_type: 表情类型（可选）
        user_id_type: 用户ID类型，默认为 open_id
        max_results: 最大结果数量

    Returns:
        List[Dict[str, Any]]: 表情回复列表
    """
    all_reactions = []
    page_token = ""
    page_size = min(50, max_results)  # 每页最多50个

    while len(all_reactions) < max_results:
        current_page_size = min(page_size, max_results - len(all_reactions))

        try:
            result = get_message_reactions(
                message_id=message_id,
                client=client,
                reaction_type=reaction_type,
                user_id_type=user_id_type,
                page_size=current_page_size,
                page_token=page_token
            )

            if result["items"]:
                all_reactions.extend(result["items"])

            # 检查是否还有更多结果
            if not result.get("has_more", False) or not result.get("page_token"):
                break

            page_token = result["page_token"]

        except Exception as e:
            lark.logger.error(f"获取表情回复时发生错误: {e}")
            break

    return all_reactions[:max_results]
