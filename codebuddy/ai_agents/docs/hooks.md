# Hooks 钩子系统

Hooks 钩子系统允许你在 AI Agent 执行特定操作时自动运行自定义脚本，实现工作流程的自动化和扩展。

## 配置

钩子在配置文件中定义，支持以下配置位置：
- `~/.ai_agents/settings.json` - 用户全局设置
- `.ai_agents/settings.json` - 项目设置
- `.ai_agents/settings.local.json` - 本地项目设置（不提交到版本控制）

### 配置结构

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**配置说明：**
- `matcher`: 匹配工具名称的模式（仅适用于 PreToolUse 和 PostToolUse）
  - 简单字符串：精确匹配，如 `"Write"` 只匹配 Write 工具
  - 正则表达式：如 `"Edit|Write"` 或 `"File.*"`
  - 通配符：使用 `"*"` 匹配所有工具
- `hooks`: 匹配时执行的命令数组
  - `type`: 目前只支持 `"command"`
  - `command`: 要执行的 bash 命令
  - `timeout`: 可选，命令超时时间（秒）

对于不使用 matcher 的事件（如 UserPromptSubmit），可以省略 matcher 字段：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/prompt-validator.py"
          }
        ]
      }
    ]
  }
}
```

## 支持的钩子事件

### PreToolUse - 工具使用前

在 AI Agent 创建工具参数之后、处理工具调用之前运行。

**常用匹配器：**
- `"FileReader"` - 文件读取
- `"FileWriter"` - 文件写入
- `"CodeEditor"` - 代码编辑
- `"BashExecutor"` - Shell 命令执行
- `"*"` - 所有工具

**示例配置：**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "FileWriter",
        "hooks": [
          {
            "type": "command",
            "command": "echo '准备写入文件' >> /tmp/file-operations.log"
          }
        ]
      }
    ]
  }
}
```

### PostToolUse - 工具使用后

在工具成功完成后立即运行。

**示例配置：**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "CodeEditor",
        "hooks": [
          {
            "type": "command",
            "command": "python -m black $EDITED_FILE",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### UserPromptSubmit - 用户提示提交

在用户提交提示后、AI Agent 处理之前运行。可用于添加上下文、验证提示或阻止某些类型的提示。

**示例配置：**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/prompt-validator.py"
          }
        ]
      }
    ]
  }
}
```

## 钩子输入

钩子通过 stdin 接收 JSON 格式的会话信息和事件特定数据：

```json
{
  "session_id": "abc123",
  "cwd": "/current/working/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "FileWriter",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "文件内容"
  }
}
```

### PreToolUse 输入示例

```json
{
  "session_id": "abc123",
  "cwd": "/project/path",
  "hook_event_name": "PreToolUse",
  "tool_name": "FileWriter",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "文件内容"
  }
}
```

### PostToolUse 输入示例

```json
{
  "session_id": "abc123",
  "cwd": "/project/path",
  "hook_event_name": "PostToolUse",
  "tool_name": "FileWriter",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "文件内容"
  },
  "tool_response": {
    "success": true,
    "message": "文件写入成功"
  }
}
```

### UserPromptSubmit 输入示例

```json
{
  "session_id": "abc123",
  "cwd": "/project/path",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "请帮我写一个计算阶乘的函数"
}
```

## 钩子输出

钩子通过退出码、stdout 和 stderr 与系统通信：

### 简单方式：退出码

- **退出码 0**: 成功。stdout 内容会显示给用户
- **退出码 2**: 阻塞错误。stderr 内容会反馈给 AI Agent 自动处理
- **其他退出码**: 非阻塞错误。stderr 内容显示给用户，执行继续

**退出码 2 的行为：**
- `PreToolUse`: 阻止工具调用，将 stderr 显示给 AI Agent
- `PostToolUse`: 将 stderr 显示给 AI Agent（工具已执行）
- `UserPromptSubmit`: 阻止提示处理，清除提示，仅向用户显示 stderr

### 高级方式：JSON 输出

钩子可以在 stdout 中返回结构化 JSON 以实现更精细的控制：

#### 通用 JSON 字段

```json
{
  "continue": true,
  "stopReason": "停止原因",
  "suppressOutput": false
}
```

- `continue`: 钩子执行后是否继续（默认：true）
- `stopReason`: continue 为 false 时显示的消息
- `suppressOutput`: 是否隐藏 stdout 输出（默认：false）

#### PreToolUse 决策控制

```json
{
  "decision": "allow" | "deny" | "ask",
  "reason": "决策原因"
}
```

- `"allow"`: 允许工具调用
- `"deny"`: 阻止工具调用，reason 显示给 AI Agent
- `"ask"`: 询问用户确认

#### PostToolUse 决策控制

```json
{
  "decision": "block",
  "reason": "阻止原因"
}
```

- `"block"`: 自动向 AI Agent 提供 reason 信息

#### UserPromptSubmit 决策控制

```json
{
  "decision": "block",
  "reason": "阻止原因",
  "additionalContext": "额外上下文信息"
}
```

- `"block"`: 阻止提示处理，reason 显示给用户
- `"additionalContext"`: 如果不阻止，添加到上下文的字符串

## 实用示例

### 1. 代码格式化钩子

```python
#!/usr/bin/env python3
import json
import sys
import subprocess

