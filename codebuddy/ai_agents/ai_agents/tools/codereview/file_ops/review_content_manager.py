"""
审查内容文件管理工具模块

专门用于管理代码审查过程中的内容文件，确保文件创建在正确的全局缓存目录中。
这些工具解决了原有create_new_file工具不能正确处理~路径的问题，确保审查内容文件
始终创建在用户主目录的全局缓存中，而不是当前工作目录。
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

def get_review_content_file_path(task_id: str) -> Path:
    """
    获取审查内容文件的完整路径。

    Args:
        task_id: 任务唯一标识

    Returns:
        Path: 审查内容文件的完整路径

    Raises:
        ValueError: 如果 task_id 格式不正确
    """
    if not task_id or not task_id.strip():
        raise ValueError("task_id 不能为空")

    # 验证 task_id 不包含危险字符
    dangerous_chars = ['/', '\\', '..', '$', '|', ';', '&', '`', '*', '?']
    if any(char in task_id for char in dangerous_chars):
        raise ValueError(f"task_id 包含非法字符: {task_id}")

    # 构建全局缓存目录路径
    cache_dir = Path("~/.cache/codeDoggy/review_content").expanduser()
    return cache_dir / f"{task_id}_content.json"


def create_review_content_file(
    task_id: str,
    content: Dict[Any, Any],
    overwrite: bool = True
) -> str:
    """
    创建审查内容文件，专门用于代码审查任务。

    这个工具专门用于CodeReview Supervisor Agent保存审查内容到全局缓存目录。
    与通用的create_new_file不同，这个工具：
    1. 自动处理~路径展开，确保文件创建在用户主目录的.cache中
    2. 强制使用标准的审查内容文件格式和路径
    3. 提供task_id格式验证和安全检查
    4. 自动创建必要的缓存目录结构

    使用场景：
    - CodeReview Supervisor在调用Review Agent前保存审查内容
    - 替代原有的create_new_file + 手动路径拼接的方式
    - 确保所有审查内容文件都在统一的全局缓存位置

    文件将创建在：~/.cache/codeDoggy/review_content/{task_id}_content.json

    Args:
        task_id: 任务唯一标识，格式如"20240618-153022-CR-0001"，用于生成文件名
        content: 要写入的审查内容，必须是包含以下结构的字典：
                {
                  "task_id": "任务ID",
                  "review_type": "审查类型(diff/file/directory等)",
                  "created_at": "创建时间",
                  "content": {
                    "diff_content": "diff内容",
                    "target_file": "目标文件路径",
                    "target_files": ["文件路径列表"],
                    "snippet_code": "代码片段",
                    // 根据review_type包含不同字段
                  }
                }
        overwrite: 是否覆盖已存在的文件，默认True（适合错误重试场景）

    Returns:
        str: 成功消息，包含文件路径和大小信息，格式："成功创建审查内容文件: /path/to/file，大小: X bytes"

    Raises:
        ValueError: 如果task_id格式不正确或content不是字典
        FileExistsError: 如果文件已存在且overwrite为False
        PermissionError: 如果权限不足创建目录或文件
        OSError: 如果文件系统操作失败

    Examples:
        # Supervisor调用Review Agent前保存审查内容
        >>> content = {
        ...     "task_id": "20240618-CR-0001",
        ...     "review_type": "diff",
        ...     "created_at": "2024-06-18T15:30:22Z",
        ...     "content": {
        ...         "diff_content": "diff --git a/src/main.py...",
        ...         "target_files": ["src/main.py", "src/utils.py"],
        ...         "commit_metadata": {"source_commit": "abc123"}
        ...     }
        ... }
        >>> result = create_review_content_file("20240618-CR-0001", content)
        >>> print(result)
        "成功创建审查内容文件: /home/user/.cache/codeDoggy/review_content/20240618-CR-0001_content.json，大小: 1024 bytes"
    """
    if not isinstance(content, dict):
        raise ValueError("content 必须是字典类型，应包含task_id、review_type、content等字段")

    try:
        # 获取文件路径
        file_path = get_review_content_file_path(task_id)

        # 检查文件是否已存在
        file_existed = file_path.exists()
        if file_existed and not overwrite:
            raise FileExistsError(f"审查内容文件已存在: {file_path}。如需覆盖请设置overwrite=True")

        # 创建父目录
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"确保审查内容缓存目录存在: {file_path.parent}")

        # 写入JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        # 获取文件大小
        file_size = file_path.stat().st_size

        # 记录日志
        action = "覆盖" if file_existed and overwrite else "创建"
        logging.info(f"{action}审查内容文件: {file_path} ({file_size} bytes)")

        return f"成功{action}审查内容文件: {file_path}，大小: {file_size} bytes"

    except PermissionError as e:
        error_msg = f"创建审查内容文件权限不足 '{task_id}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e
    except OSError as e:
        error_msg = f"创建审查内容文件失败 '{task_id}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e
    except (TypeError, ValueError) as e:
        error_msg = f"序列化审查内容失败 '{task_id}': {e}"
        logging.error(error_msg)
        raise ValueError(error_msg) from e


def read_review_content_file(task_id: str) -> Dict[Any, Any]:
    """
    读取审查内容文件，专门用于Review Agent和Verify Agent获取审查内容。

    这个工具专门用于micro agents从全局缓存中读取Supervisor保存的审查内容。
    使用场景：
    - Review Agent从缓存文件中读取要审查的代码/diff内容
    - Verify Agent读取原始审查内容进行验证
    - 替代直接使用read_file_content + 手动路径拼接的方式
    - 当文件不存在时，agents应返回MISSING_CODE错误给Supervisor

    工作流程：
    1. Agent接收到包含task_id的任务参数
    2. 使用此工具读取对应的审查内容文件
    3. 根据review_type提取相应的内容字段进行处理
    4. 如果文件不存在，返回错误JSON给Supervisor重新保存

    从缓存文件路径读取：~/.cache/codeDoggy/review_content/{task_id}_content.json

    Args:
        task_id: 任务唯一标识，必须与Supervisor分配的task_id完全一致

    Returns:
        Dict[Any, Any]: 解析后的审查内容，包含完整的内容结构：
                       {
                         "task_id": "任务ID",
                         "review_type": "审查类型",
                         "created_at": "创建时间",
                         "content": {
                           // 根据review_type包含不同的内容字段
                           "diff_content": "diff内容",      # diff模式
                           "target_file": "文件路径",       # file模式
                           "target_files": ["文件列表"],    # file_list模式
                           "review_scope": ["目录列表"],    # directory模式
                           "snippet_code": "代码片段"       # snippet模式
                         }
                       }

    Raises:
        ValueError: 如果task_id格式不正确
        FileNotFoundError: 如果审查内容文件不存在（Agent应返回MISSING_CODE错误）
        PermissionError: 如果权限不足读取文件
        json.JSONDecodeError: 如果文件JSON格式错误（Agent应返回INVALID_FORMAT错误）
        OSError: 如果文件系统操作失败

    Examples:
        # Review Agent读取审查内容
        >>> try:
        ...     content = read_review_content_file("20240618-CR-0001")
        ...     review_type = content["review_type"]
        ...     if review_type == "diff":
        ...         diff_content = content["content"]["diff_content"]
        ...         # 进行diff审查...
        ... except FileNotFoundError:
        ...     # 返回MISSING_CODE错误给Supervisor
        ...     return {"status": "ERROR", "error_type": "MISSING_CODE", "message": "审查内容文件不存在"}

        # Verify Agent读取内容进行验证
        >>> content = read_review_content_file("20240618-CR-0001")
        >>> original_files = content["content"].get("target_files", [])
        >>> # 基于原始内容验证Review结果...
    """
    try:
        # 获取文件路径
        file_path = get_review_content_file_path(task_id)

        # 检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(f"审查内容文件不存在: {file_path}。Agent应返回MISSING_CODE错误给Supervisor重新保存文件。")

        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")

        # 读取并解析JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        # 验证基本结构
        if not isinstance(content, dict):
            raise ValueError("审查内容文件格式错误: 根节点必须是字典")

        # 验证必要字段
        required_fields = ["task_id", "review_type", "content"]
        missing_fields = [field for field in required_fields if field not in content]
        if missing_fields:
            raise ValueError(f"审查内容文件缺少必要字段: {missing_fields}")

        # 验证文件内容中的task_id是否匹配
        file_task_id = content.get("task_id")
        if file_task_id != task_id:
            logging.warning(f"文件内容中的task_id ({file_task_id}) 与请求的task_id ({task_id}) 不匹配")

        logging.info(f"成功读取审查内容文件: {file_path}, review_type: {content.get('review_type')}")
        return content

    except FileNotFoundError:
        raise
    except PermissionError as e:
        error_msg = f"读取审查内容文件权限不足 '{task_id}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"审查内容文件JSON格式错误 '{task_id}': {e}"
        logging.error(error_msg)
        raise json.JSONDecodeError(error_msg, e.doc, e.pos) from e
    except OSError as e:
        error_msg = f"读取审查内容文件失败 '{task_id}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e

def update_review_content_file_with_result(
    task_id: str,
    result_type: str,
    result_data: any
) -> str:
    """
    更新审查内容文件，添加Agent处理结果。

    用于Supervisor在各个Agent完成后，将其结果添加到审查内容文件中，
    形成包含完整处理上下文的文件，供后续Agent使用或最终结果合并。

    智能类型处理：
    - 如果 result_data 是字符串，尝试解析为JSON
    - 如果 result_data 是字典，直接使用
    - 如果解析失败，抛出明确的错误信息

    Args:
        task_id: 任务唯一标识
        result_type: 结果类型，支持 "review_result" 或 "verify_result"
        result_data: Agent返回的结果，可以是字典或JSON字符串

    Returns:
        str: 更新操作的结果描述

    Raises:
        ValueError: 如果参数格式不正确
        FileNotFoundError: 如果审查内容文件不存在
        OSError: 如果文件操作失败

    Examples:
        # 添加Review Agent结果（字典格式）
        >>> update_review_content_file_with_result("20240618-CR-0001", "review_result", review_agent_dict)

        # 添加Review Agent结果（JSON字符串格式）
        >>> update_review_content_file_with_result("20240618-CR-0001", "review_result", review_agent_json_str)
    """
    # 智能类型处理
    if isinstance(result_data, str):
        try:
            parsed_result = json.loads(result_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"result_data 是无效的JSON字符串: {e}")
    elif isinstance(result_data, dict):
        parsed_result = result_data
    else:
        raise ValueError(f"result_data 必须是字典或JSON字符串，实际类型: {type(result_data)}")

    if result_type not in ["review_result", "verify_result"]:
        raise ValueError("result_type 必须是 'review_result' 或 'verify_result'")

    try:
        # 读取现有文件内容
        existing_content = read_review_content_file(task_id)

        # 添加结果到文件中
        existing_content[result_type] = parsed_result
        # 添加时间戳
        from datetime import datetime
        existing_content[result_type]["completed_at"] = datetime.utcnow().isoformat() + "Z"

        # 写回文件
        file_path = get_review_content_file_path(task_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_content, f, ensure_ascii=False, indent=2)

        file_size = file_path.stat().st_size
        logging.info(f"成功更新审查内容文件(添加{result_type}): {file_path} ({file_size} bytes)")

        return f"成功更新审查内容文件(添加{result_type}): {file_path}，大小: {file_size} bytes"

    except Exception as e:
        error_msg = f"更新审查内容文件失败({result_type}) '{task_id}': {e}"
        logging.error(error_msg)
        raise type(e)(error_msg) from e
