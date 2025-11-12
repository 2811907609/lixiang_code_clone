import logging
import re
import subprocess
"""
    提供各种语言静态分析工具，使用reviewdog来过滤，只保留diff的静态问题
"""

staticToolMap = {
    "Go": "staticcheck",
}

staticToolCmdMap = {
    "Go":
        'staticcheck ./... | reviewdog -efm="%%f:%%l:%%c: %%m" -diff="git diff %s %s"',
}


def static_check(language: str, repo_path: str, source_ref: str,
                 target_ref: str):
    """
    根据语言类型调用相应的静态检查工具

    参数:
        language (str): 编程语言
        repo_path (str): 代码仓库路径
        source_ref (str): 源提交引用
        target_ref (str): 目标提交引用

    返回:
        list: 静态检查结果列表
    """
    try:
        if language == "Go":
            return go_static_check(language, repo_path, source_ref, target_ref)
        elif language == "Python":
            return []
        elif language in ["JavaScript", "TypeScript"]:
            return []
        else:
            logging.warning("不支持的语言类型: %s", language)
            return []
    except Exception as e:
        logging.error("静态检查出错: %s", e)
        return []


def is_tool_available(tool_name):
    try:
        subprocess.run(
            [tool_name, "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_tool_exist(language: str):
    tool = staticToolMap.get(language, "")
    if not tool:
        return False
    return is_tool_available(tool)


def check_review_dog_exist():
    return is_tool_available("reviewdog")


# 通用的静态检查函数
def _run_static_check(language: str, repo_path: str, source_ref: str,
                      target_ref: str):
    is_tool_exist = check_tool_exist(language=language)
    is_review_dog = check_review_dog_exist()
    if not is_tool_exist or not is_review_dog:
        logging.warning("tool is not exist")
        return []
    cmd = staticToolCmdMap.get(language, "")
    if not cmd:
        logging.warning("cmd is not exist")
        return []
    cmd = cmd % (source_ref, target_ref)
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        check=True,
        cwd=repo_path,
        timeout=5 * 60,
    )
    logging.info("cmd %s", cmd)
    logging.info("res %s", res)
    if res.stdout:
        return res.stdout.decode().split("\n")
    return []


# 各语言的静态检查实现
def go_static_check(language: str, repo_path: str, source_ref: str,
                    target_ref: str):
    """Go语言静态检查"""
    return _run_static_check(language, repo_path, source_ref, target_ref)


def python_static_check(language: str, repo_path: str, source_ref: str,
                        target_ref: str):
    """Python语言静态检查"""
    return _run_static_check(language, repo_path, source_ref, target_ref)


def js_ts_static_check(language: str, repo_path: str, source_ref: str,
                       target_ref: str):
    """JavaScript/TypeScript语言静态检查"""
    return _run_static_check(language, repo_path, source_ref, target_ref)


def parse_static_check_errors(language: str, error_list: list) -> list:
    """
    根据不同的语言解析静态检查的错误列表

    Args:
        language (str): 编程语言类型
        error_list (list): 静态检查错误列表

    Returns:
        list: 解析后的错误信息列表，每个元素包含文件路径、行号、错误信息等
    """
    if not error_list:
        return []

    # 去除空字符串
    error_list = [error for error in error_list if error.strip()]

    # 去重
    error_list = list(set(error_list))

    if language == "Go":
        return parse_go_static_check_errors(error_list)

    return []


def parse_go_static_check_errors(error_list: list) -> list:
    """
    解析Go语言静态检查的错误

    Args:
        error_list (list): Go静态检查错误列表

    Returns:
        list: 解析后的错误信息列表，每个元素是一个字典，包含文件路径、行号、错误信息等
    """
    result = []
    for error in error_list:
        try:
            # 匹配格式: 文件路径:行号:列号: 错误信息 (错误类型)
            # 或 文件路径:行号: 错误信息 (错误类型)
            match = re.match(r"^(.*?):(\d+)(?::(\d+))?: (.*)$", error)

            if not match:
                continue

            file_path = match.group(1)
            line_num = int(match.group(2))

            # 提取错误信息
            error_message = match.group(4).strip()
            result.append(
                {
                    "relevantFile": file_path,
                    "suggestionLine": line_num,
                    "message": f"静态检查错误：{error_message}",
                }
            )
        except Exception as e:
            logging.error("解析Go静态检查错误失败: %s, 错误: %s", error, e)
            continue

    return result