# 读取输入
input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

if tool_name == "CodeEditor":
    file_path = tool_input.get("file_path", "")
    if file_path.endswith(".py"):
        # 运行 black 格式化
        try:
            subprocess.run(["black", file_path], check=True)
            print(f"已格式化 Python 文件: {file_path}")
        except subprocess.CalledProcessError:
            print(f"格式化失败: {file_path}", file=sys.stderr)
            sys.exit(1)

sys.exit(0)
```

### 2. 提示验证钩子

```python
#!/usr/bin/env python3
import json
import sys
import re

input_data = json.load(sys.stdin)
prompt = input_data.get("prompt", "")

# 检查敏感模式
sensitive_patterns = [
    (r"(?i)\b(password|secret|key|token)\s*[:=]", "提示包含潜在的敏感信息"),
]

for pattern, message in sensitive_patterns:
    if re.search(pattern, prompt):
        output = {
            "decision": "block",
            "reason": f"安全策略违规: {message}。请重新表述您的请求。"
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

# 添加当前时间上下文
import datetime
context = f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

output = {
    "additionalContext": context
}
print(json.dumps(output, ensure_ascii=False))
sys.exit(0)
```

### 3. 文件保护钩子

```python
#!/usr/bin/env python3
import json
import sys
import os

input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

if tool_name in ["FileWriter", "CodeEditor"]:
    file_path = tool_input.get("file_path", "")

    # 保护重要文件
    protected_files = [".env", "config.json", "secrets.yaml"]
    protected_dirs = [".git", "node_modules"]

    if any(protected in file_path for protected in protected_files + protected_dirs):
        output = {
            "decision": "deny",
            "reason": f"受保护的文件或目录: {file_path}"
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

sys.exit(0)
```

## 安全注意事项

**风险提醒**: 钩子系统会在您的系统上自动执行任意 shell 命令。使用钩子即表示您：
- 对配置的命令完全负责
- 了解钩子可以访问、修改或删除用户账户可访问的任何文件
- 理解恶意或编写不当的钩子可能导致数据丢失或系统损坏

### 安全最佳实践

1. **验证和清理输入** - 永远不要盲目信任输入数据
2. **总是引用 shell 变量** - 使用 `"$VAR"` 而不是 `$VAR`
4. **使用绝对路径** - 为脚本指定完整路径

## 调试

### 基本故障排除

如果钩子不工作：
1. **检查配置** - 确保 JSON 配置有效
2. **验证语法** - 确保 JSON 设置正确
3. **测试命令** - 先手动运行钩子命令
4. **检查权限** - 确保脚本可执行
5. **查看日志** - 使用调试模式查看钩子执行详情

常见问题：
- **命令未找到** - 为脚本使用完整路径

### 执行详情

- **超时**: 默认 60 秒执行限制，可按命令配置
- **环境**: 在当前目录中运行，使用 AI Agent 的环境
- **输入**: 通过 stdin 传递 JSON
- **输出**: 通过 stdout/stderr 和退出码通信
