# SOP工作流

本目录包含各种AI智能体的标准操作程序(SOP)工作流。

## 目录结构

- `bug_fix/` - Bug修复智能体的SOP工作流
- `repo_analysis/` - 代码仓库分析智能体的SOP工作流
- `test_generation/` - 测试生成智能体的SOP工作流

每个子目录包含：
- `sop.md` - 主要的SOP文档
- 其他相关的指南和参考文件

## SOP管理器

本目录提供了一个SOP管理器(`sop_manager.py`)，用于程序化地访问SOP内容。

### 主要功能

1. **获取所有可用的SOP类别**
2. **获取特定类别的SOP内容**（包括额外文件列表）
3. **获取SOP类别中的额外参考文件内容**

### 使用方法

```python
from ai_agents.sop_workflows.sop_manager import (
    get_available_sop_categories,
    get_sop,
    get_sop_additional_file
)

# 获取所有可用的SOP类别
categories = get_available_sop_categories()
print(categories)  # ['bug_fix', 'repo_analysis', 'test_generation']

# 获取特定类别的SOP内容
sop_content = get_sop('repo_analysis')
print(sop_content)

# 获取额外的参考文件
additional_content = get_sop_additional_file('repo_analysis', 'language_identification.md')
print(additional_content)
```

### 运行演示

```bash
# 运行基本演示
python examples/sop_manager_demo.py

# 运行测试
source local.env && uv run pytest tests/test_sop_manager.py -vv -s
```

### API参考

#### `get_available_sop_categories() -> List[str]`
返回所有包含`sop.md`文件的子目录名称列表。

#### `get_sop(category: str) -> str`
获取指定类别的完整SOP内容，包括主要SOP和额外文件列表。

**参数:**
- `category`: SOP类别名称（如：'bug_fix', 'repo_analysis', 'test_generation'）

**返回:** SOP内容字符串

**异常:** 当类别不存在或没有sop.md文件时抛出`ValueError`

#### `get_sop_additional_file(category: str, filename: str) -> str`
获取SOP类别中的额外文件内容。

**参数:**
- `category`: SOP类别名称
- `filename`: 文件名（不能是'sop.md'）

**返回:** 文件内容字符串

**异常:** 当类别不存在、文件不存在或文件是sop.md时抛出`ValueError`
