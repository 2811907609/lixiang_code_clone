"""
代码编辑分析相关的prompt

包含编辑需求分析、策略选择等通用prompt。
"""

EDIT_ANALYSIS_PROMPT = """
请分析以下代码编辑需求，并以JSON格式返回分析结果：

## 编辑需求
{edit_request}

## 文件信息
文件路径: {file_path}
文件类型: {file_type}

## 目标代码
```{file_type}
{target_code}
```

## 上下文信息
{context_info}

## 分析要求
请分析并返回以下信息的JSON格式：

```json
{{
    "edit_type": "替换|插入|删除|重构|重命名",
    "complexity": "简单|中等|复杂",
    "scope": "单行|多行|函数|类|文件",
    "target_elements": ["具体的目标元素列表"],
    "dependencies": ["可能影响的其他代码元素"],
    "risk_level": "低|中|高",
    "estimated_changes": "预估的修改行数",
    "special_considerations": ["需要特别注意的事项"],
    "recommended_approach": "建议的处理方法"
}}
```

## 分析指导
1. **编辑类型**：
   - 替换：修改现有代码内容
   - 插入：添加新的代码
   - 删除：移除现有代码
   - 重构：重新组织代码结构
   - 重命名：修改标识符名称

2. **复杂度评估**：
   - 简单：单一、明确的修改
   - 中等：涉及多个相关修改
   - 复杂：需要理解复杂逻辑或大范围重构

3. **影响范围**：
   - 单行：只影响一行代码
   - 多行：影响连续的几行代码
   - 函数：影响整个函数
   - 类：影响整个类
   - 文件：影响多个函数/类

4. **风险评估**：
   - 低：不太可能引入错误
   - 中：需要仔细验证
   - 高：可能影响系统稳定性

请仅返回JSON格式的分析结果，不要包含其他解释。
"""

STRATEGY_SELECTION_PROMPT = """
根据代码编辑分析结果，选择最适合的编辑策略：

## 分析结果
{analysis_result}

## 可用策略

### 1. Cline SEARCH/REPLACE
**适用场景**：
- 简单到中等复杂度的修改
- 精确的搜索替换操作
- 多个小范围的同时修改
- 函数/变量重命名

**优势**：
- 直观易懂的格式
- 多层次匹配策略
- 支持多块同时编辑
- 错误信息详细

**限制**：
- 需要精确的搜索内容
- 不适合大范围重构
- 对复杂上下文支持有限

### 2. Codex 结构化补丁
**适用场景**：
- 复杂的代码重构
- 需要精确上下文定位
- 大范围的结构调整
- Unicode字符处理

**优势**：
- 强大的上下文定位
- Unicode标准化支持
- 适合复杂重构
- 多层次匹配策略

**限制**：
- 格式相对复杂
- 简单修改可能过度设计
- 需要准确的上下文标记

## 选择标准

请根据以下标准选择策略并以JSON格式返回：

```json
{{
    "recommended_strategy": "cline|codex",
    "confidence": "高|中|低",
    "reasoning": "选择理由的详细说明",
    "alternative_strategy": "备选策略（如果适用）",
    "special_instructions": ["特殊注意事项"],
    "expected_success_rate": "预期成功率百分比"
}}
```

## 决策矩阵

| 因素 | Cline优势 | Codex优势 |
|------|-----------|-----------|
| 复杂度 | 简单-中等 | 中等-复杂 |
| 范围 | 单行-多行 | 函数-文件 |
| 上下文需求 | 低-中 | 中-高 |
| 重构程度 | 低 | 高 |
| Unicode处理 | 基础 | 强大 |

请仅返回JSON格式的策略选择结果。
"""

CODE_LOCATION_ANALYSIS_PROMPT = """
分析代码中的目标位置，为编辑操作提供精确定位信息：

## 文件内容
```{file_type}
{file_content}
```

## 编辑目标
{edit_target}

## 分析要求
请分析并返回目标代码的位置信息：

```json
{{
    "target_lines": [起始行号, 结束行号],
    "target_function": "所在函数名（如果适用）",
    "target_class": "所在类名（如果适用）",
    "context_before": "目标前的上下文代码",
    "context_after": "目标后的上下文代码",
    "exact_match": "精确的目标代码内容",
    "surrounding_structure": "周围的代码结构描述",
    "unique_identifiers": ["可用于定位的唯一标识符"],
    "potential_conflicts": ["可能的冲突或歧义"]
}}
```

## 定位指导
1. 找到最精确的目标代码片段
2. 识别周围的稳定上下文
3. 确定唯一的定位标识符
4. 评估潜在的匹配冲突

请仅返回JSON格式的位置分析结果。
"""


def get_edit_analysis_prompt(edit_request: str, file_path: str, file_type: str,
                           target_code: str, context_info: str = "") -> str:
    """
    生成编辑分析prompt

    Args:
        edit_request: 编辑需求描述
        file_path: 文件路径
        file_type: 文件类型
        target_code: 目标代码
        context_info: 上下文信息

    Returns:
        str: 完整的分析prompt
    """
    return EDIT_ANALYSIS_PROMPT.format(
        edit_request=edit_request,
        file_path=file_path,
        file_type=file_type,
        target_code=target_code,
        context_info=context_info or "无额外上下文"
    )


def get_strategy_selection_prompt(analysis_result: str) -> str:
    """
    生成策略选择prompt

    Args:
        analysis_result: 编辑分析结果（JSON字符串）

    Returns:
        str: 策略选择prompt
    """
    return STRATEGY_SELECTION_PROMPT.format(analysis_result=analysis_result)


def get_code_location_prompt(file_content: str, file_type: str, edit_target: str) -> str:
    """
    生成代码位置分析prompt

    Args:
        file_content: 文件内容
        file_type: 文件类型
        edit_target: 编辑目标描述

    Returns:
        str: 位置分析prompt
    """
    return CODE_LOCATION_ANALYSIS_PROMPT.format(
        file_content=file_content,
        file_type=file_type,
        edit_target=edit_target
    )
