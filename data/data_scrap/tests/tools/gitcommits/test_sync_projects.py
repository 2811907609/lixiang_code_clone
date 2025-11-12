import os
import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from data_scrap.tools.gitcommits.scrap_state import RepoStatusManager
from data_scrap.tools.gitcommits.sync_projects import ProjectSync


@dataclass
class MockRepoInfo:
    """模拟 repoutils.repo.RepoInfo 类"""
    full_name: str
    clone_url: str


class TestProjectSync:

    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 创建临时目录和文件路径，但不创建文件
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(self.temp_dir, 'test.duckdb')

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_basic(self, mock_gitlab_provider_class):
        """测试基本的同步所有仓库功能"""
        # 准备模拟数据
        mock_repos = [
            MockRepoInfo(full_name="group1/repo1", clone_url="https://gitlab.com/group1/repo1.git"),
            MockRepoInfo(full_name="group1/repo2", clone_url="https://gitlab.com/group1/repo2.git"),
            MockRepoInfo(full_name="group2/repo3", clone_url="https://gitlab.com/group2/repo3.git"),
        ]

        # 模拟 GitLabProvider
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter(mock_repos)
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(
            gitlab_url="https://gitlab.example.com",
            gitlab_token="test-token",
            db_path=self.temp_db_path
        )

        # 执行同步
        result = sync.sync_all_repos(page_size=50, limit=None)

        # 验证结果
        assert result == 3  # 添加了3个新仓库

        # 验证 GitLabProvider 的调用
        mock_gitlab_provider_class.assert_called_once_with(
            "https://gitlab.example.com",
            "test-token"
        )
        mock_provider.list_repos.assert_called_once_with(page_size=50, limit=None)

        # 验证数据库中的数据
        with RepoStatusManager(self.temp_db_path) as state_manager:
            stats = state_manager.get_stats()
            assert stats['total'] == 3
            assert stats['pending'] == 3

            # 验证具体的仓库数据
            repo1_status = state_manager.get_repo_status("group1/repo1")
            assert repo1_status is not None
            assert repo1_status['repo_name'] == "group1/repo1"
            assert repo1_status['repo_url'] == "https://gitlab.com/group1/repo1.git"
            assert repo1_status['status'] == 'pending'

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_with_existing_repos(self, mock_gitlab_provider_class):
        """测试同步时有已存在仓库的情况"""
        # 准备模拟数据
        mock_repos = [
            MockRepoInfo(full_name="group1/repo1", clone_url="https://gitlab.com/group1/repo1.git"),
            MockRepoInfo(full_name="group1/repo2", clone_url="https://gitlab.com/group1/repo2.git"),
        ]

        # 模拟 GitLabProvider
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter(mock_repos)
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(db_path=self.temp_db_path)

        # 预先添加一个仓库
        with RepoStatusManager(self.temp_db_path) as state_manager:
            state_manager.add_repo("group1/repo1", "https://gitlab.com/group1/repo1.git")

        # 执行同步
        result = sync.sync_all_repos()

        # 验证结果 - 只添加了1个新仓库（repo1已存在）
        assert result == 1

        # 验证数据库中的数据
        with RepoStatusManager(self.temp_db_path) as state_manager:
            stats = state_manager.get_stats()
            assert stats['total'] == 2

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_with_limit(self, mock_gitlab_provider_class):
        """测试带限制的同步"""
        # 准备模拟数据
        mock_repos = [
            MockRepoInfo(full_name=f"group1/repo{i}", clone_url=f"https://gitlab.com/group1/repo{i}.git")
            for i in range(1, 6)  # 5个仓库
        ]

        # 模拟 GitLabProvider
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter(mock_repos)
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(db_path=self.temp_db_path)

        # 执行同步，限制为3个
        result = sync.sync_all_repos(limit=3)

        # 验证结果
        assert result == 5  # 实际还是会处理所有返回的仓库

        # 验证 list_repos 调用参数
        mock_provider.list_repos.assert_called_once_with(page_size=100, limit=3)

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_provider_exception(self, mock_gitlab_provider_class):
        """测试 GitLab Provider 抛异常的情况"""
        # 模拟 GitLabProvider 抛异常
        mock_provider = MagicMock()
        mock_provider.list_repos.side_effect = Exception("GitLab API error")
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(db_path=self.temp_db_path)

        # 执行同步，应该抛异常
        with pytest.raises(Exception, match="GitLab API error"):
            sync.sync_all_repos()

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_empty_result(self, mock_gitlab_provider_class):
        """测试没有仓库返回的情况"""
        # 模拟 GitLabProvider 返回空列表
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter([])
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(db_path=self.temp_db_path)

        # 执行同步
        result = sync.sync_all_repos()

        # 验证结果
        assert result == 0

        # 验证数据库状态
        with RepoStatusManager(self.temp_db_path) as state_manager:
            stats = state_manager.get_stats()
            assert stats['total'] == 0

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    @patch('data_scrap.tools.gitcommits.sync_projects.logger')
    def test_sync_all_repos_logging(self, mock_logger, mock_gitlab_provider_class):
        """测试日志记录功能"""
        # 准备模拟数据
        mock_repos = [
            MockRepoInfo(full_name="group1/repo1", clone_url="https://gitlab.com/group1/repo1.git"),
        ]

        # 模拟 GitLabProvider
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter(mock_repos)
        mock_gitlab_provider_class.return_value = mock_provider

        # 创建 ProjectSync 实例
        sync = ProjectSync(db_path=self.temp_db_path)

        # 执行同步
        _ = sync.sync_all_repos()

        # 验证日志调用
        mock_logger.info.assert_any_call("Starting repository sync from GitLab")
        mock_logger.info.assert_any_call("Added new repo: group1/repo1")
        mock_logger.info.assert_any_call("Sync completed. Added 1 new repositories")

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_sync_all_repos_database_add_failure(self, mock_gitlab_provider_class):
        """测试数据库添加失败的情况"""
        # 准备模拟数据
        mock_repos = [
            MockRepoInfo(full_name="group1/repo1", clone_url="https://gitlab.com/group1/repo1.git"),
        ]

        # 模拟 GitLabProvider
        mock_provider = MagicMock()
        mock_provider.list_repos.return_value = iter(mock_repos)
        mock_gitlab_provider_class.return_value = mock_provider

        # 模拟数据库添加失败（返回 None）
        with patch.object(RepoStatusManager, 'add_repo', return_value=None):
            # 创建 ProjectSync 实例
            sync = ProjectSync(db_path=self.temp_db_path)

            # 执行同步
            result = sync.sync_all_repos()

            # 验证结果 - 没有成功添加仓库
            assert result == 0




