"""代码审查结果验证模块"""

import json


class ValidationError(Exception):
    """验证错误基类"""
    pass


class QueryValidationError(ValidationError):
    """查询验证错误"""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion


class ReviewResultValidationError(ValidationError):
    """审查结果验证错误"""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion


class ParameterValidationError(ValidationError):
    """参数验证错误"""
    def __init__(self, message, missing_fields=None, invalid_fields=None):
        super().__init__(message)
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []


def validate_review_result_format(result, memory) -> bool:
    """
    验证审查结果的数据结构是否正确

    要求的数据结构格式：
    [
        {
            "relevantFile": "问题文件的完整路径",
            "existingCode": "有问题的代码片段(必须来自diff中的+行)",
            "suggestionContent": "问题分析：原因+影响+解决方案",
            "improvedCode": "修复后的完整代码示例",
            "label": "问题类型标签",
            "suggestionLine": "问题行号(数字)"
        }
    ]

    Args:
        result: 审查结果
        memory: Agent的内存对象（框架传递，本函数中未使用）

    Returns:
        bool: 如果格式正确返回True，否则抛出异常

    Raises:
        Exception: 当数据结构不正确时抛出详细的错误信息
    """
    try:
        # 判断输入类型并解析
        if isinstance(result, str):
            # 如果是字符串，尝试解析JSON
            try:
                parsed_result = json.loads(result)
            except json.JSONDecodeError as e:
                raise ReviewResultValidationError(
                    f"返回结果不是有效的JSON格式。错误详情：{str(e)}",
                    suggestion="请确保返回的是正确的JSON数组格式，例如：\n"
                              '[{"relevantFile": "...", "existingCode": "...", ...}]'
                )
        elif isinstance(result, list):
            # 如果已经是list，直接使用
            parsed_result = result
        else:
            # 其他类型直接抛出异常
            raise ReviewResultValidationError(
                f"返回结果类型不支持，当前类型：{type(result).__name__}",
                suggestion="仅支持JSON字符串或列表类型，请确保返回正确的数据格式"
            )

        # 检查是否为列表
        if not isinstance(parsed_result, list):
            raise ReviewResultValidationError(
                f"返回结果必须是一个数组（列表），当前类型：{type(parsed_result).__name__}",
                suggestion="正确格式示例：[{...}] 而不是 {...}"
            )

        # 检查是否为空列表
        if len(parsed_result) == 0:
            # 空列表是允许的，表示没有发现问题
            return True

        # 定义必需的字段
        required_fields = {
            "relevantFile": str,
            "existingCode": str,
            "suggestionContent": str,
            "improvedCode": str,
            "label": str,
            "suggestionLine": (int, str)  # 允许字符串类型的数字
        }

        # 检查每个元素
        for index, item in enumerate(parsed_result):
            if not isinstance(item, dict):
                raise ReviewResultValidationError(
                    f"数组中第{index+1}个元素必须是对象（字典），当前类型：{type(item).__name__}",
                    suggestion="正确格式：{'relevantFile': '...', 'existingCode': '...', ...}"
                )

            # 检查必需字段是否存在
            missing_fields = []
            for field_name in required_fields.keys():
                if field_name not in item:
                    missing_fields.append(field_name)

            if missing_fields:
                raise ParameterValidationError(
                    f"第{index+1}个元素缺少必需字段：{', '.join(missing_fields)}\n"
                    f"必需字段包括：{', '.join(required_fields.keys())}\n"
                    f"当前元素字段：{', '.join(item.keys())}",
                    missing_fields=missing_fields
                )

            # 检查字段类型
            for field_name, expected_types in required_fields.items():
                field_value = item[field_name]

                # 特殊处理 suggestionLine 字段
                if field_name == "suggestionLine":
                    # 尝试将字符串转换为数字
                    if isinstance(field_value, str):
                        try:
                            int(field_value)
                        except ValueError:
                            raise ParameterValidationError(
                                f"第{index+1}个元素的 '{field_name}' 字段必须是数字或可转换为数字的字符串，当前值：'{field_value}'",
                                invalid_fields=[field_name]
                            )
                    elif not isinstance(field_value, int):
                        raise ParameterValidationError(
                            f"第{index+1}个元素的 '{field_name}' 字段必须是数字，当前类型：{type(field_value).__name__}",
                            invalid_fields=[field_name]
                        )
                else:
                    # 检查其他字段类型
                    if not isinstance(field_value, expected_types):
                        expected_type_names = expected_types.__name__ if hasattr(expected_types, '__name__') else str(expected_types)
                        raise ParameterValidationError(
                            f"第{index+1}个元素的 '{field_name}' 字段类型错误。期望：{expected_type_names}，实际：{type(field_value).__name__}",
                            invalid_fields=[field_name]
                        )

                # 检查字符串字段是否为空
                if isinstance(field_value, str) and field_value.strip() == "":
                    raise ParameterValidationError(
                        f"第{index+1}个元素的 '{field_name}' 字段不能为空字符串",
                        invalid_fields=[field_name]
                    )

        return True

    except ValidationError:
        # 自定义异常直接重新抛出，不需要额外处理
        raise
    except Exception as e:
        # 其他异常转换为 ReviewResultValidationError
        error_msg = str(e)
        suggestion = ("请检查返回的数据结构，确保符合要求的格式：\n"
                     "[\n"
                     "  {\n"
                     '    "relevantFile": "文件路径",\n'
                     '    "existingCode": "问题代码",\n'
                     '    "suggestionContent": "分析内容",\n'
                     '    "improvedCode": "修复代码",\n'
                     '    "label": "问题类型",\n'
                     '    "suggestionLine": 行号数字\n'
                     "  }\n"
                     "]")

        raise ReviewResultValidationError(f"{error_msg}\n\n修复建议：\n{suggestion}")
