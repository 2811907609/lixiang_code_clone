# 如何新增一个新的 Agent 应用

参考 Simple Agent 示例，详细说明如何在项目中新增一个完整的 Agent 应用。

## 概述

一个完整的 Agent 应用包含以下核心组件：

1. **Supervisor Agent** - 监督智能体，负责任务协调和管理
2. **SOP Workflow** - 标准操作流程，定义 Agent 的工作流程
3. **CLI Interface** - 命令行接口，提供用户交互入口
4. **Run Module** - 运行模块，封装 Agent 的执行逻辑

## 目录结构

新增 Agent 应用需要创建以下文件结构：

```
ai_agents/
├── supervisor_agents/
│   └── {agent_name}/
│       ├── __init__.py
│       ├── agent.py
│       └── run.py
├── sop_workflows/
│   └── {agent_name}/
│       ├── sop.md.j2                    # Jinja2 模板文件（推荐）
│       ├── common_instructions.md       # 通用指导（可选）
│       ├── specific_guidelines.md       # 具体指南（可选）
│       └── sop.md                       # 或普通 Markdown 文件
└── clis/
    └── {agent_name}/
        └── cli.py
```

## 详细实现步骤

### 1. 创建 SOP Workflow

首先在 `ai_agents/sop_workflows/` 目录下创建新的 SOP 工作流。

#### 选项 1：使用 Jinja2 模板（推荐）

**文件路径**: `ai_agents/sop_workflows/{agent_name}/sop.md.j2`

```jinja2
你是一个编程专家，请帮助用户完成他的任务。

{% include 'common_instructions.md' %}

{% include 'specific_guidelines.md' %}
```

同时创建可复用的组件文件：

**文件路径**: `ai_agents/sop_workflows/{agent_name}/common_instructions.md`
```markdown
## 通用指导原则

- 始终遵循最佳实践
- 确保代码质量和可维护性
- 提供清晰的文档和注释
```

**文件路径**: `ai_agents/sop_workflows/{agent_name}/specific_guidelines.md`
```markdown
## 具体实施指南

1. 分析问题需求
2. 设计解决方案
3. 实施代码更改
4. 测试和验证
```

#### 选项 2：使用普通 Markdown

**文件路径**: `ai_agents/sop_workflows/{agent_name}/sop.md`

```markdown
# 定义你的 Agent 的标准操作流程
# 这里描述 Agent 应该如何执行任务的详细步骤

你是一个编程专家，请帮助用户完成他的任务。
```

### 2. 实现 Supervisor Agent

**文件路径**: `ai_agents/supervisor_agents/{agent_name}/agent.py`

```python
from pathlib import Path

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.supervisor_agents.base_supervisor_agent import BaseSupervisorAgent
from ai_agents.sop_workflows.sop_manager import get_sop

class YourSupervisorAgent(BaseSupervisorAgent):
    """
    你的 Agent 描述
    """

    # 配置参数
    with_memory = False  # 是否启用记忆系统
    tool_call_type = "tool_call"  # "tool_call" 或 "code_act"
    max_steps = 20  # 最大执行步数

    @property
    def name(self) -> str:
        return "your_agent_name"

    @property
    def sop_category(self) -> str:
        return "{agent_name}"  # 对应 SOP 目录名

    @property
    def default_task_type(self) -> str:
        return "complex_reasoning"  # 或其他任务类型

    def __init__(self,
                 model=None,
                 execution_env=None,
                 execution_env_config=None,
                 logger: AgentLogger=None):
        """
        初始化 Agent

        Args:
            model: 可选的模型实例
            execution_env: 可选的执行环境实例
            execution_env_config: 执行环境配置参数
            logger: 日志记录器实例
        """
        super().__init__(model=model,
                         execution_env=execution_env,
                         execution_env_config=execution_env_config,
                         logger=logger)

    def _get_tools(self):
        """获取 Agent 使用的工具列表

        可以在这里添加特定的工具或微智能体
        """
        tools = []

        return tools

    def _get_enhanced_task(self, task: str) -> str:
        """
        构建增强的任务描述

        Args:
            task: 原始任务描述

        Returns:
            str: 增强后的任务描述，包含 SOP 流程和执行指导
        """
        sop_content = get_sop(self.sop_category)
        enhanced_task = f"""
**SOP Workflow**:
{sop_content}

**Task Execution Principles**:
- Progressive Solutions: Start with minimal changes, gradually expand
- Validation-Driven Development: Immediately validate after each modification
- Quality Assurance: Ensure no new regression problems are introduced

**User Original Task**: {task}

Please strictly follow the above SOP process and coordination strategy to generate detailed execution plans and coordinate micro-agents to complete the task.
"""
        return enhanced_task
```

