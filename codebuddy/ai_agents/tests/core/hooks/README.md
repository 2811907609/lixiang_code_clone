# Hook 系统综合测试套件

本目录包含 AI Agents Hook 系统集成的综合测试套件。该测试套件验证 hook 系统功能、性能、错误处理和向后兼容性的所有方面。

## 测试结构

### 测试文件

- **`test_end_to_end_integration.py`** - 完整 hook 工作流的端到端集成测试
- **`test_performance.py`** - 测量 hook 执行开销和可扩展性的性能测试
- **`test_error_scenarios.py`** - 超时处理和失败情况的错误场景测试
- **`test_configuration_integration.py`** - 多配置源的配置集成测试
- **`test_backward_compatibility.py`** - 确保现有工具不变的向后兼容性测试
- **`test_documentation.py`** - 所有公共 API 的文档测试

### 测试夹具

- **`fixtures/sample_configs/`** - 用于测试的示例 JSON 配置文件

  - `basic_hooks.json` - 基本 hook 配置
  - `complex_hooks.json` - 带决策的复杂 hook 配置
  - `invalid_config.json` - 用于错误测试的无效配置
  - `malformed.json` - 用于错误测试的格式错误 JSON

- **`fixtures/test_scripts/`** - 用于 hook 执行测试的测试脚本
  - `validator.py` - 基本验证 hook 脚本
  - `decision_hook.py` - 返回 JSON 决策的 hook 脚本
  - `blocking_hook.py` - 阻止操作的 hook 脚本
  - `json_response_hook.py` - 带结构化 JSON 响应的 hook 脚本
  - `error_logger.py` - 用于错误日志记录的 hook 脚本
  - `timeout_hook.py` - 超时的 hook 脚本
  - `failing_hook.py` - 具有各种失败模式的 hook 脚本

### 测试工具

- **`run_comprehensive_tests.py`** - 执行所有测试套件的综合测试运行器
- **`test_suite_verification.py`** - 检查测试套件完整性的验证脚本

## 运行测试

### 快速测试运行

运行特定测试文件：

```bash
uv run python -m pytest tests/core/hooks/test_end_to_end_integration.py -v
```

### 综合测试套件

运行所有测试并生成详细报告：

```bash
uv run python tests/core/hooks/run_comprehensive_tests.py
```

### 验证

验证测试套件完整性：

```bash
uv run python tests/core/hooks/test_suite_verification.py
```

### 单独测试类别

运行特定测试类别：

```bash
# 端到端集成测试
uv run python -m pytest tests/core/hooks/test_end_to_end_integration.py -v

# 性能测试
uv run python -m pytest tests/core/hooks/test_performance.py -v

# 错误场景测试
uv run python -m pytest tests/core/hooks/test_error_scenarios.py -v

# 配置集成测试
uv run python -m pytest tests/core/hooks/test_configuration_integration.py -v

# 向后兼容性测试
uv run python -m pytest tests/core/hooks/test_backward_compatibility.py -v

# 文档测试
uv run python -m pytest tests/core/hooks/test_documentation.py -v
```

## 测试覆盖范围

测试套件涵盖以下领域：

### 端到端集成（9 个测试）

- 基本 hook 工作流执行
- 复杂决策工作流（允许/拒绝/询问）
- 阻塞 hook 工作流
- 错误 hook 工作流
- JSON 响应解析
- 模式匹配工作流
- 多配置源
- 工具装饰器集成

### 性能（7 个测试）

- Hook 执行开销测量
- 多 hook 性能
- 模式匹配性能
- 并发 hook 执行
- 内存使用稳定性
- Hook 超时性能
- 负载下的系统可扩展性

### 错误场景（15+个测试）

- 脚本 hook 超时
- Python hook 超时
- 脚本 hook 失败（各种退出代码）
- Python hook 异常
- 无效配置
- 格式错误的 JSON 处理
- 缺失文件处理
- 错误恢复机制
- 错误时的资源清理

### 配置集成（12+个测试）

- 单一配置源加载
- 多配置合并
- 配置优先级处理
- 部分配置文件
- 空配置文件
- 配置验证
- 路径解析（相对、绝对、~）
- 配置重新加载
- 混合配置和编程式 hook

