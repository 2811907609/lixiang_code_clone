# Git Commits Scraper

Git 提交数据采集工具，用于从 GitLab 仓库批量抓取 Git 提交记录并发送到指定的 API 端点。

## 功能特性

- **项目同步**: 从 GitLab 同步项目列表到本地数据库
- **批量采集**: 支持多进程并发采集 Git 提交数据
- **状态管理**: 完整的采集状态跟踪和错误重试机制
- **数据发送**: 将采集的数据发送到指定的 API 端点
- **SQL 查询**: 支持直接执行 SQL 查询数据库

## 核心组件

- `cli.py` - 命令行接口，提供所有功能的入口
- `sync_projects.py` - GitLab 项目同步器
- `scrap_state.py` - 仓库状态管理器和数据库操作
- `scrap_repos.py` - 批量采集逻辑
- `scrap_repo.py` - 单个仓库采集逻辑
- `perceval.py` - Perceval Git 命令包装器
- `send_jsons.py` - 数据发送器

## 常用命令

### 项目同步

从 GitLab 同步项目到本地数据库：

```bash
source test.env && uv run data_scrap/tools/gitcommits/cli.py sync_projects --limit 100
```

### 查看状态

查看当前待采集的仓库：

```bash
source test.env && uv run data_scrap/tools/gitcommits/cli.py list_pending --limit 20
```

### 批量采集

启动批量采集：

```bash
# 采集一批仓库（默认批次大小）
source test.env && uv run data_scrap/tools/gitcommits/cli.py scrap_repos --batch_size 10

# 采集所有待处理的仓库
source test.env && uv run data_scrap/tools/gitcommits/cli.py scrap_all --batch_size 20
```

### 单个仓库采集

采集指定仓库：

```bash
source test.env && uv run data_scrap/tools/gitcommits/cli.py scrap_repo \
  --repo_url "https://gitlab.example.com/project/repo.git" \
  --start_date "2024-01-01" \
  --end_date "2024-12-31"
```

### 数据发送

发送采集的 JSON 数据到 API：

```bash
# 发送目录下所有 JSONL 文件
source test.env && uv run data_scrap/tools/gitcommits/cli.py send_jsons --json_dir jsons

# 发送单个文件
source test.env && uv run data_scrap/tools/gitcommits/cli.py send_jsons --json_file /path/to/file.jsonl
```

### SQL 查询

直接查询数据库：

```bash
# 查看统计信息
source test.env && uv run data_scrap/tools/gitcommits/cli.py sql "SELECT status, COUNT(*) FROM repo_status GROUP BY status"

# 查看最近更新的仓库
source test.env && uv run data_scrap/tools/gitcommits/cli.py sql "SELECT repo_name, status, updated_at FROM repo_status ORDER BY updated_at DESC LIMIT 10"
```

### 状态管理

重置所有仓库状态：

```bash
source test.env && uv run data_scrap/tools/gitcommits/cli.py reset_all_repos
```

## Jupyter/IPython 使用

在 Jupyter notebook 或 IPython 中进行交互式查询：

```python
from data_scrap.tools.gitcommits.scrap_state import get_db_helper

# 获取数据库连接
db = get_db_helper()

# 执行 SQL 查询
results = db.execute_sql("SELECT * FROM repo_status WHERE status = 'failed' LIMIT 5")

# 查看结果
for repo in results:
    print(f"{repo['repo_name']}: {repo['error_message']}")

# 关闭连接
db.close()
```

## 配置

确保在配置文件中设置以下环境变量：

- `GITLAB_URL` - GitLab 实例 URL
- `GITLAB_TOKEN` - GitLab API 访问令牌
- `REPO_DB_PATH` - 数据库文件路径
- `EVENT_RECEIVER_URL` - 数据接收 API 端点

## 数据库表结构

`repo_status` 表字段说明：

- `id` - 主键ID
- `repo_name` - 仓库名称
- `repo_url` - 仓库 URL
- `status` - 状态 (pending/processing/completed/failed)
- `last_activity_at` - 最后活动时间
- `last_collected_at` - 最后采集时间
- `next_collect_at` - 下次采集时间
- `retry_count` - 重试次数
- `error_message` - 错误信息
- `branches_info` - 分支信息 (JSON)

## 数据格式

采集的提交数据以 JSONL 格式存储，每行一个 JSON 对象，包含完整的 Git 提交信息和元数据。

podman pull artifactory.ep.chehejia.com/ep-docker-test-local/portal/data_scrap_gitcommits:v1


podman run --rm -it  -v ~/.ssh:/root/.ssh -v $(pwd):/app/data/data_scrap/storage   artifactory.ep.chehejia.com/ep-docker-test-local/portal/data_scrap_gitcommits:v1 /bin/bash


source storage/test.env  && uv run data_scrap/tools/gitcommits/cli.py  sync_projects -d storage/repo_status.duckdb  -l 50000


source storage/test.env  && uv run data_scrap/tools/gitcommits/cli.py  scrap_repos -s '2025-06-28' --dry_run --db_path storage/repo_status.duckdb  --output_dir storage/jsons/



source storage/test.env  && uv run data_scrap/tools/gitcommits/cli.py  scrap_all -s '2025-06-28' --dry_run --db_path storage/repo_status.duckdb  --output_dir storage/jsons/


source storage/test.env  && uv run data_scrap/tools/gitcommits/cli.py send_jsons --json-dir storage/jsons/
