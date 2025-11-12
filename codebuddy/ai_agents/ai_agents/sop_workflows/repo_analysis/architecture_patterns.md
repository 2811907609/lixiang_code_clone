# 整体架构模式识别指南

## 概述

本指南提供系统化的整体架构模式识别方法，通过分析目录结构、服务组织、通信方式等特征，准确识别项目采用的架构风格。

## 单体架构 (Monolithic Architecture)

### 识别特征
- 单一代码仓库包含所有功能
- 统一的构建和部署流程
- 共享数据库和配置
- 模块间直接函数调用

### 识别标志
- 单一入口文件 (`main.py`, `app.py`, `server.js`)
- 统一的配置文件和数据库连接
- 分层目录结构 (`controllers/`, `services/`, `models/`)
- 模块间直接导入依赖

## 微服务架构 (Microservices Architecture)

### 识别特征
- 多个独立的服务目录
- 每个服务独立开发和部署
- 服务间通过 API 通信
- 独立的数据存储

### 识别标志
- `services/` 目录包含多个服务
- 每个服务有独立的构建配置 (`Dockerfile`, `package.json`)
- API Gateway 或服务发现配置
- `docker-compose.yml` 或 K8s 配置
- 服务间通信配置 (HTTP/gRPC)

## 分层架构 (Layered Architecture)

### 识别特征
- 明确的层次划分和职责
- 上层依赖下层，单向依赖
- 每层专注特定职责
- 层间通过接口通信

### 识别标志
- 层次化目录结构 (`presentation/`, `business/`, `persistence/`)
- 接口和实现分离
- 依赖注入配置
- 层间通信规范

## 六边形架构 (Hexagonal Architecture)

### 识别特征
- 端口适配器模式
- 核心业务逻辑与外部隔离
- 依赖倒置原则
- 技术无关的核心领域

### 识别标志
- `domain/`, `ports/`, `adapters/` 目录分离
- 接口驱动设计
- 依赖注入容器配置
- 核心业务逻辑与技术实现分离

## 事件驱动架构 (Event-Driven Architecture)

### 识别特征
- 组件间通过事件通信
- 异步处理和响应
- 松耦合设计
- 易于扩展的事件处理器

### 识别标志
- `events/`, `handlers/` 目录分离
- 消息队列配置 (RabbitMQ, Kafka, Redis)
- 事件存储机制
- 异步处理框架 (`@event_handler` 装饰器)

## CQRS (Command Query Responsibility Segregation)

### 识别特征
- 命令和查询使用不同模型
- 读写模型分别优化
- 最终一致性
- 适用于复杂业务场景

### 识别标志
- `commands/`, `queries/` 目录分离
- 不同的读写数据模型
- 事件溯源机制
- 投影和同步机制 (`projectors/`)

## Monorepo 架构

### 识别特征
- 单一仓库包含多个相关项目
- 共享代码和工具链
- 统一的版本控制和CI/CD
- 项目间可能有依赖关系

### 识别标志
- `packages/`, `apps/`, `libs/`, `projects/` 等顶级目录
- 根目录的工作空间配置文件
- 共享的构建和开发工具配置
- 项目间的依赖声明

### 常见Monorepo工具识别
- **Lerna**: `lerna.json`, `packages/` 目录
- **Nx**: `nx.json`, `workspace.json`, `apps/` 和 `libs/` 目录
- **Rush**: `rush.json`, `common/` 目录
- **Yarn Workspaces**: `package.json` 中的 `workspaces` 字段
- **pnpm Workspaces**: `pnpm-workspace.yaml`
- **Bazel**: `WORKSPACE`, `BUILD` 文件
- **Turborepo**: `turbo.json`

### Monorepo结构模式
- **按功能分组**: `packages/ui/`, `packages/api/`, `packages/shared/`
- **按应用分组**: `apps/web/`, `apps/mobile/`, `apps/admin/`
- **混合模式**: `apps/` + `packages/` + `tools/`

## Memory 更新 Key 示例

```
project.architecture.overall_pattern
project.architecture.characteristics
project.architecture.decisions
project.architecture.communication
project.architecture.data_management
project.architecture.monorepo
```

## 识别策略

### 多维度分析
1. **目录结构**: 代码组织方式反映架构意图
2. **配置文件**: 部署和服务配置显示架构模式
3. **通信方式**: 组件间通信方式决定架构类型
4. **数据管理**: 数据存储和访问模式

### 架构演进识别
- 分析 Git 历史中的架构变迁
- 识别重构和迁移的痕迹
- 评估当前架构的成熟度
