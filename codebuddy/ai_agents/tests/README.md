# AI Agents 测试架构

## 测试分类

### 1. 单元测试 (Unit Tests)
- **标记**: `@pytest.mark.unit` 或无标记（自动添加unit标记）
- **特点**:
  - 不调用真实LLM API
  - 使用mock模拟外部依赖
  - 执行速度快
  - 适合CI环境
- **运行方式**:
  ```bash
  source local.env && uv run pytest -vv -s -m unit
  ```

### 2. LLM集成测试 (LLM Integration Tests)
- **标记**: `@pytest.mark.llm`
- **特点**:
  - 需要真实LLM API调用
  - 需要配置LLM_API_BASE和LLM_API_KEY
  - 仅在本地调试时运行
  - 成本较高，数量精简
- **运行方式**:
  ```bash
  source local.env && uv run pytest -vv -s -m llm
  ```

## 常用测试命令

### 运行所有单元测试
```bash
source local.env && uv run pytest -vv -s -m unit
```

### 运行所有LLM测试
```bash
source local.env && uv run pytest -vv -s -m llm
```

### 运行所有测试（包括LLM）
```bash
source local.env && uv run pytest -vv -s
```

### 运行特定文件的测试
```bash
source local.env && uv run pytest -vv -s tests/core/test_model_config.py
```

### 运行CI友好的测试（排除LLM测试）
```bash
source local.env && uv run pytest -vv -s -m "not llm"
```

## 测试编写指南

### 单元测试示例
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit  # 可选，没有标记会自动添加
class TestMyClass:
    @patch('module.external_api_call')
    def test_method_with_mock(self, mock_api):
        # 使用mock模拟外部调用
        mock_api.return_value = "mocked_response"
        # 测试逻辑...
```

### LLM集成测试示例
```python
import pytest
from tests.test_config import skip_if_no_llm_config

@pytest.mark.llm
class TestMyLLMIntegration:
    def setup_method(self):
        skip_if_no_llm_config()
        # 初始化真实LLM客户端...

    def test_real_llm_call(self):
        # 真实LLM API调用测试...
```

## 环境配置

确保在`test.env`或`local.env`文件中配置了必要的环境变量：
```bash
LLM_API_BASE=https://your-api-base
LLM_API_KEY=your-api-key
TEST_REPO_PATH=/path/to/test/repository

# 模型配置（支持OpenAI兼容的API）
FAST_MODEL=your-model-name
POWERFUL_MODEL=your-powerful-model-name
SUMMARY_MODEL=your-summary-model-name
```

### OpenAI兼容API配置
模型前面加上 `openai/` 前缀。

示例配置：
```bash
LLM_API_BASE="http://localhost:7000/v3/openai/v1"
LLM_API_KEY="your-api-key"
FAST_MODEL="openai/lpai_qwen3-30b-a3b"  # 自定义模型名称
```

## 注意事项

1. **默认标记**: 没有明确标记的测试会自动添加`@pytest.mark.unit`标记
2. **LLM测试**: 只在有API配置且非CI环境时运行
3. **成本控制**: LLM测试应该精简，只测试关键功能
4. **CI兼容**: 单元测试应该能在CI环境中稳定运行
