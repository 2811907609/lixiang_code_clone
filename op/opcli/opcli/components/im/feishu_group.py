"""
飞书群聊管理模块
"""

import json
from typing import Optional, Dict, Any
import lark_oapi as lark
from lark_oapi.api.im.v1 import GetChatRequest, GetChatResponse
from opcli.components.im.feishu import get_feishu_client


def get_group_info(
    chat_id: str,
    client: Optional[lark.Client] = None,
    user_id_type: str = "open_id"
) -> Dict[str, Any]:
    """
    根据群ID获取群聊详细信息

    Args:
        chat_id: 群聊ID
        client: 飞书客户端实例，如果不提供则使用全局客户端
        user_id_type: 用户ID类型，默认为 "open_id"

    Returns:
        Dict[str, Any]: 群聊详细信息

    Raises:
        ValueError: 当客户端未正确初始化时抛出
        Exception: 当API调用失败时抛出
    """
    # 获取客户端实例
    if client is None:
        client = get_feishu_client()

    # 构造请求对象
    request: GetChatRequest = GetChatRequest.builder() \
        .chat_id(chat_id) \
        .user_id_type(user_id_type) \
        .build()

    # 发起请求
    response: GetChatResponse = client.im.v1.chat.get(request)

    # 处理失败返回
    if not response.success():
        error_msg = f"获取群聊信息失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        if response.raw:
            error_msg += f", resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        lark.logger.error(error_msg)
        raise Exception(error_msg)

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))

    # 解析群聊信息
    data = response.data
    result = {
        "success": True,
        "avatar": getattr(data, 'avatar', ''),
        "name": getattr(data, 'name', ''),
        "description": getattr(data, 'description', ''),
        "i18n_names": getattr(data, 'i18n_names', {}),
        "add_member_permission": getattr(data, 'add_member_permission', ''),
        "share_card_permission": getattr(data, 'share_card_permission', ''),
        "at_all_permission": getattr(data, 'at_all_permission', ''),
        "edit_permission": getattr(data, 'edit_permission', ''),
        "owner_id_type": getattr(data, 'owner_id_type', ''),
        "owner_id": getattr(data, 'owner_id', ''),
        "user_manager_id_list": getattr(data, 'user_manager_id_list', []),
        "bot_manager_id_list": getattr(data, 'bot_manager_id_list', []),
        "group_message_type": getattr(data, 'group_message_type', ''),
        "chat_mode": getattr(data, 'chat_mode', ''),
        "chat_type": getattr(data, 'chat_type', ''),
        "chat_tag": getattr(data, 'chat_tag', ''),
        "join_message_visibility": getattr(data, 'join_message_visibility', ''),
        "leave_message_visibility": getattr(data, 'leave_message_visibility', ''),
        "membership_approval": getattr(data, 'membership_approval', ''),
        "moderation_permission": getattr(data, 'moderation_permission', ''),
        "external": getattr(data, 'external', False),
        "tenant_key": getattr(data, 'tenant_key', ''),
        "user_count": getattr(data, 'user_count', ''),
        "bot_count": getattr(data, 'bot_count', ''),
        "restricted_mode_setting": getattr(data, 'restricted_mode_setting', {}),
        "urgent_setting": getattr(data, 'urgent_setting', ''),
        "video_conference_setting": getattr(data, 'video_conference_setting', ''),
        "hide_member_count_setting": getattr(data, 'hide_member_count_setting', ''),
        "chat_status": getattr(data, 'chat_status', ''),
    }

    return result
