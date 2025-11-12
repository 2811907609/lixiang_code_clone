import logging
from dataclasses import dataclass, field, fields
from typing import Any, Dict

import yaml
from ai_agents.tools.git import check_git_file_exists, get_git_file_content


@dataclass
class CodeReviewConfig:
    """CodeDoggy代码审查配置类"""

    model: str = "gemini-2_5-pro-preview"

    max_comments: int = 5
    file_max_comment: int = 2

    # 忽略配置
    should_review_patterns: list = field(
        default_factory=lambda: [
            r".*\.go$",
            r".*\.py$",
            r".*\.java$",
            r".*\.c$",
            r".*\.sql$",
            r".*\.rs$",
            r".*\.tsx$",
            r".*\.jsx$",
            r".*\.vue$",
            r".*\.kt$",
            r".*\.scala$",
            r".*\.md$",
            r".*\.php$",
            r".*\.cpp$",
            r".*\.h$",
            r".*\.hpp$",
            r".*\.cc$",
            r".*\.sh$",
        ]
    )

    # 自定义规则
    custom_rules: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "rules": [],
        }
    )

    # 评分配置
    scoring: Dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": True,
            "score": 7,
        }
    )

    auto_code_review_score: Dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": False,
            "score": 1,
        }
    )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "CodeReviewConfig":
        """从字典创建配置对象，解析失败时使用默认值"""
        default_config = get_default_config()
        try:
            model = config_dict.get("model", default_config.model)
            if not isinstance(model, str):
                model = "gemini-2_5-pro-preview"

            review_config = config_dict.get("review", None)
            if review_config is None or not isinstance(review_config, dict):
                max_comments = default_config.max_comments
                file_max_comment = default_config.file_max_comment
            else:
                max_comments = review_config.get(
                    "max_comments", default_config.max_comments
                )
                file_max_comment = review_config.get(
                    "file_max_comment", default_config.file_max_comment
                )

            should_review_config = config_dict.get("should_review", None)
            if should_review_config is None or not isinstance(
                should_review_config, dict
            ):
                patterns = default_config.should_review_patterns
            else:
                patterns = should_review_config.get(
                    "patterns", default_config.should_review_patterns
                )

            custom_config = config_dict.get("custom_rules", default_config.custom_rules)
            if not isinstance(custom_config, dict):
                custom_config = default_config.custom_rules

            scoring_config = config_dict.get("scoring", default_config.scoring)
            if not isinstance(scoring_config, dict):
                scoring_config = default_config.scoring

            auto_code_review_score = config_dict.get(
                "auto_code_review_score", default_config.auto_code_review_score
            )
            if not isinstance(auto_code_review_score, dict):
                auto_code_review_score = default_config.auto_code_review_score

            return cls(
                model=model,
                max_comments=max_comments,
                file_max_comment=file_max_comment,
                should_review_patterns=patterns,
                custom_rules=custom_config,
                scoring=scoring_config,
                auto_code_review_score=auto_code_review_score,
            )
        except Exception as e:
            logging.error(f"解析配置字典失败: {e}，返回默认配置")
            return cls()  # 返回默认配置


def parse_config_content(
    config_content: str,
) -> CodeReviewConfig:
    """
    解析YAML配置文件内容，如果解析失败或配置无效则返回默认配置

    Args:
        config_content: YAML格式的配置文件内容

    Returns:
        CodeReviewConfig: 解析后的配置对象，如果解析失败或配置无效则返回默认配置
    """
    try:
        config_dict = yaml.safe_load(config_content)
        if config_dict is None:
            logging.warning("配置文件为空，使用默认配置")
            return get_default_config()
        # 尝试从字典创建配置对象
        config = CodeReviewConfig.from_dict(config_dict)
        return config
    except yaml.YAMLError as e:
        logging.error(f"解析YAML配置文件失败: {e}，使用默认配置")
        return get_default_config()
    except Exception as e:
        logging.error(f"解析配置内容时出现未知错误: {e}，使用默认配置")
        return get_default_config()


def get_default_config() -> CodeReviewConfig:
    """
    获取默认配置，从 default_config.yaml 文件加载

    Returns:
        CodeReviewConfig: 默认配置对象
    """
    return CodeReviewConfig()


def get_repo_config(
    repo_path: str,
    commit: str = "HEAD",
    config_filename: str = ".codedoggy_config.yaml",
) -> CodeReviewConfig:
    """
    从Git仓库中获取配置文件，如果配置文件不存在、解析失败或验证失败则返回默认配置

    Args:
        repo_path: 仓库路径
        commit: Git提交标识符，默认为HEAD
        config_filename: 配置文件名，默认为.codedoggy_config.yaml

    Returns:
        CodeReviewConfig: 配置对象，如果配置无效则返回默认配置
    """
    try:
        if not repo_path:
            return get_default_config()

        # 检查配置文件是否存在
        if not check_git_file_exists(repo_path, config_filename, commit):
            logging.info(
                f"配置文件 {config_filename} 在仓库 {repo_path} 的提交 {commit} 中不存在，使用默认配置"
            )
            return get_default_config()

        # 读取配置文件内容
        config_content = get_git_file_content(repo_path, config_filename, commit)
        logging.info(f"成功读取配置文件 {config_filename} 从仓库 {repo_path}")
        config = parse_config_content(config_content)
        return config
    except Exception as e:
        logging.error(f"获取仓库配置失败: {e}，使用默认配置")
        return get_default_config()


def merge_config(target, source_dict):
    """
    根据source_dict中的键值对覆盖target对象的相同字段
    只有当target对象存在对应字段时才进行覆盖

    Args:
        target: 目标对象（被覆盖）
        source_dict: 源字典，包含要覆盖的字段名和值
    """
    # 获取目标对象的所有字段名
    target_field_names = {field.name for field in fields(target)}

    for field_name, source_value in source_dict.items():
        # 检查目标对象是否有这个字段
        if field_name not in target_field_names:
            continue

        # 跳过空值
        if is_empty_value(source_value):
            continue

        # 直接覆盖字段值
        setattr(target, field_name, source_value)


def is_empty_value(value):
    """判断值是否为空"""
    if value is None:
        return True
    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return True
    return False
