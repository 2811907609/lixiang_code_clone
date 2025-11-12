"""
测试配置模块
用于管理不同类型测试的配置和环境检查
"""

import os
import pytest

from ai_agents.config import config
import ai_agents.lib.tracing # noqa: F401


def skip_if_no_llm_config():
    """检查是否有LLM配置，如果没有则跳过测试"""
    if not config.LLM_API_BASE or not config.LLM_API_KEY or config.LLM_API_KEY == "not_provided":
        pytest.skip("需要配置LLM_API_BASE和LLM_API_KEY环境变量进行LLM测试")


def skip_if_ci():
    """如果在CI环境中则跳过测试"""
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        pytest.skip("此测试在CI环境中跳过")


def get_test_repo_path():
    """获取测试仓库路径"""
    return os.getenv("TEST_REPO_PATH", os.getcwd())


class TestEnvironment:
    """测试环境配置类"""

    @staticmethod
    def is_ci():
        """检查是否在CI环境中"""
        return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))

    @staticmethod
    def has_llm_config():
        """检查是否有LLM配置"""
        return (config.LLM_API_BASE and
                config.LLM_API_KEY and
                config.LLM_API_KEY != "not_provided")

    @staticmethod
    def should_run_llm_tests():
        """判断是否应该运行LLM测试"""
        return TestEnvironment.has_llm_config() and not TestEnvironment.is_ci()


# 测试标记装饰器
def unit_test(func):
    """标记为单元测试"""
    return pytest.mark.unit(func)


def integration_test(func):
    """标记为集成测试"""
    return pytest.mark.integration(func)


def llm_test(func):
    """标记为LLM测试，需要API调用"""
    return pytest.mark.llm(pytest.mark.local_only(func))


def slow_test(func):
    """标记为慢速测试"""
    return pytest.mark.slow(func)
