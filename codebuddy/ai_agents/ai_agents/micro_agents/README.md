# 微智能体 (Micro Agents)

微智能体模块提供了专业化的技术智能体，用于执行特定的技术任务。所有微智能体都继承自 `BaseMicroAgent` 抽象基类，确保接口的一致性和可组合性。

## 架构设计

### BaseMicroAgent 抽象基类

`BaseMicroAgent` 是所有微智能体的抽象基类，定义了统一的接口和行为模式：

```python
from ai_agents.micro_agents import BaseMicroAgent
from ai_agents.core import TaskType

class MyMicroAgent(BaseMicroAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def description(self) -> str:
        return "我的专业智能体描述"

    @property
    def default_task_type(self) -> TaskType:
        return TaskType.CODE_GENERATION

    def _get_tools(self):
        return [
            # 你的工具列表
        ]
```

### 核心接口

每个微智能体必须实现以下抽象方法和属性：

- **`name`**: 智能体名称
- **`description`**: 智能体功能描述
- **`default_task_type`**: 默认任务类型（用于模型选择）
- **`_get_tools()`**: 返回智能体使用的工具列表

### 核心方法

- **`get_code_agent()`**: 返回配置好的 CodeAgent 实例，这是微智能体的核心接口
- **`run(task)`**: 直接执行任务的便利方法

## 设计原则

1. **专业化**: 每个微智能体专注于特定的技术领域
2. **标准化**: 通过 `get_code_agent()` 方法提供统一接口
3. **可组合**: 可以被监督智能体作为 `managed_agents` 使用
4. **自包含**: 包含完成任务所需的所有工具和配置

## 使用方式

### 作为独立智能体使用

```python
from ai_agents.micro_agents import SearchAgent

# 创建智能体实例
search_agent = SearchAgent()

# 直接执行任务
result = search_agent.run("在项目中搜索所有的 TODO 注释")
```

## 现有微智能体

### SearchAgent
专门用于在目录和文件中搜索关键词和文本模式。

**主要功能**:
- 在目录中搜索关键词
- 提供搜索结果的上下文
- 浏览文件和目录结构
- 读取和分析文件内容
- 项目结构探索

**任务类型**: `COMPLEX_REASONING`

### CodeAnalysisAgent
专门用于深度代码结构分析，使用智能解析器自动选择最佳解析策略，支持多种编程语言的测试生成。

**主要功能**:
- 智能代码元素提取（函数、类、方法）
- 自动选择最佳解析策略（Tree-sitter 优先，Regex 回退）
- 分析代码复杂度和依赖关系
- 识别测试覆盖率缺口
- 建议测试结构和策略
- 支持多种编程语言
- 分析代码质量和可测试性
- 语义理解和复杂度分析
- 识别测试重点和边缘情况

**任务类型**: `CODE_REVIEW`

### TestGenerationAgent
专门用于生成和更新多种编程语言的测试用例。

**主要功能**:
- 从头生成综合测试文件
- 更新现有测试文件，添加新测试用例
- 创建测试夹具和模拟设置
- 处理多种测试框架
- 使用智能代码编辑工具
- 支持特定语言的测试模式

**任务类型**: `CODE_GENERATION`

### CoverageAnalysisAgent
专门用于代码覆盖率分析和报告生成。

**主要功能**:
- 运行覆盖率测试并生成报告
- 分析覆盖率数据和识别缺口
- 生成可视化覆盖率报告
- 提供覆盖率改进建议
- 支持多种覆盖率工具
- 分析分支和路径覆盖率

**任务类型**: `CODE_REVIEW`

### TestExecutionAgent
专门用于测试执行和结果分析。

**主要功能**:
- 执行各种类型的测试
- 解析和分析测试结果
- 管理测试环境和依赖
- 生成详细的测试报告
- 诊断测试失败原因
- 支持多种测试框架

**任务类型**: `CODE_REVIEW`

### CodeEditorAgent
专门用于智能代码编辑。

**主要功能**:
- 理解自然语言编辑需求
- 自动选择最佳编辑策略
- 执行精确的代码修改
- 错误恢复和重试机制

**任务类型**: `CODE_GENERATION`

## 扩展指南

要创建新的微智能体：

1. 继承 `BaseMicroAgent`
2. 实现所有抽象方法和属性
3. 在 `_get_tools()` 中定义专业工具
4. 选择合适的 `default_task_type`
5. 编写详细的 `description`
6. 添加到 `__init__.py` 的导出列表

## 最佳实践

1. **工具选择**: 只包含与智能体专业领域相关的工具
2. **描述编写**: 详细说明智能体的能力、适用场景和限制
3. **任务类型**: 根据智能体的主要工作选择合适的模型类型
4. **错误处理**: 在工具使用中包含适当的错误处理
5. **测试**: 为每个新智能体编写单元测试

## 模型管理

微智能体支持两种模型配置方式：

1. **自动选择** (推荐): 根据 `default_task_type` 自动选择合适的模型
2. **手动指定**: 直接传入 `model` 参数

```python
# 自动选择模型
agent = SearchAgent()

# 手动指定模型
agent = SearchAgent(model=my_model)

# 无模型模式（仅用于测试）
agent = SearchAgent(model=None)
```
