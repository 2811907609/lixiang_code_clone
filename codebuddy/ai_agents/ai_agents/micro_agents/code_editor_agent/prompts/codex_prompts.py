"""
Codex格式相关的prompt和指导

包含OpenAI Codex结构化补丁格式的详细说明、最佳实践和示例。
"""

CODEX_FORMAT_INSTRUCTION = """
使用OpenAI Codex结构化补丁格式进行代码编辑：

## 基本格式
*** Begin Patch
*** Update File: [文件名]
@@ [可选的上下文标记]
[上下文行]
- [要删除的行]
+ [要添加的行]
[上下文行]
*** End Patch

## 核心特性
1. **上下文定位**: 使用@@ 标记和上下文行精确定位代码位置
2. **Unicode标准化**: 自动处理Unicode标点符号差异
3. **多层次匹配**: 精确匹配 → 忽略空白 → 模糊匹配
4. **结构化操作**: 支持Update/Add/Delete文件操作

## 上下文标记使用
- `@@ class ClassName:` - 定位到特定类
- `@@ def method_name():` - 定位到特定方法
- `@@ if condition:` - 定位到特定代码块
- 可以使用多个@@ 标记指定嵌套上下文

## 适用场景
- ✅ 复杂的代码重构
- ✅ 需要精确上下文定位的修改
- ✅ 大范围的代码结构调整
- ✅ 多个相关修改的组合
- ✅ Unicode字符处理
- ❌ 简单的单行替换（过于复杂）

## 匹配策略（按优先级）
1. **精确匹配** - Unicode标准化后完全相同
2. **忽略行尾空白** - 忽略每行末尾的空白字符
3. **忽略所有空白** - 忽略行首尾的所有空白字符

## 注意事项
- 删除行（-）必须与文件中的实际内容匹配
- 上下文行用于精确定位，通常需要2-3行
- 文件名应该是相对路径
- 支持复杂的代码结构变更
"""

CODEX_GENERATION_PROMPT = """
请根据以下信息生成Codex格式的代码编辑补丁：

文件路径: {file_path}
编辑需求: {edit_request}
目标代码位置: {target_location}
原始代码片段:
```
{original_code}
```
周围上下文:
```
{context_code}
```

要求：
1. 生成完整的Codex补丁格式
2. 使用适当的@@ 上下文标记定位代码
3. 包含足够的上下文行确保精确匹配
4. 删除行（-）必须与原始代码完全匹配
5. 添加行（+）应满足编辑需求
6. 保持代码的缩进和格式风格

请直接输出Codex格式的补丁，不要包含其他解释。
"""

CODEX_ERROR_RECOVERY_PROMPT = """
Codex补丁应用失败，错误信息：{error_message}

原始补丁：
{original_patch}

请分析失败原因并生成修正后的Codex补丁：

常见失败原因和解决方案：
1. **上下文不匹配** - 调整@@ 标记或上下文行
2. **删除行不匹配** - 检查实际文件内容，确保删除行准确
3. **Unicode字符问题** - 注意标点符号的Unicode变体
4. **缩进问题** - 确保上下文行的缩进正确
5. **文件路径错误** - 检查文件名是否正确

请提供修正后的Codex补丁：
"""

CODEX_BEST_PRACTICES = """
Codex格式最佳实践：

## 1. 上下文标记策略
- 使用层次化的@@ 标记：类 → 方法 → 代码块
- 选择独特且稳定的标识符
- 避免使用可能变化的注释作为标记

## 2. 上下文行选择
- 包含2-3行稳定的上下文
- 选择不太可能被修改的代码行
- 避免空行和注释行作为关键上下文

## 3. 删除/添加行设计
- 删除行必须与文件内容完全匹配
- 添加行保持一致的代码风格
- 考虑对周围代码的影响

## 4. Unicode处理
- 利用Codex的Unicode标准化特性
- 注意不同的引号、破折号等标点符号
- 测试特殊字符的处理

## 5. 复杂重构策略
- 将大的重构分解为多个小的补丁
- 确保每个补丁都是独立可应用的
- 考虑补丁应用的顺序

## 6. 错误预防
- 仔细验证上下文标记的准确性
- 测试删除行的精确匹配
- 考虑代码的语法正确性
"""


def get_codex_instruction_prompt(file_path: str, edit_request: str,
                                target_location: str, original_code: str,
                                context_code: str = "") -> str:
    """
    生成Codex格式补丁的prompt

    Args:
        file_path: 文件路径
        edit_request: 编辑需求描述
        target_location: 目标代码位置描述
        original_code: 原始代码片段
        context_code: 周围的上下文代码

    Returns:
        str: 完整的prompt
    """
    return CODEX_GENERATION_PROMPT.format(
        file_path=file_path,
        edit_request=edit_request,
        target_location=target_location,
        original_code=original_code,
        context_code=context_code or "无额外上下文"
    )


def get_codex_error_recovery_prompt(error_message: str, original_patch: str) -> str:
    """
    生成Codex错误恢复的prompt

    Args:
        error_message: 错误信息
        original_patch: 原始补丁内容

    Returns:
        str: 错误恢复prompt
    """
    return CODEX_ERROR_RECOVERY_PROMPT.format(
        error_message=error_message,
        original_patch=original_patch
    )


def get_codex_format_guide() -> str:
    """获取Codex格式完整指南"""
    return f"{CODEX_FORMAT_INSTRUCTION}\n\n{CODEX_BEST_PRACTICES}"