class TestProjectSyncInit:

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    @patch('data_scrap.tools.gitcommits.sync_projects.config')
    def test_project_sync_init_with_defaults(self, mock_config, mock_gitlab_provider_class):
        """测试使用默认配置初始化 ProjectSync"""
        # 模拟配置
        mock_config.GITLAB_URL = "https://gitlab.default.com"
        mock_config.GITLAB_TOKEN = "default-token"
        mock_config.REPO_DB_PATH = "default.duckdb"

        # 创建实例
        sync = ProjectSync()

        # 验证属性
        assert sync.gitlab_url == "https://gitlab.default.com"
        assert sync.gitlab_token == "default-token"
        assert sync.db_path == "default.duckdb"

        # 验证 GitLabProvider 创建
        mock_gitlab_provider_class.assert_called_once_with(
            "https://gitlab.default.com",
            "default-token"
        )

    @patch('data_scrap.tools.gitcommits.sync_projects.GitLabProvider')
    def test_project_sync_init_with_custom_params(self, mock_gitlab_provider_class):
        """测试使用自定义参数初始化 ProjectSync"""
        # 创建实例
        sync = ProjectSync(
            gitlab_url="https://custom.gitlab.com",
            gitlab_token="custom-token",
            db_path="custom.duckdb"
        )

        # 验证属性
        assert sync.gitlab_url == "https://custom.gitlab.com"
        assert sync.gitlab_token == "custom-token"
        assert sync.db_path == "custom.duckdb"

        # 验证 GitLabProvider 创建
        mock_gitlab_provider_class.assert_called_once_with(
            "https://custom.gitlab.com",
            "custom-token"
        )

    def test_get_sync_stats(self):
        """测试获取同步统计信息"""
        temp_dir = tempfile.mkdtemp()
        temp_db_path = os.path.join(temp_dir, 'test_stats.duckdb')

        try:
            # 创建 ProjectSync 实例
            sync = ProjectSync(db_path=temp_db_path)

            # 预先添加一些测试数据
            with RepoStatusManager(temp_db_path) as state_manager:
                state_manager.add_repo("repo1", "url1")
                state_manager.add_repo("repo2", "url2")

            # 获取统计信息
            stats = sync.get_sync_stats()

            # 验证结果
            assert stats['total'] == 2
            assert stats['pending'] == 2
            assert stats['completed'] == 0
            assert stats['failed'] == 0
            assert stats['processing'] == 0

        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
