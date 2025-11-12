
# Agent Memory Prompts

# Micro Agent Memory Prompt
MICRO_AGENT_MEMORY_PROMPT = """
# Memory使用指导 - 微智能体

## Memory权限
- **只读**: project.* (了解已有项目知识)
- **只读**: task.* (了解任务上下文)
- **只读**: history.* (学习历史经验)

## Memory使用原则
- 开始前先读取project和task context了解背景
- 专注于技术执行，将结果提供给supervisor
- 使用中文格式提供分析结果
"""

# Supervisor Agent Memory Prompt
SUPERVISOR_AGENT_MEMORY_PROMPT = """
# Memory使用指导 - 监督智能体

## Memory权限
- **读写**: project.* (更新项目信息，需要justification)
- **读写**: task.* (管理任务进度和状态)
- **只读**: history.* (学习历史经验)

## Memory使用原则
- 开始前先检查已有分析，进行增量更新
- 对micro agent结果进行加工后再更新到Memory
- 所有更新必须使用Markdown格式，避免JSON
- 更新project信息时必须提供清晰的justification
"""
