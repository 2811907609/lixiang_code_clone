"""
智能代码编辑微智能体

提供智能化的代码编辑功能，结合 SearchAndReplace 和Codex两种编辑策略，
能够根据编辑需求自动选择最佳的编辑方式。

主要功能：
1. 自然语言编辑需求分析
2. 智能策略选择（SearchAndReplace vs Codex）
3. 自动生成编辑指令
4. 错误恢复和重试机制
5. 丰富的示例库支持

使用示例：
```python
from ai_agents.micro_agents.code_editor_agent import smart_edit_code

# 简单使用
result = smart_edit_code(
    "app.py",
    "将函数名calculate改为compute"
)

# 带上下文信息
result = smart_edit_code(
    "models.py",
    "为User类添加邮箱验证方法",
    context_info="这是一个用户管理系统的模型文件"
)

# 使用智能体实例
from ai_agents.micro_agents.code_editor_agent import CodeEditorAgent

agent = CodeEditorAgent(llm_client=my_llm)
result = agent.edit_code("service.py", "重构错误处理逻辑")
```
"""

from .agent import (
    CodeEditorAgent,
    EditResult,
    create_code_editor_agent,
    smart_edit_code,
)

# 导出prompt模块，供高级用户使用
from .prompts import analysis, cline_prompts, codex_prompts

# 导出示例库，供学习和参考
from .examples import cline_examples, codex_examples

__all__ = [
    # 主要类和函数
    "CodeEditorAgent",
    "EditResult",
    "create_code_editor_agent",
    "smart_edit_code",

    # Prompt模块
    "analysis",
    "cline_prompts",
    "codex_prompts",

    # 示例库
    "cline_examples",
    "codex_examples",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Agents Team"
__description__ = "智能代码编辑微智能体"
