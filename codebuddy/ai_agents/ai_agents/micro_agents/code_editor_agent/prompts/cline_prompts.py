"""
Cline格式相关的prompt和指导

包含Cline SEARCH/REPLACE格式的详细说明、最佳实践和示例。
"""

CLINE_FORMAT_INSTRUCTION = """
使用Cline SEARCH/REPLACE格式进行代码编辑：

## 基本格式
------- SEARCH
[要搜索的精确代码内容]
=======
[要替换的新代码内容]
+++++++ REPLACE

## 核心原则
1. **精确匹配**: SEARCH块必须与文件中的内容完全一致
2. **保持缩进**: 替换内容应保持适当的缩进风格
3. **最小化范围**: 只包含需要修改的最小代码块
4. **多块支持**: 可以在一个操作中包含多个SEARCH/REPLACE块

## 匹配策略（按优先级）
1. **精确匹配** - 字符串完全相同
2. **行级trim匹配** - 忽略每行首尾空白符
3. **块锚点匹配** - 对于大代码块，使用首尾行作为锚点

## 适用场景
- ✅ 简单的函数/变量重命名
- ✅ 单行或少量行的内容替换
- ✅ 精确的代码片段修改
- ✅ 多个小范围的同时修改
- ❌ 大范围的代码重构
- ❌ 复杂的上下文相关修改

## 注意事项
- 确保SEARCH内容与文件中的代码完全匹配
- 注意空白符、缩进和换行符
- 对于多行代码，保持原有的缩进结构
- 如果不确定精确内容，可以先查看文件
"""

CLINE_GENERATION_PROMPT = """
请根据以下信息生成Cline格式的代码编辑指令：

文件路径: {file_path}
编辑需求: {edit_request}
目标代码位置: {target_location}
原始代码片段:
```
{original_code}
```

要求：
1. 生成精确的SEARCH/REPLACE块
2. 确保SEARCH内容与原始代码完全匹配
3. REPLACE内容应满足编辑需求
4. 保持代码的缩进和格式风格
5. 如果需要多个修改，可以生成多个SEARCH/REPLACE块

请直接输出Cline格式的编辑指令，不要包含其他解释。
"""

CLINE_ERROR_RECOVERY_PROMPT = """
Cline编辑操作失败，错误信息：{error_message}

原始编辑指令：
{original_instruction}

请分析失败原因并生成修正后的Cline指令：

常见失败原因和解决方案：
1. **搜索内容不匹配** - 检查空白符、缩进、换行符
2. **内容已被修改** - 重新获取最新的文件内容
3. **搜索范围过大** - 缩小到最小必要的代码块
4. **特殊字符问题** - 注意引号、转义字符等

请提供修正后的Cline指令：
"""

CLINE_BEST_PRACTICES = """
Cline格式最佳实践：

## 1. 搜索内容选择
- 选择独特且稳定的代码片段
- 避免包含可能变化的注释或空行
- 优先选择函数签名、类定义等结构性代码

## 2. 替换内容设计
- 保持与原代码相同的缩进风格
- 维护代码的语法正确性
- 考虑对其他代码的影响

## 3. 多块编辑策略
- 按逻辑顺序排列多个SEARCH/REPLACE块
- 避免块之间的相互依赖
- 确保每个块都是独立可执行的

## 4. 错误预防
- 仔细检查搜索内容的准确性
- 测试替换内容的语法正确性
- 考虑边界情况和特殊字符

## 5. 性能优化
- 优先使用精确匹配
- 避免过长的搜索内容
- 合理利用块锚点匹配特性
"""


def get_cline_instruction_prompt(file_path: str, edit_request: str,
                                target_location: str, original_code: str) -> str:
    """
    生成Cline格式指令的prompt

    Args:
        file_path: 文件路径
        edit_request: 编辑需求描述
        target_location: 目标代码位置描述
        original_code: 原始代码片段

    Returns:
        str: 完整的prompt
    """
    return CLINE_GENERATION_PROMPT.format(
        file_path=file_path,
        edit_request=edit_request,
        target_location=target_location,
        original_code=original_code
    )


def get_cline_error_recovery_prompt(error_message: str, original_instruction: str) -> str:
    """
    生成Cline错误恢复的prompt

    Args:
        error_message: 错误信息
        original_instruction: 原始编辑指令

    Returns:
        str: 错误恢复prompt
    """
    return CLINE_ERROR_RECOVERY_PROMPT.format(
        error_message=error_message,
        original_instruction=original_instruction
    )


def get_cline_format_guide() -> str:
    """获取Cline格式完整指南"""
    return f"{CLINE_FORMAT_INSTRUCTION}\n\n{CLINE_BEST_PRACTICES}"
