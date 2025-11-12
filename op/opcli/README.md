# OPCLI

开放平台命令行工具

## 项目简介

OPCLI 是一个用于运维操作的命令行工具，提供与飞书等平台的集成功能。通过命令行方式快速查询群聊信息、获取消息记录、统计数据等。

## 功能特性

- 飞书（Lark）平台集成
  - 搜索群聊
  - 获取群聊详细信息
  - 获取历史消息
  - 群聊统计分析（消息数、表情回复数等）
- 可扩展的组件架构
- 支持 JSON 和表格两种输出格式

## 安装

```bash
uv install
```

## 配置

在项目根目录创建 `local.env` 文件，配置飞书应用凭证：

```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

## 使用示例

### 查看帮助

```bash
uv run opcli --help
uv run opcli feishu --help
```

### 搜索群聊

```bash
# 搜索包含关键词的群聊
source local.env && uv run opcli feishu search-groups "产品讨论"

# 限制返回结果数量
source local.env && uv run opcli feishu search-groups "技术" -n 5

# JSON 格式输出
source local.env && uv run opcli feishu search-groups "运营" -o json
```

### 获取群聊详细信息

```bash
# 获取指定群聊的详细信息
source local.env && uv run opcli feishu get-group oc_abc123xyz

# JSON 格式输出
source local.env && uv run opcli feishu get-group oc_abc123xyz -o json
```

### 获取历史消息

```bash
# 获取群聊最近 50 条消息
source local.env && uv run opcli feishu get-messages oc_abc123xyz

# 获取指定日期范围的消息
source local.env && uv run opcli feishu get-messages oc_abc123xyz \
  --start-date 2025-10-01 --end-date 2025-11-01

# 获取更多消息（最多 100 条）
source local.env && uv run opcli feishu get-messages oc_abc123xyz -n 100
```

### 群聊统计分析

```bash
# 获取群聊统计信息（包含消息数和表情回复数）
source local.env && uv run opcli feishu group-stats oc_42025a545d05037ce4f140928aca8ae6

# 指定日期范围统计
source local.env && uv run opcli feishu group-stats \
  --start-date 2025-10-05 \
  --end-date 2025-11-05 \
  oc_42025a545d05037ce4f140928aca8ae6

# 获取更多消息并以 JSON 格式输出
source local.env && uv run opcli feishu group-stats \
  oc_42025a545d05037ce4f140928aca8ae6 \
  -n 100 -o json


## 项目结构

```
opcli/
├── cli/                    # 命令行接口
│   ├── main.py            # 主入口
│   └── feishu.py          # 飞书相关命令
├── components/            # 功能组件
│   └── im/               # 即时通讯相关
│       ├── feishu.py     # 飞书客户端
│       ├── feishu_group.py   # 群聊管理
│       └── feishu_msg.py     # 消息处理
└── config.py             # 配置管理
```

## 开发

```bash
# 安装开发依赖
uv sync

# 运行测试
uv run pytest

# 代码格式化
uv run ruff format
```

## License

MIT
