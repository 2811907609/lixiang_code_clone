"""
测试SOP管理器功能
"""

import pytest
from pathlib import Path
import tempfile

from ai_agents.sop_workflows.sop_manager import (
    SOPManager,
    get_available_sop_categories,
    get_sop,
)


class TestSOPManager:
    """测试SOPManager类"""

    def test_init(self):
        """测试SOPManager初始化"""
        manager = SOPManager()
        assert manager.sop_workflows_dir.exists()
        assert manager.sop_workflows_dir.name == "sop_workflows"

    def test_get_available_categories(self):
        """测试获取可用类别"""
        manager = SOPManager()
        categories = manager.get_available_categories()

        # 检查返回的是列表
        assert isinstance(categories, list)

        # 检查已知的类别是否存在
        expected_categories = ["bug_fix", "repo_analysis", "test_generation"]
        for category in expected_categories:
            assert category in categories

        # 检查列表是否已排序
        assert categories == sorted(categories)

    def test_get_sop_valid_category(self):
        """测试获取有效类别的SOP"""
        manager = SOPManager()

        # 测试已知存在的类别
        sop_content = manager.get_sop("repo_analysis")

        # 检查内容不为空
        assert sop_content.strip()

    def test_get_sop_invalid_category(self):
        """测试获取无效类别的SOP"""
        manager = SOPManager()

        # 测试不存在的类别
        with pytest.raises(ValueError, match="SOP类别 'nonexistent' 不存在"):
            manager.get_sop("nonexistent")


class TestSOPManagerFunctions:
    """测试模块级别的函数"""

    def test_get_available_sop_categories(self):
        """测试get_available_sop_categories函数"""
        categories = get_available_sop_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0

        # 检查已知类别
        expected_categories = ["bug_fix", "repo_analysis", "test_generation"]
        for category in expected_categories:
            assert category in categories

    def test_get_sop_function(self):
        """测试get_sop函数"""
        sop_content = get_sop("bug_fix")

        assert sop_content.strip()
        assert isinstance(sop_content, str)


class TestSOPManagerWithTempFiles:
    """使用临时文件测试SOPManager"""

    def test_with_temp_directory(self):
        """测试使用临时目录的SOPManager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建测试目录结构
            test_category = temp_path / "test_category"
            test_category.mkdir()

            # 创建sop.md文件
            sop_file = test_category / "sop.md"
            sop_file.write_text("# 测试SOP\n\n这是一个测试SOP文件。", encoding='utf-8')

            # 创建SOPManager实例并设置临时目录
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 测试获取类别
            categories = manager.get_available_categories()
            assert "test_category" in categories

            # 测试获取SOP内容
            manager.get_sop("test_category")

    def test_jinja2_template_rendering(self):
        """测试Jinja2模板渲染功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建测试目录
            test_category = temp_path / "jinja_test"
            test_category.mkdir()

            # 创建Jinja2模板文件
            template_content = """# 测试标题

这是一个Jinja2模板SOP文件。

## 步骤
1. 第一步
2. 第二步
"""
            template_file = test_category / "sop.md.j2"
            template_file.write_text(template_content, encoding='utf-8')

            # 创建SOPManager实例
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 测试模板渲染
            sop_content = manager.get_sop("jinja_test")
            assert "Jinja2模板SOP文件" in sop_content
            assert "第一步" in sop_content

    def test_jinja2_template_priority(self):
        """测试Jinja2模板优先级（sop.md.j2优于sop.md）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建测试目录
            test_category = temp_path / "priority_test"
            test_category.mkdir()

            # 创建两个文件
            template_file = test_category / "sop.md.j2"
            template_file.write_text("# Jinja2模板内容", encoding='utf-8')

            md_file = test_category / "sop.md"
            md_file.write_text("# 普通Markdown内容", encoding='utf-8')

            # 创建SOPManager实例
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 应该优先使用Jinja2模板
            sop_content = manager.get_sop("priority_test")
            assert "Jinja2模板内容" in sop_content
            assert "普通Markdown内容" not in sop_content

    def test_jinja2_template_syntax_error(self):
        """测试Jinja2模板语法错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建测试目录
            test_category = temp_path / "syntax_error_test"
            test_category.mkdir()

            # 创建有语法错误的模板文件
            template_content = "# 语法错误模板\n\n{% if condition %}\n没有对应的endif"
            template_file = test_category / "sop.md.j2"
            template_file.write_text(template_content, encoding='utf-8')

            # 创建SOPManager实例
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 应该抛出包含语法错误信息的ValueError
            with pytest.raises(ValueError, match="语法错误"):
                manager.get_sop("syntax_error_test")

    def test_jinja2_env_caching(self):
        """测试Jinja2环境缓存机制"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建测试目录
            test_category = temp_path / "cache_test"
            test_category.mkdir()

            # 创建模板文件
            template_file = test_category / "sop.md.j2"
            template_file.write_text("# 缓存测试", encoding='utf-8')

            # 创建SOPManager实例
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 第一次调用
            manager.get_sop("cache_test")
            first_env = manager._jinja_envs.get(str(test_category))

            # 第二次调用
            manager.get_sop("cache_test")
            second_env = manager._jinja_envs.get(str(test_category))

            # 应该是同一个环境实例（缓存生效）
            assert first_env is second_env
            assert len(manager._jinja_envs) == 1

    def test_get_available_categories_includes_jinja2_templates(self):
        """测试获取类别时包含Jinja2模板目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建只有sop.md.j2的目录
            jinja_category = temp_path / "jinja_only"
            jinja_category.mkdir()
            template_file = jinja_category / "sop.md.j2"
            template_file.write_text("# Jinja2模板", encoding='utf-8')

            # 创建只有sop.md的目录
            md_category = temp_path / "md_only"
            md_category.mkdir()
            md_file = md_category / "sop.md"
            md_file.write_text("# 普通Markdown", encoding='utf-8')

            # 创建两者都有的目录
            both_category = temp_path / "both_files"
            both_category.mkdir()
            (both_category / "sop.md.j2").write_text("# 模板", encoding='utf-8')
            (both_category / "sop.md").write_text("# Markdown", encoding='utf-8')

            # 创建SOPManager实例
            manager = SOPManager()
            manager.sop_workflows_dir = temp_path

            # 获取所有类别
            categories = manager.get_available_categories()

            # 应该包含所有三个目录
            assert "jinja_only" in categories
            assert "md_only" in categories
            assert "both_files" in categories
            assert len(categories) == 3
