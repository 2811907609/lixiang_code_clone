"""
飞书（Lark）客户端初始化和管理模块
"""

import json
from typing import Optional, List, Dict, Any
import lark_oapi as lark
from lark_oapi.api.im.v1 import SearchChatRequest, SearchChatResponse
from opcli.config import config


def init_feishu_client(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    log_level: Optional[lark.LogLevel] = None
) -> lark.Client:
    """
    初始化飞书客户端

    Args:
        app_id: 飞书应用 ID，如果不提供则从配置中获取
        app_secret: 飞书应用密钥，如果不提供则从配置中获取
        log_level: 日志级别，如果不提供则从配置中获取

    Returns:
        lark.Client: 配置好的飞书客户端实例

    Raises:
        ValueError: 当 app_id 或 app_secret 未提供且配置中也未设置时抛出
    """
    # 从参数或配置获取认证信息
    app_id = app_id or config.FEISHU_APP_ID
    app_secret = app_secret or config.FEISHU_APP_SECRET

    # 获取日志级别
    if log_level is None:
        log_level_str = config.FEISHU_LOG_LEVEL.upper()
        if log_level_str == "DEBUG":
            log_level = lark.LogLevel.DEBUG
        elif log_level_str == "INFO":
            log_level = lark.LogLevel.INFO
        elif log_level_str == "WARN":
            log_level = lark.LogLevel.WARN
        elif log_level_str == "ERROR":
            log_level = lark.LogLevel.ERROR
        else:
            log_level = lark.LogLevel.DEBUG

    if not app_id:
        raise ValueError("app_id 必须提供，可通过参数或环境变量 FEISHU_APP_ID 设置")

    if not app_secret:
        raise ValueError("app_secret 必须提供，可通过参数或环境变量 FEISHU_APP_SECRET 设置")

    # 使用 builder 模式创建客户端
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(log_level) \
        .build()

    return client


def create_feishu_client_from_config() -> lark.Client:
    """
    从配置创建飞书客户端的便捷函数

    Returns:
        lark.Client: 配置好的飞书客户端实例

    Raises:
        ValueError: 当必需的配置未设置时抛出
    """
    return init_feishu_client()


# 创建全局客户端实例（延迟初始化）
_client: Optional[lark.Client] = None


def get_feishu_client() -> lark.Client:
    """
    获取全局飞书客户端实例（单例模式）

    Returns:
        lark.Client: 飞书客户端实例

    Raises:
        ValueError: 当配置未正确设置时抛出
    """
    global _client
    if _client is None:
        _client = create_feishu_client_from_config()
    return _client



def search_chats(
    client: Optional[lark.Client] = None,
    query: str = "",
    user_id_type: str = "open_id",
    page_token: str = "",
    page_size: int = 10
) -> Dict[str, Any]:
    """
    搜索群聊

    Args:
        client: 飞书客户端实例，如果不提供则使用全局客户端
        query: 搜索关键词
        user_id_type: 用户ID类型，默认为 "open_id"
        page_token: 分页token，用于获取下一页结果
        page_size: 每页结果数量，默认为10

    Returns:
        Dict[str, Any]: 搜索结果，包含群聊信息和分页数据

    Raises:
        ValueError: 当客户端未正确初始化时抛出
        Exception: 当API调用失败时抛出
    """
    # 获取客户端实例
    if client is None:
        client = get_feishu_client()

    # 构造请求对象
    request: SearchChatRequest = SearchChatRequest.builder() \
        .user_id_type(user_id_type) \
        .query(query) \
        .page_token(page_token) \
        .page_size(page_size) \
        .build()

    # 发起请求
    response: SearchChatResponse = client.im.v1.chat.search(request)

    # 处理失败返回
    if not response.success():
        error_msg = f"搜索群聊失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        if response.raw:
            error_msg += f", resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        lark.logger.error(error_msg)
        raise Exception(error_msg)

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))

    result = {
        "success": True,
        "data": response.data,
        "has_more": response.data.has_more if response.data else False,
        "page_token": response.data.page_token if response.data else "",
        "items": []
    }

    # 解析群聊列表
    if response.data and response.data.items:
        for item in response.data.items:
            chat_info = {
                "chat_id": getattr(item, 'chat_id', ''),
                "name": getattr(item, 'name', ''),
                "description": getattr(item, 'description', ''),
                "avatar": getattr(item, 'avatar', ''),
                "owner_id": getattr(item, 'owner_id', ''),
                "owner_id_type": getattr(item, 'owner_id_type', ''),
                "external": getattr(item, 'external', False),
                "tenant_key": getattr(item, 'tenant_key', ''),
                "chat_status": getattr(item, 'chat_status', ''),
                # 以下字段可能不存在，使用安全的默认值
                "chat_type": getattr(item, 'chat_type', ''),
                "chat_mode": getattr(item, 'chat_mode', ''),
                "chat_biz_id": getattr(item, 'chat_biz_id', ''),
                "admin_ids": getattr(item, 'admin_ids', []),
                "member_count": getattr(item, 'member_count', 0),
                "add_member_permission": getattr(item, 'add_member_permission', ''),
                "share_card_permission": getattr(item, 'share_card_permission', ''),
                "at_all_permission": getattr(item, 'at_all_permission', ''),
                "edit_permission": getattr(item, 'edit_permission', ''),
                "join_permission": getattr(item, 'join_permission', ''),
                "status": getattr(item, 'status', ''),
                "create_time": getattr(item, 'create_time', ''),
                "update_time": getattr(item, 'update_time', ''),
            }
            result["items"].append(chat_info)

    return result


def search_groups_by_name(
    group_name: str,
    client: Optional[lark.Client] = None,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    根据群名称搜索群聊的便捷函数

    Args:
        group_name: 群名称关键词
        client: 飞书客户端实例，如果不提供则使用全局客户端
        max_results: 最大结果数量

    Returns:
        List[Dict[str, Any]]: 匹配的群聊列表
    """
    all_groups = []
    page_token = ""
    page_size = min(50, max_results)  # 每页最多50个

    while len(all_groups) < max_results:
        current_page_size = min(page_size, max_results - len(all_groups))

        try:
            result = search_chats(
                client=client,
                query=group_name,
                page_token=page_token,
                page_size=current_page_size
            )

            if result["items"]:
                all_groups.extend(result["items"])

            # 检查是否还有更多结果
            if not result.get("has_more", False) or not result.get("page_token"):
                break

            page_token = result["page_token"]

        except Exception as e:
            lark.logger.error(f"搜索群聊时发生错误: {e}")
            break

    return all_groups[:max_results]
