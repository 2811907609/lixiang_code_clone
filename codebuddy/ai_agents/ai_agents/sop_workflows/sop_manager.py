"""
SOP工作流管理器

提供获取SOP工作流内容和相关文件的功能。

使用示例:
    # 获取所有可用的SOP类别
    categories = get_available_sop_categories()
    print(categories)  # ['bug_fix', 'repo_analysis', 'test_generation']

    # 获取特定类别的SOP内容
    sop_content = get_sop('repo_analysis')
    print(sop_content)
"""

from pathlib import Path
from typing import List
from jinja2 import FileSystemLoader, TemplateNotFound
from jinja2.sandbox import SandboxedEnvironment
import jinja2


class SOPManager:
    """SOP工作流管理器"""

    def __init__(self):
        """初始化SOP管理器"""
        self.sop_workflows_dir = Path(__file__).parent
        # 为每个 SOP 类别目录创建 Jinja2 环境缓存
        self._jinja_envs = {}

    def get_available_categories(self) -> List[str]:
        """
        获取所有可用的SOP类别

        Returns:
            List[str]: 包含sop.md.j2或sop.md文件的子目录名称列表
        """
        categories = []

        for item in self.sop_workflows_dir.iterdir():
            if item.is_dir() and ((item / "sop.md.j2").exists() or (item / "sop.md").exists()):
                categories.append(item.name)

        return sorted(categories)

    def _get_jinja_env(self, category_dir: Path) -> SandboxedEnvironment:
        """
        为指定目录获取或创建 Jinja2 沙箱环境

        Args:
            category_dir (Path): SOP类别目录路径

        Returns:
            SandboxedEnvironment: Jinja2 沙箱环境实例
        """
        dir_key = str(category_dir)
        if dir_key not in self._jinja_envs:
            # 使用沙箱环境，限制模板访问能力，防止安全漏洞
            self._jinja_envs[dir_key] = SandboxedEnvironment(
                loader=FileSystemLoader(str(category_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        return self._jinja_envs[dir_key]

    def get_sop(self, category: str) -> str:
        """
        获取指定类别的SOP内容

        Args:
            category (str): SOP类别名称

        Returns:
            str: SOP内容，包括主要SOP和额外文件列表

        Raises:
            ValueError: 当类别不存在或没有sop.md/sop.md.j2文件时
        """
        category_dir = self.sop_workflows_dir / category

        if not category_dir.exists():
            raise ValueError(f"SOP类别 '{category}' 不存在")

        # 优先检查 Jinja2 模板文件
        template_file = category_dir / "sop.md.j2"
        sop_file = category_dir / "sop.md"

        sop_content = ""

        if template_file.exists():
            # 使用 Jinja2 渲染模板
            try:
                jinja_env = self._get_jinja_env(category_dir)
                template = jinja_env.get_template("sop.md.j2")
                sop_content = template.render()
            except TemplateNotFound:
                raise ValueError(f"SOP类别 '{category}' 中的模板文件 sop.md.j2 不存在")
            except jinja2.TemplateSyntaxError as e:
                raise ValueError(f"SOP类别 '{category}' 中的模板文件 sop.md.j2 语法错误: {str(e)}")
            except jinja2.UndefinedError as e:
                raise ValueError(f"SOP类别 '{category}' 中的模板文件 sop.md.j2 包含未定义变量: {str(e)}")
            except Exception as e:
                raise ValueError(f"SOP类别 '{category}' 中的模板文件 sop.md.j2 渲染失败: {str(e)}")
        elif sop_file.exists():
            # 使用普通 Markdown 文件
            with open(sop_file, 'r', encoding='utf-8') as f:
                sop_content = f.read()
        else:
            raise ValueError(f"SOP类别 '{category}' 中没有找到 sop.md.j2 或 sop.md 文件")

        return sop_content


# 创建全局实例
sop_manager = SOPManager()


def get_available_sop_categories() -> List[str]:
    """
    获取所有可用的SOP类别

    Returns:
        List[str]: 包含sop.md文件的子目录名称列表
    """
    return sop_manager.get_available_categories()


def get_sop(category: str) -> str:
    """
    获取指定类别的SOP内容

    Args:
        category (str): SOP类别名称（如：bug_fix, repo_analysis, test_generation）

    Returns:
        str: SOP内容，包括主要SOP和额外文件列表

    Raises:
        ValueError: 当类别不存在或没有sop.md文件时
    """
    return sop_manager.get_sop(category)
