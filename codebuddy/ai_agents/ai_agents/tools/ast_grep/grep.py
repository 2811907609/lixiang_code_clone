import logging
import tempfile
import os
import subprocess
import json

language_grep_map = {
    "Go": "go_grep.yaml",
    "go": "go_grep.yaml",
    "TypeScript": "ts_grep.yaml",
    "ts": "ts_grep.yaml",
    "py": "py_grep.yaml",
    "Python": "pr_grep.yaml",
}


def grep_func_content_by_keywords(
    repo_path: str,
    keyword: str,
    language: str,
) -> str:
    """
    使用AST语法树分析搜索代码仓库中的函数/结构体完整定义及其调用上下文。

    本工具基于ast-grep，能够根据语法结构准确识别并提取完整的代码块，而非简单的文本匹配。

    使用场景：
    * 需要了解函数签名、参数、返回值或实现逻辑
    * 需要查看结构体完整定义及其字段
    * 需要理解特定代码在项目中的使用方式

    特性与限制:
    1. 当前支持的编程语言: Go(go)、TypeScript(ts)、Python(py)
    2. 搜索时请使用精确的函数名或结构体名作为关键词
    3. 返回匹配到的完整代码块(如整个函数定义、结构体定义)
    4. 也能识别关键词在代码中被调用的上下文


    Args:
        repo_path: 代码仓库的绝对路径，格式为'/xx/xx/xx'
        keyword: 搜索关键词，应为精确的函数名或结构体名(不含语言关键字如func/type等)
        language: 编程语言，目前支持 'go'/'Go' 、 'ts'/'TypeScript'、'py'/'Python'

    Returns:
        list[dict]: 包含匹配结果的列表，每个元素为字典，包含以下字段:
            - file_path: 文件相对路径
            - content: 匹配到的完整代码块内容
    """

    if not repo_path:
        raise ValueError("repo_path is required")
    if not keyword:
        raise ValueError("keyword is required")
    if not language:
        raise ValueError("language is required")

    rule_suffix = language_grep_map.get(language, "")
    if not rule_suffix:
        raise ValueError(f"language {language} is not supported")
    rule_dir = os.path.dirname(os.path.abspath(__file__))
    rule_path = os.path.join(rule_dir, "grep_config", rule_suffix)
    if not rule_path or not os.path.exists(rule_path):
        raise FileNotFoundError(f"YAML file not found: {rule_path}")

    with open(rule_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("{WORDS}", str(keyword))
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="processed_",
        delete=False,
        encoding="utf-8",
        dir=os.path.join(rule_dir, "grep_config"),
) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    logging.info("temp_path: %s", temp_path)
    cmd = [
        "ast-grep",
        "scan",
        repo_path,
        "-r",
        temp_path,
        "--json=compact",
    ]
    try:
        # 执行命令并捕获输出
        grep_data = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        grep_data_json = json.loads(grep_data.stdout)
        result = []
        for data in grep_data_json:
            result.append(
                {"file_path": data.get("file", ""), "content": data.get("text", "")}
            )
        return result
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # ast grep 未找到匹配
            return ""
        raise RuntimeError(f"grep error: {e.stderr}") from e
    finally:
        os.unlink(temp_path)
