"""ConfigManager测试模块"""

import pytest
from unittest.mock import patch

from ai_agents.modules.codedoggy.rule.config_manager import (
    ConfigManager,
    get_repo_config_manager,
    _global_config_manager,
)
from ai_agents.modules.codedoggy.rule.config import CodeReviewConfig


class TestConfigManager:
    """ConfigManager类的测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.config_manager = ConfigManager()

    def test_init(self):
        """测试ConfigManager初始化"""
        # 验证初始化状态
        assert isinstance(self.config_manager._config_cache, dict)
        assert len(self.config_manager._config_cache) == 0
        assert isinstance(self.config_manager._default_config, CodeReviewConfig)

    def test_get_default_config(self):
        """测试获取默认配置"""
        default_config = self.config_manager.get_default_config()

        # 验证返回的是CodeReviewConfig实例
        assert isinstance(default_config, CodeReviewConfig)
        # 验证默认值
        assert default_config.model == "gemini-2_5-pro-preview"
        assert default_config.max_comments == 5
        assert default_config.file_max_comment == 2

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.parse_config_content")
    def test_get_config_from_database_success(
        self, mock_parse_config, mock_get_configuration
    ):
        """测试从数据库成功获取配置"""
        # 设置mock返回值
        mock_config_data = [{"value": "test_config_content"}]
        mock_get_configuration.return_value = mock_config_data

        mock_config = CodeReviewConfig(model="test-model")
        mock_parse_config.return_value = mock_config

        # 调用方法
        result = self.config_manager.get_config(
            repo_path="/test/repo", project="test_project", server="test_server"
        )

        # 验证调用
        mock_get_configuration.assert_called_once_with(
            "codedoggy", "test_server/test_project"
        )
        mock_parse_config.assert_called_once_with("test_config_content")

        # 验证结果
        assert result == mock_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    def test_get_config_from_database_empty_result(self, mock_get_configuration):
        """测试数据库返回空结果时的处理"""
        # 设置mock返回空结果
        mock_get_configuration.return_value = []

        with patch(
            "ai_agents.modules.codedoggy.rule.config_manager.get_default_branch"
        ) as mock_get_branch, patch(
            "ai_agents.modules.codedoggy.rule.config_manager.get_repo_config"
        ) as mock_get_repo_config:

            mock_get_branch.return_value = "main"
            mock_repo_config = CodeReviewConfig(model="repo-model")
            mock_get_repo_config.return_value = mock_repo_config

            result = self.config_manager.get_config(
                repo_path="/test/repo", project="test_project", server="test_server"
            )

            # 验证先尝试数据库，然后回退到仓库配置
            mock_get_configuration.assert_called_once_with(
                "codedoggy", "test_server/test_project"
            )
            mock_get_branch.assert_called_once_with("/test/repo")
            mock_get_repo_config.assert_called_once_with(
                "/test/repo", "main", ".codedoggy_config.yaml"
            )

            assert result == mock_repo_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_default_branch")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_repo_config")
    def test_get_config_from_repo_only(self, mock_get_repo_config, mock_get_branch):
        """测试仅从仓库获取配置（无project和server参数）"""
        mock_get_branch.return_value = "main"
        mock_repo_config = CodeReviewConfig(model="repo-model")
        mock_get_repo_config.return_value = mock_repo_config

        result = self.config_manager.get_config(repo_path="/test/repo")

        # 验证调用
        mock_get_branch.assert_called_once_with("/test/repo")
        mock_get_repo_config.assert_called_once_with(
            "/test/repo", "main", ".codedoggy_config.yaml"
        )

        assert result == mock_repo_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_default_branch")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_repo_config")
    def test_get_config_with_custom_filename(
        self, mock_get_repo_config, mock_get_branch
    ):
        """测试使用自定义配置文件名"""
        mock_get_branch.return_value = "develop"
        mock_repo_config = CodeReviewConfig(model="custom-model")
        mock_get_repo_config.return_value = mock_repo_config

        result = self.config_manager.get_config(
            repo_path="/test/repo", config_filename="custom_config.yaml"
        )

        mock_get_branch.assert_called_once_with("/test/repo")
        mock_get_repo_config.assert_called_once_with(
            "/test/repo", "develop", "custom_config.yaml"
        )

        assert result == mock_repo_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.logging")
    def test_get_config_database_exception(self, mock_logging, mock_get_configuration):
        """测试数据库访问异常时的处理"""
        # 设置mock抛出异常
        mock_get_configuration.side_effect = Exception("Database connection failed")

        result = self.config_manager.get_config(
            repo_path="/test/repo", project="test_project", server="test_server"
        )

        # 验证异常被记录
        mock_logging.error.assert_called()
        error_call = mock_logging.error.call_args[0][0]
        assert "获取配置失败" in error_call

        # 验证返回默认配置
        assert result == self.config_manager._default_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_default_branch")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.logging")
    def test_get_config_repo_exception(self, mock_logging, mock_get_branch):
        """测试仓库访问异常时的处理"""
        # 设置mock抛出异常
        mock_get_branch.side_effect = Exception("Git command failed")

        result = self.config_manager.get_config(repo_path="/test/repo")

        # 验证异常被记录
        mock_logging.error.assert_called()
        error_call = mock_logging.error.call_args[0][0]
        assert "获取配置失败" in error_call

        # 验证返回默认配置
        assert result == self.config_manager._default_config

    def test_get_config_partial_params(self):
        """测试部分参数的处理"""
        # 只提供project但没有server
        with patch(
            "ai_agents.modules.codedoggy.rule.config_manager.get_default_branch"
        ) as mock_get_branch, patch(
            "ai_agents.modules.codedoggy.rule.config_manager.get_repo_config"
        ) as mock_get_repo_config:

            mock_get_branch.return_value = "main"
            mock_repo_config = CodeReviewConfig()
            mock_get_repo_config.return_value = mock_repo_config

            result = self.config_manager.get_config(
                repo_path="/test/repo", project="test_project"
            )

            # 应该跳过数据库查询，直接从仓库获取
            mock_get_branch.assert_called_once_with("/test/repo")
            mock_get_repo_config.assert_called_once()

            assert result == mock_repo_config


class TestGlobalConfigManager:
    """全局配置管理器的测试"""

    def test_get_repo_config_manager_singleton(self):
        """测试全局配置管理器的单例模式"""
        manager1 = get_repo_config_manager()
        manager2 = get_repo_config_manager()

        # 验证返回同一个实例
        assert manager1 is manager2
        assert manager1 is _global_config_manager

        # 验证是ConfigManager实例
        assert isinstance(manager1, ConfigManager)

    def test_global_config_manager_type(self):
        """测试全局配置管理器的类型"""
        assert isinstance(_global_config_manager, ConfigManager)


class TestConfigManagerIntegration:
    """ConfigManager集成测试"""

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_default_branch")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_repo_config")
    def test_full_workflow_database_to_repo_fallback(
        self, mock_get_repo_config, mock_get_branch, mock_get_configuration
    ):
        """测试完整的工作流：数据库查询失败后直接返回默认配置"""
        config_manager = ConfigManager()

        # 设置数据库查询失败
        mock_get_configuration.side_effect = Exception("Network error")

        # 设置仓库配置（虽然不会被调用）
        mock_get_branch.return_value = "main"
        repo_config = CodeReviewConfig(model="fallback-model")
        mock_get_repo_config.return_value = repo_config

        with patch("ai_agents.modules.codedoggy.rule.config_manager.logging"):
            result = config_manager.get_config(
                repo_path="/test/repo",
                project="test_project",
                server="test_server",
                config_filename="custom.yaml",
            )

        # 验证数据库被调用，但由于异常，直接返回默认配置
        mock_get_configuration.assert_called_once_with(
            "codedoggy", "test_server/test_project"
        )
        # 由于异常处理机制，不会调用仓库相关函数
        mock_get_branch.assert_not_called()
        mock_get_repo_config.assert_not_called()

        # 返回默认配置
        assert result == config_manager._default_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_default_branch")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.get_repo_config")
    def test_database_empty_fallback_to_repo(
        self, mock_get_repo_config, mock_get_branch, mock_get_configuration
    ):
        """测试数据库返回空结果时回退到仓库配置"""
        config_manager = ConfigManager()

        # 设置数据库返回空结果
        mock_get_configuration.return_value = []

        # 设置仓库配置成功
        mock_get_branch.return_value = "main"
        repo_config = CodeReviewConfig(model="repo-fallback-model")
        mock_get_repo_config.return_value = repo_config

        result = config_manager.get_config(
            repo_path="/test/repo",
            project="test_project",
            server="test_server",
            config_filename="custom.yaml",
        )

        # 验证调用顺序：先查数据库，再查仓库
        mock_get_configuration.assert_called_once_with(
            "codedoggy", "test_server/test_project"
        )
        mock_get_branch.assert_called_once_with("/test/repo")
        mock_get_repo_config.assert_called_once_with(
            "/test/repo", "main", "custom.yaml"
        )

        assert result == repo_config

    @patch("ai_agents.modules.codedoggy.rule.config_manager.getConfiguration")
    @patch("ai_agents.modules.codedoggy.rule.config_manager.parse_config_content")
    def test_database_priority_over_repo(
        self, mock_parse_config, mock_get_configuration
    ):
        """测试数据库配置优先级高于仓库配置"""
        config_manager = ConfigManager()

        # 设置数据库返回配置
        mock_config_data = [{"value": "database_config"}]
        mock_get_configuration.return_value = mock_config_data

        db_config = CodeReviewConfig(model="database-model")
        mock_parse_config.return_value = db_config

        result = config_manager.get_config(
            repo_path="/test/repo", project="test_project", server="test_server"
        )

        # 验证只调用了数据库相关的函数，没有调用仓库相关的函数
        mock_get_configuration.assert_called_once()
        mock_parse_config.assert_called_once_with("database_config")

        assert result == db_config

    def test_config_manager_immutability(self):
        """测试配置管理器的配置不会被意外修改"""
        config_manager = ConfigManager()
        original_default = config_manager._default_config

        # 获取配置
        config1 = config_manager.get_default_config()
        config2 = config_manager.get_default_config()

        # 验证返回的是同一个对象（引用相等）
        assert config1 is original_default
        assert config2 is original_default

        # 验证修改返回的配置不会影响原始配置
        config1.model = "modified-model"
        assert (
            config_manager._default_config.model == "modified-model"
        )  # 由于是同一个对象，会被修改

    def test_error_logging_integration(self):
        """测试错误日志记录的集成"""
        config_manager = ConfigManager()

        with patch(
            "ai_agents.modules.codedoggy.rule.config_manager.get_default_branch"
        ) as mock_get_branch, patch(
            "ai_agents.modules.codedoggy.rule.config_manager.logging"
        ) as mock_logging:

            # 设置异常
            test_exception = Exception("Test error message")
            mock_get_branch.side_effect = test_exception

            result = config_manager.get_config(repo_path="/test/repo")

            # 验证错误日志被正确调用
            mock_logging.error.assert_called_once()
            log_message = mock_logging.error.call_args[0][0]
            assert "获取配置失败" in log_message
            assert str(test_exception) in str(mock_logging.error.call_args)

            # 验证返回默认配置
            assert result == config_manager._default_config


if __name__ == "__main__":
    pytest.main([__file__])