### 3. 实现运行模块

参考 `ai_agents/supervisor_agents/simple/run.py`

### 4. 创建 CLI 接口
参考 `clis/simple/cli.py`

## 配置选项说明

### Supervisor Agent 配置

- **`with_memory`**: 是否启用记忆系统，用于跨步骤信息存储
- **`tool_call_type`**: 工具调用类型
  - `"tool_call"`: 使用结构化工具调用
  - `"code_act"`: 使用代码执行模式
- **`max_steps`**: Agent 最大执行步数
- **`default_task_type`**: 默认任务类型，影响模型选择

### 任务类型选项

- `"complex_reasoning"`: 复杂推理任务
- `"code_generation"`: 代码生成任务
- `"text_processing"`: 文本处理任务

## 使用示例

创建完成后，可以通过以下方式使用新的 Agent：

```bash
# 直接运行
python clis/{agent_name}/cli.py "你的任务描述" --working_dir=/path/to/project

# 或者作为模块运行
python -m clis.{agent_name}.cli "你的任务描述" --working_dir=/path/to/project
```

## 高级功能

### SOP 模板系统

使用 Jinja2 模板可以实现更灵活的 SOP 内容组织：

#### 模板文件结构
```
ai_agents/sop_workflows/{agent_name}/
├── sop.md.j2                    # 主模板文件
├── common_instructions.md       # 通用指导原则
├── specific_guidelines.md       # 具体实施指南
├── error_handling.md           # 错误处理流程
└── best_practices.md           # 最佳实践
```

#### 模板语法示例
```jinja2
你是一个 {{agent_type}} 专家，请帮助用户完成任务。

{% include 'common_instructions.md' %}

## 专业领域指导
{% include 'specific_guidelines.md' %}

## 错误处理
{% include 'error_handling.md' %}

{% include 'best_practices.md' %}
```

#### 模板优势
- **内容复用**：通用内容可以在多个 Agent 间共享
- **模块化管理**：将复杂的 SOP 拆分为易于维护的小文件
- **动态组合**：根据不同场景灵活组合内容
- **版本控制友好**：小文件更容易进行版本管理和协作

#### 安全最佳实践

**模板编写注意事项**：
- 使用 `ignore missing` 参数避免文件不存在时的异常
- 使用 `with context` 确保模板上下文传递
- 提供变量默认值设置，避免未定义变量错误

### 添加微智能体

如果需要使用微智能体，可以在 SOP 目录下创建 `micro_agents` 文件夹：

```
ai_agents/sop_workflows/{agent_name}/
├── sop.md.j2                   # 或 sop.md
└── micro_agents/
    ├── analyzer.yaml
    ├── executor.yaml
    └── validator.yaml
```

然后在 `_get_tools()` 方法中加载这些微智能体。

### 自定义工具集成

可以在 `_get_tools()` 方法中添加特定的工具：

```python
def _get_tools(self):
    tools = []

    # 添加自定义工具
    from your_custom_tools import CustomTool
    tools.append(CustomTool())

    return tools
```

## 最佳实践

1. **明确 SOP 流程**: 在 `sop.md.j2` 或 `sop.md` 中详细描述 Agent 的工作流程
2. **使用模板系统**: 优先使用 Jinja2 模板实现内容的模块化和复用
3. **合理组织文件**: 将通用内容抽取到独立文件中，便于维护和复用
4. **合理设置步数**: 根据任务复杂度设置 `max_steps`
5. **选择合适的工具调用类型**: 简单任务用 `tool_call`，复杂任务用 `code_act`
6. **添加详细日志**: 在关键步骤添加日志输出
7. **错误处理**: 在 CLI 中添加完善的异常处理
8. **模板测试**: 确保 Jinja2 模板能够正确渲染，没有语法错误

## 参考示例

可以参考项目中现有的 Agent 实现：

- **Simple Agent**: 最基础的示例实现
- **SWEBench Agent**: 复杂的软件工程任务处理

通过遵循这个指南，你可以快速创建一个功能完整的 Agent 应用。