### 向后兼容性（15+个测试）

- 简单工具不变
- 多参数工具
- 复杂返回类型
- 异常处理保持
- 副作用保持
- 性能影响最小
- 元数据保持
- 传统工具模式
- 工具组合模式
- 有状态工具

### 文档（10+个测试）

- 公共 API 文档完整性
- 文档示例验证
- API 签名稳定性
- 参数文档一致性
- 返回类型文档
- 异常文档
- 使用示例验证

## 测试需求验证

测试套件验证规范中的所有需求：

### 需求 1 - JSON 配置

- ✅ 从多个源加载配置
- ✅ 基于配置的 Hook 执行
- ✅ 通过 stdin 传递工具信息
- ✅ 退出代码处理（0、2、其他）

### 需求 2 - 编程式注册

- ✅ Python 函数注册
- ✅ 带参数的函数执行
- ✅ 异常处理
- ✅ 多 hook 执行顺序
- ✅ 决策对象处理

### 需求 3 - 模式匹配

- ✅ 精确字符串匹配
- ✅ 正则表达式模式匹配
- ✅ 通配符匹配
- ✅ 多匹配器执行

### 需求 4 - 安全和错误处理

- ✅ 超时强制执行
- ✅ 超时时进程终止
- ✅ 错误捕获和日志记录
- ✅ 输入清理
- ✅ 文件系统权限尊重

### 需求 5 - 日志记录和调试

- ✅ Hook 执行日志记录
- ✅ 错误输出日志记录
- ✅ 调试模式详细日志记录
- ✅ 决策日志记录
- ✅ 配置错误报告

### 需求 6 - 工具执行控制

- ✅ 预 hook 拒绝阻塞
- ✅ 用户确认提示
- ✅ 后 hook 反馈阻塞
- ✅ 附加上下文注入
- ✅ 工具参数修改

## 性能基准

性能测试建立了以下基准：

- **Hook 开销**：简单 hook 的开销 < 50%
- **模式匹配**：复杂模式 < 10ms
- **超时处理**：1s 超时 < 3s
- **内存使用**：1000 次执行增加 < 50MB
- **并发执行**：正确处理多个同时 hook

## 错误处理覆盖

错误场景测试涵盖：

- **超时场景**：脚本和 Python hook 超时
- **失败模式**：各种退出代码和异常
- **配置错误**：无效、格式错误和缺失的配置
- **资源管理**：失败时的正确清理
- **恢复机制**：优雅降级和错误隔离

## 向后兼容性保证

向后兼容性测试确保：

- **零破坏性更改**：现有工具工作不变
- **性能保持**：不使用 hook 时开销最小
- **API 稳定性**：所有现有工具模式继续工作
- **元数据保持**：文档字符串、名称和签名保持
- **异常处理**：原始异常行为保持

## 贡献

添加新的 hook 系统功能时：

1. 在适当的测试文件中添加相应的测试
2. 如果需要新的配置格式，更新测试夹具
3. 为新功能添加性能测试
4. 确保向后兼容性测试通过
5. 为新的公共 API 更新文档测试
6. 运行综合测试套件以验证所有测试通过

## 测试执行环境

测试设计为在项目的标准测试环境中运行：

- **Python**：3.12+
- **测试框架**：pytest
- **依赖项**：通过 uv 的所有项目依赖项
- **平台**：跨平台（在 macOS 上测试，应在 Linux/Windows 上工作）
- **隔离**：每个测试类重置 HookManager 单例
- **清理**：临时文件和资源得到正确清理

## 故障排除

### 常见问题

1. **权限错误**：确保 `fixtures/test_scripts/` 中的测试脚本可执行
2. **超时问题**：某些测试在较慢的系统上可能需要更长时间 - 如需要可调整超时预期
3. **导入错误**：确保所有 hook 系统模块正确安装
4. **配置错误**：检查示例配置文件是否为有效 JSON

### 调试模式

使用详细输出运行测试：

```bash
uv run python -m pytest tests/core/hooks/ -v -s --tb=long
```

### 性能问题

如果性能测试因系统负载而失败：

```bash
# 单独运行性能测试
uv run python -m pytest tests/core/hooks/test_performance.py -v --tb=short
```
