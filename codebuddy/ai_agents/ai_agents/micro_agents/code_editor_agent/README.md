# 智能代码编辑微智能体 (CodeEditorAgent)

基于smolagents的CodeAgent实现，提供智能代码编辑功能，支持自然语言描述的编辑需求。

## 核心特性

- **🤖 智能工具选择**：自动选择最适合的代码编辑工具
- **🛠️ 双工具支持**：SEARCH AND REPLACE + Codex结构化补丁
- **🎯 灵活使用**：高级接口 + CodeAgent直接访问

## 快速开始

### 基本使用

```python
from ai_agents.micro_agents.code_editor_agent import smart_edit_code

# 简单的函数重命名
result = smart_edit_code("app.py", "将函数名calculate改为compute")
print(f"编辑{'成功' if result.success else '失败'}: {result.message}")
```

### 使用智能体实例

```python
from ai_agents.micro_agents.code_editor_agent import CodeEditorAgent

agent = CodeEditorAgent()
result = agent.edit_code(
    "models.py",
    "为User类添加邮箱验证方法",
    context_info="用户管理系统的模型文件"
)
```

### 获取底层CodeAgent

```python
# 直接使用CodeAgent
code_agent = agent.get_code_agent()
result = code_agent.run("将所有print语句改为logging.info")
```

## 编辑策略

### SEARCH AND REPLACE
适合简单替换和重命名：
```
------- SEARCH
def old_function():
    return "old"
=======
def new_function():
    return "new"
+++++++ REPLACE
```

### Codex 结构化补丁
适合复杂重构：
```
*** Begin Patch
*** Update File: models.py
@@ class User:
- def validate(self): return True
+ def validate(self): return self.email and '@' in self.email
*** End Patch
```

## 配置选项

```python
# 使用自定义模型
agent = CodeEditorAgent(model=my_model)

# 指定编辑策略偏好
result = agent.edit_code(
    "service.py",
    "重构错误处理逻辑",
    preferred_strategy="codex"  # 或 "cline"
)
```

## 最佳实践

### 提供清晰的编辑需求
```python
# ❌ 模糊的需求
result = agent.edit_code("app.py", "修改一下")

# ✅ 清晰的需求
result = agent.edit_code("app.py", "将calculate_total函数的返回值从整数改为浮点数")
```

### 处理编辑结果
```python
result = agent.edit_code("file.py", "编辑需求")

if result.success:
    print(f"编辑完成，使用策略: {result.strategy_used}")
else:
    print(f"编辑失败: {result.message}")
```

## 架构设计

```
CodeEditorAgent
├── 模型管理 (自动选择CODE_GENERATION模型)
├── CodeAgent配置 (注册search_and_replace, codex_patch_apply工具)
├── 高级接口 (edit_code, run, get_code_agent)
└── 任务构建 (策略偏好处理, 上下文整合)
```

### 与smolagents的集成

- **CodeEditorAgent**: 配置器和高级接口，负责工具配置、模型选择、任务构建
- **底层CodeAgent**: 任务理解、工具调用、执行管理
