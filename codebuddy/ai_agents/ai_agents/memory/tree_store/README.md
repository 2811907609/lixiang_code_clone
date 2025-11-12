
# Memory Bank 介绍
参考下面 cline 的链接，Memory Bank 是一种非常巧妙的 Agent Memory 管理方案，思路清晰，
实现简单，只需要 COPY 一段 prompt 就有比较好的效果。

https://docs.cline.bot/prompting/cline-memory-bank

# 层次化内存系统设计文档
## 概述
层次化内存系统（Hierarchical Memory System）是一个为AI代理设计的高效、结构化的上下文记忆管理系统。它解决了传统基于文件系统的memory bank在大型仓库中面临的上下文过长和更新复杂的问题。

## 核心优势
层次化结构：使用点分隔的key结构（如project.architecture.overview）组织信息
按需加载：只读取需要的内容，避免上下文膨胀
精准更新：直接更新特定节点，无需处理大型markdown文件
权限分离：不同类型的Agent有不同的访问权限
自动保存：支持JSON存储和Markdown导出

## 系统架构
### 内存分类
系统将内存分为三个层次：

1. 项目级内存（长期存储）
用途：存储项目架构、代码库分析、技术栈等长期有效信息
生命周期：跨任务持久化
访问权限：代码库分析Agent完全访问，任务执行Agent只读（特殊情况可更新）

        project.summary              # 项目概述
        project.architecture.*       # 系统架构
        project.codebase.*          # 代码结构分析
        project.stack.*             # 技术栈信息
        project.patterns.*          # 设计模式和最佳实践

2. 任务级内存（短期存储）
用途：存储当前任务的计划、进度、上下文等临时信息
生命周期：任务完成后归档到历史
访问权限：任务执行Agent完全访问

        task.summary                 # 任务描述和目标
        task.plan.*                  # 执行计划
        task.context.*              # 工作上下文
        task.progress.*              # 进度和发现
        task.results                 # 任务结果
        task.discoveries             # 重要发现

3. 历史内存（经验积累）
用途：存储已完成任务的总结和跨任务的经验模式
生命周期：保留最近N个任务（默认10个）
访问权限：所有Agent只读

        history.recent_tasks         # 最近N个任务的summary
        history.patterns            # 跨任务发现的模式
        history.lessons              # 经验教训和避坑指南

### 层次化任务管理
支持父子任务的层次化管理：

主任务：task_001
子任务：task_001.1, task_001.2
孙任务：task_001.1.1
继承机制
子任务自动继承父任务的所有短期内存
子任务在独立的命名空间中工作
子任务完成时可选择性合并结果到父任务
合并策略
子任务完成时，以下信息会合并到父任务：

任务总结
关键结果
重要发现
经验教训

## 核心功能
1. 任务管理

        memory_complete_task(summary, merge_to_parent) - 完成任务

2. 内容操作

        memory_get_content(keys, memory_type) - 获取指定内容
        memory_update_task_content(key, content, mode) - 更新任务内容
        memory_update_project_info(key, content, justification, mode) - 更新项目信息

3. 概览查看

        memory_get_project_context() - 获取项目概览
        memory_get_task_overview() - 获取任务概览
        memory_get_history() - 获取历史信息

4. 自动化功能
自动保存：每次更新后自动保存到JSON和Markdown
模板应用：新任务自动应用基础结构模板
历史管理：自动维护最近N个任务的记录

## Agent设计
### 代码库分析Agent（Repository Analyst）
职责：
* 分析代码库结构和模式
* 维护项目架构文档
* 更新技术栈信息
* 识别和记录设计模式

权限：
* 项目级内存：完全访问（读写）
* 历史内存：只读
* 任务内存：只读（用于上下文）
* 关键工具：

```
memory_get_project_context()
memory_update_project_info(key, content, justification, mode)
memory_get_history()
```


### 任务执行Agent（Task Executor）
职责：

* 执行具体任务
* 维护任务状态和进度
* 应用项目知识解决问题
* 记录发现和经验

权限：

* 项目级内存：只读（发现错误时可谨慎更新）
* 任务内存：完全访问
* 历史内存：只读
* 关键工具：

    ```
    memory_get_task_overview()
    memory_update_task_content(key, content, mode)
    memory_new_task() / memory_complete_task()
    ```

## 存储结构
### 目录结构

    .memory_store/
    ├── project/                 # 项目级内存
    │   ├── keys.json
    │   ├── project.summary.json
    │   ├── project.architecture.overview.json
    │   └── *.md                # Markdown导出文件
    ├── tasks/                  # 任务级内存
    │   ├── task_001/
    │   ├── task_001.1/
    │   └── task_002/
    ├── history/                # 历史内存
    │   ├── keys.json
    │   ├── history.recent_tasks.json
    │   └── *.md
    └── current_task.json       # 当前任务配置

JSON格式
每个内存节点存储为独立的JSON文件：

{
  "key": "project.architecture.overview",
  "content": "系统采用微服务架构..."
}
Markdown导出
按第一级key分组导出为markdown文件，便于人工查看：

project.md - 包含所有project.*的内容
task.md - 包含当前任务的所有task.*内容
history.md - 包含历史信息

## 使用示例
### 创建新任务

    # 创建主任务
    memory_new_task("task_001", "", "实现用户认证功能")

    # 创建子任务
    memory_new_task("task_001.1", "task_001", "设计用户数据模型")

### 更新项目信息（代码库分析Agent）

    memory_update_project_info(
        "project.architecture.auth",
        "采用JWT Token + OAuth2.0的认证方案",
        "分析现有代码后确定的认证架构"
    )

### 管理任务进度（任务执行Agent）

    # 获取项目上下文
    project_info = memory_get_project_context()

    # 更新任务进度
    memory_update_task_content(
        "task.progress.status",
        "已完成用户模型设计，开始实现认证逻辑",
        "append"
    )

    # 完成任务
    memory_complete_task(
        "成功实现用户认证功能，包括注册、登录、JWT验证",
        merge_to_parent=True
    )

## 配置选项
### 初始化参数
    memory_system = HierarchicalMemorySystem(
        storage_dir=".memory_store",    # 存储目录
        max_history_tasks=10           # 保留的历史任务数量
    )

### 自定义模板
系统提供简洁的任务模板，避免上下文浪费：

template_keys = {
    "task.summary": "任务描述和目标",
    "task.plan.overview": "执行计划概述",
    "task.context.current": "当前工作上下文",
    "task.progress.status": "进度状态"
}

## 最佳实践
1. 内存组织
使用清晰的层次化key命名
利用.summary节点提供简洁概览
定期整理和更新项目级信息

2. Agent协作
代码库分析Agent专注长期知识维护
任务执行Agent专注具体任务完成
通过历史内存分享跨任务经验

3. 上下文管理
优先使用概览和summary减少上下文长度
按需获取具体内容
及时完成任务避免内存碎片化

4. 质量保证
项目信息更新必须提供justification
定期review和清理过时信息
利用markdown导出进行人工审查

这个系统设计为大型代码库的AI代理协作提供了高效、可扩展的记忆管理方案，既保证了上下文的精确性，又避免了传统方案的性能问题。
