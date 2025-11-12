import logging
import os
from typing import Dict

import yaml
from ai_agents.modules.codedoggy.client.portal import getConfiguration
from ai_agents.modules.codedoggy.git.branch import get_default_branch
from ai_agents.modules.codedoggy.rule.config import (
    CodeReviewConfig,
    get_default_config,
    get_repo_config,
    merge_config,
)


class ConfigManager:
    """配置管理器，负责加载、缓存和管理CodeDoggy配置"""

    def __init__(self):
        self._config_cache: Dict[str, CodeReviewConfig] = {}
        self._default_config = get_default_config()

    def get_config(
        self,
        repo_path: str,
        config_filename: str = ".codedoggy_config.yaml",
        project: str = None,
        server: str = None,
    ) -> CodeReviewConfig:
        """
            获取仓库配置

            Args:
                repo_path: 仓库路径
                config_filename: 配置文件名，默认为.codedoggy_config.yaml
                project: 项目名称，用于从数据库获取配置
                server: 服务器名称，用于从数据库获取配置

            Returns:
                CodeReviewConfig: 配置对象
        """
        benchmark = os.getenv('benchmark')
        if benchmark:
            _model = os.getenv('CODEDOGGY_BENCHMARK_MODEL', 'bailian-qwen3-coder-plus')
            return CodeReviewConfig(
                model=_model,
                max_comments=20,
                file_max_comment=10,
                scoring= {
                    "enabled": True,
                    "score": 3,
                }
            )

        try:
            db_config = None
            if project and server:
                # 优先从数据库中查询
                config_db = getConfiguration("codedoggy", f"""{server}/{project}""")
                if config_db and len(config_db) > 0:
                    try:
                        db_config = yaml.safe_load(config_db[0].get("value"))
                    except Exception as e:
                        logging.error(f"解析数据库配置失败: {e}")
            # 从仓库获取配置
            commit = get_default_branch(repo_path)
            config = get_repo_config(repo_path, commit, config_filename)
            if db_config:
                # 合并config
                merge_config(config, db_config)
            return config
        except Exception as e:
            logging.error(f"获取配置失败: {e}，返回默认配置")
            return self._default_config

    def get_default_config(self) -> CodeReviewConfig:
        """
        获取默认配置

        Returns:
            CodeReviewConfig: 默认配置对象
        """
        return self._default_config


# 全局配置管理器实例
_global_config_manager = ConfigManager()


def get_repo_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例

    Returns:
        ConfigManager: 配置管理器实例
    """
    return _global_config_manager
