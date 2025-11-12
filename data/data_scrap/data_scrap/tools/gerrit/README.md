# Gerrit Changes Scraper

Gerrit 代码审查数据采集工具，用于从 Gerrit 服务器实时监听事件并采集变更详情。

## 功能特性

- **实时事件监听**: 通过 Kafka 消费 Gerrit 事件流
- **智能数据采集**: 从多个 Gerrit 实例获取最完整的变更数据
- **状态管理**: 完整的任务状态跟踪和重试机制
- **数据发送**: 将采集的数据以 Perceval 格式发送到 Kafka
- **容错处理**: 支持失败重试和僵尸任务回收

## 核心组件

- `scrap-changes.py` - 主要的采集器脚本，包含所有核心功能
- `run_prod.sh` - 生产环境启动脚本

## 工作原理

1. **事件监听**: 监听 Kafka 中的 Gerrit 事件（如 patchset-created、change-merged 等）
2. **任务入队**: 将需要采集的变更记录到数据库任务队列
3. **数据采集**: 通过 SSH 连接到 Gerrit 服务器获取变更详情
4. **智能选择**: 从多个 Gerrit 实例中选择返回数据最完整的结果
5. **数据发送**: 将数据包装成 Perceval 格式并发送到目标 Kafka Topic

## 配置要求

确保设置以下环境变量：

- `SCRAP_DB_URI` - PostgreSQL 数据库连接字符串
- `GERRIT_USER` - Gerrit SSH 用户名
- `TARGET_TOPIC` - 目标 Kafka Topic 名称
- `DATA_SCRAP_PG_PASSWD` - 数据库密码（在 run_prod.sh 中使用）

## 运行方式

### 生产环境

```bash
# 使用生产配置运行
source test.env && ./data_scrap/tools/gerrit/run_prod.sh
```

### 开发环境

```bash
# 直接运行主程序
source test.env && uv run data_scrap/tools/gerrit/scrap-changes.py main
```

### 单独运行组件

```bash
# 只处理现有任务（不监听新事件）
source test.env && uv run data_scrap/tools/gerrit/scrap-changes.py refresh_change_items

# 只回收僵尸任务
source test.env && uv run data_scrap/tools/gerrit/scrap-changes.py recycle_zoombies
```

## Gerrit 服务器配置

脚本配置了多个 Gerrit 实例以获取最佳数据质量：

```python
_gerrit_server_instances = {
    'gerrit-master-1': {
        'port': '40101',
        'host': '10.134.86.224',
    },
    'gerrit-master-2': {
        'port': '40102',
        'host': '10.134.86.224',
    },
}
```

## 数据库表结构

`gerrit_change_task_queue` 表字段说明：

- `change_id` - Gerrit 变更 ID
- `repo` - 仓库名称
- `private` - 是否为私有变更
- `event_type` - 触发事件类型
- `last_event_at` - 最后事件时间
- `last_scrap_at` - 最后采集时间
- `scrap_task_status` - 采集任务状态 (pending/doing/done/failed)
- `continuous_failed_count` - 连续失败次数
- `scrap_count` - 总采集次数
- `scrap_success_count` - 成功采集次数

## 支持的 Gerrit 事件类型

- `patchset-created` - 补丁集创建
- `change-merged` - 变更合并
- `change-abandoned` - 变更废弃
- `comment-added` - 评论添加
- `reviewer-added` - 审核者添加
- `vote-deleted` - 投票删除
- `private-state-changed` - 私有状态变更
- `wip-state-changed` - WIP 状态变更
- 其他 Gerrit 标准事件

## 数据格式

采集的数据以 Perceval 兼容格式输出：

```json
{
    "backend_name": "Gerrit",
    "backend_version": "0.13.1",
    "category": "review",
    "data": { /* 完整的 Gerrit 变更数据 */ },
    "origin": "gerrit.it.chehejia.com",
    "timestamp": 1640995200,
    "uuid": "unique-identifier"
}
```

## 性能优化

- **批量消费**: 一次消费多条 Kafka 消息
- **并发处理**: 使用 asyncio 并发处理多个任务
- **智能重试**: 失败后按指数退避重试
- **数据截断**: 自动截断过大的文件列表和补丁集
- **消息大小控制**: 限制 Kafka 消息大小在 1MB 以内

## 监控和故障处理

- **僵尸任务回收**: 自动回收超过 30 分钟的僵尸任务
- **失败重试**: 连续失败 10 次后停止重试
- **状态跟踪**: 完整的任务执行状态记录
- **日志记录**: 详细的操作日志便于问题排查
