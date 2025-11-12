"""
智能代码编辑微智能体

基于smolagents的CodeAgent实现，提供智能化的代码编辑功能：
1. 分析编辑需求
2. 自动选择最佳编辑策略（Cline vs Codex）
3. 生成具体的编辑指令
4. 执行编辑操作
5. 错误恢复和重试
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from ai_agents.tools.file_ops import (
    create_new_file,
    read_file_content,
    read_file_lines,
    get_file_info,
    get_file_outline,
    browse_directory,
    quick_browse_directory,
)
from ...core import TaskType
from ...tools.code_editing import search_and_replace, codex_patch_apply
from ..base_micro_agent import BaseMicroAgent


logger = logging.getLogger(__name__)


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    message: str
    strategy_used: str
    attempts: int
    final_content: Optional[str] = None
    error_details: Optional[str] = None


class CodeEditorAgent(BaseMicroAgent):
    """
    智能代码编辑微智能体

    基于smolagents的CodeAgent实现，提供智能化的代码编辑功能。
    该智能体能够理解自然语言的编辑需求，自动选择最佳的编辑策略，
    并执行精确的代码修改。
    """

    @property
    def name(self) -> str:
        return "code_editor_agent"

    @property
    def description(self) -> str:
        return """该智能体专门负责智能代码编辑。它可以理解自然语言描述的编辑需求，
        自动分析代码结构和编辑复杂度，选择最适合的编辑策略（Cline或Codex格式），
        生成精确的编辑指令，并执行代码修改。支持错误恢复和多次重试机制。"""

    @property
    def default_task_type(self) -> TaskType:
        # 代码编辑需要生成和修改代码，使用代码生成模型
        return TaskType.CODE_GENERATION





    def _get_tools(self):
        """获取智能体使用的工具列表"""
        return [
            browse_directory,
            quick_browse_directory,

            read_file_content,
            read_file_lines,
            get_file_info,
            get_file_outline,

            create_new_file,
            search_and_replace,
            codex_patch_apply,
        ]

    def edit_code(self, file_path: str, edit_request: str,
                  context_info: str = "", preferred_strategy: str = None) -> EditResult:
        """
        智能编辑代码

        Args:
            file_path: 文件路径
            edit_request: 编辑需求描述（自然语言）
            context_info: 可选的上下文信息
            preferred_strategy: 首选策略 ('cline' 或 'codex')

        Returns:
            EditResult: 编辑结果
        """
        try:
            # 检查文件是否存在
            if not Path(file_path).exists():
                return EditResult(
                    success=False,
                    message=f"文件不存在: {file_path}",
                    strategy_used="none",
                    attempts=0
                )

            # 构建任务描述
            task = self._build_edit_task(file_path, edit_request, context_info, preferred_strategy)

            # 获取CodeAgent并执行任务
            agent = self.get_code_agent()
            result = agent.run(task)

            return EditResult(
                success=True,
                message="编辑任务已提交给CodeAgent执行",
                strategy_used="codeagent",
                attempts=1,
                final_content=str(result)
            )

        except Exception as e:
            logger.error(f"代码编辑过程中发生错误: {e}")
            return EditResult(
                success=False,
                message=f"编辑过程中发生错误: {e}",
                strategy_used="none",
                attempts=0,
                error_details=str(e)
            )

    def _build_edit_task(self, file_path: str, edit_request: str,
                        context_info: str, preferred_strategy: str = None) -> str:
        """
        构建给CodeAgent的任务描述

        Args:
            file_path: 文件路径
            edit_request: 编辑需求
            context_info: 上下文信息
            preferred_strategy: 首选策略

        Returns:
            str: 任务描述
        """
        task_parts = [
            f"请编辑文件 {file_path}。",
            f"编辑需求: {edit_request}",
        ]

        if context_info:
            task_parts.append(f"上下文信息: {context_info}")

        if preferred_strategy:
            if preferred_strategy == "cline":
                task_parts.append("请使用search_and_replace工具，它使用Cline SEARCH/REPLACE格式进行编辑。")
            elif preferred_strategy == "codex":
                task_parts.append("请使用codex_patch_apply工具，它使用Codex结构化补丁格式进行编辑。")
        else:
            task_parts.append("""
请根据编辑需求的复杂度选择合适的工具：
- 对于简单的搜索替换，使用search_and_replace工具（Cline格式）
- 对于复杂的重构，使用codex_patch_apply工具（Codex格式）
""")

        task_parts.append("""
编辑指导原则：
1. 仔细分析文件内容和编辑需求
2. 选择最适合的编辑工具和格式
3. 确保编辑指令精确匹配文件内容
4. 保持代码的格式和风格一致
5. 如果编辑失败，尝试调整策略或格式
""")

        return "\n\n".join(task_parts)




# 便利函数
def create_code_editor_agent(model=None) -> CodeEditorAgent:
    """
    创建代码编辑智能体实例

    Args:
        model: 直接提供的模型实例

    Returns:
        CodeEditorAgent: 智能体实例
    """
    return CodeEditorAgent(model=model)


def smart_edit_code(file_path: str, edit_request: str,
                   context_info: str = "", preferred_strategy: str = None,
                   model=None) -> EditResult:
    """
    智能编辑代码的便利函数

    Args:
        file_path: 文件路径
        edit_request: 编辑需求
        context_info: 上下文信息
        preferred_strategy: 首选策略 ('cline' 或 'codex')
        model: 可选的模型实例

    Returns:
        EditResult: 编辑结果
    """
    agent = create_code_editor_agent(model=model)
    return agent.edit_code(file_path, edit_request, context_info, preferred_strategy)
