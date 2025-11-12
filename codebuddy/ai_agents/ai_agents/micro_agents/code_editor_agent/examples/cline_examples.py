"""
Cline格式的示例库

包含各种场景下的Cline SEARCH/REPLACE示例，用于指导AI生成正确的编辑指令。
"""

from typing import List, Dict, Any

# Cline示例数据结构
CLINE_EXAMPLES = [
    {
        "id": "simple_function_rename",
        "description": "简单函数重命名",
        "edit_type": "重命名",
        "complexity": "简单",
        "scope": "单行",
        "language": "python",
        "original_code": """def calculate_sum(a, b):
    return a + b

def main():
    result = calculate_sum(1, 2)
    print(result)""",
        "edit_request": "将函数名calculate_sum改为compute_total",
        "cline_instruction": """------- SEARCH
def calculate_sum(a, b):
=======
def compute_total(a, b):
+++++++ REPLACE

------- SEARCH
    result = calculate_sum(1, 2)
=======
    result = compute_total(1, 2)
+++++++ REPLACE""",
        "expected_result": """def compute_total(a, b):
    return a + b

def main():
    result = compute_total(1, 2)
    print(result)""",
        "tags": ["函数重命名", "多处修改", "Python"]
    },

    {
        "id": "variable_rename",
        "description": "变量重命名",
        "edit_type": "重命名",
        "complexity": "简单",
        "scope": "多行",
        "language": "python",
        "original_code": """def process_data():
    user_input = get_input()
    processed_data = transform(user_input)
    save_result(processed_data)
    return processed_data""",
        "edit_request": "将变量user_input重命名为raw_data",
        "cline_instruction": """------- SEARCH
    user_input = get_input()
    processed_data = transform(user_input)
=======
    raw_data = get_input()
    processed_data = transform(raw_data)
+++++++ REPLACE""",
        "expected_result": """def process_data():
    raw_data = get_input()
    processed_data = transform(raw_data)
    save_result(processed_data)
    return processed_data""",
        "tags": ["变量重命名", "Python"]
    },

    {
        "id": "add_parameter",
        "description": "函数添加参数",
        "edit_type": "修改",
        "complexity": "中等",
        "scope": "多行",
        "language": "python",
        "original_code": """def send_email(subject, body):
    email = create_email(subject, body)
    smtp_send(email)

def notify_user():
    send_email("Alert", "Something happened")""",
        "edit_request": "为send_email函数添加recipient参数",
        "cline_instruction": """------- SEARCH
def send_email(subject, body):
    email = create_email(subject, body)
    smtp_send(email)
=======
def send_email(recipient, subject, body):
    email = create_email(subject, body)
    email.to = recipient
    smtp_send(email)
+++++++ REPLACE

------- SEARCH
    send_email("Alert", "Something happened")
=======
    send_email("user@example.com", "Alert", "Something happened")
+++++++ REPLACE""",
        "expected_result": """def send_email(recipient, subject, body):
    email = create_email(subject, body)
    email.to = recipient
    smtp_send(email)

def notify_user():
    send_email("user@example.com", "Alert", "Something happened")""",
        "tags": ["函数修改", "参数添加", "Python"]
    },

    {
        "id": "class_method_update",
        "description": "类方法更新",
        "edit_type": "修改",
        "complexity": "中等",
        "scope": "函数",
        "language": "python",
        "original_code": """class UserManager:
    def __init__(self):
        self.users = []

    def add_user(self, name):
        self.users.append(name)

    def get_user_count(self):
        return len(self.users)""",
        "edit_request": "修改add_user方法，添加邮箱验证",
        "cline_instruction": """------- SEARCH
    def add_user(self, name):
        self.users.append(name)
=======
    def add_user(self, name, email):
        if '@' not in email:
            raise ValueError("Invalid email address")
        user = {"name": name, "email": email}
        self.users.append(user)
+++++++ REPLACE""",
        "expected_result": """class UserManager:
    def __init__(self):
        self.users = []

    def add_user(self, name, email):
        if '@' not in email:
            raise ValueError("Invalid email address")
        user = {"name": name, "email": email}
        self.users.append(user)

    def get_user_count(self):
        return len(self.users)""",
        "tags": ["类方法", "参数添加", "验证逻辑", "Python"]
    },

    {
        "id": "import_statement",
        "description": "导入语句修改",
        "edit_type": "修改",
        "complexity": "简单",
        "scope": "单行",
        "language": "python",
        "original_code": """import os
import sys
from datetime import datetime

def main():
    print("Hello World")""",
        "edit_request": "添加json模块的导入",
        "cline_instruction": """------- SEARCH
import os
import sys
from datetime import datetime
=======
import os
import sys
import json
from datetime import datetime
+++++++ REPLACE""",
        "expected_result": """import os
import sys
import json
from datetime import datetime

def main():
    print("Hello World")""",
        "tags": ["导入语句", "Python"]
    },

    {
        "id": "error_handling",
        "description": "添加错误处理",
        "edit_type": "修改",
        "complexity": "中等",
        "scope": "函数",
        "language": "python",
        "original_code": """def read_config(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data""",
        "edit_request": "添加文件不存在的错误处理",
        "cline_instruction": """------- SEARCH
def read_config(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data
=======
def read_config(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Config file {filename} not found")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in {filename}")
        return {}
+++++++ REPLACE""",
        "expected_result": """def read_config(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Config file {filename} not found")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in {filename}")
        return {}""",
        "tags": ["错误处理", "异常捕获", "Python"]
    },

    {
        "id": "javascript_function",
        "description": "JavaScript函数修改",
        "edit_type": "修改",
        "complexity": "简单",
        "scope": "函数",
        "language": "javascript",
        "original_code": """function calculateTotal(items) {
    let total = 0;
    for (let item of items) {
        total += item.price;
    }
    return total;
}""",
        "edit_request": "添加税费计算",
        "cline_instruction": """------- SEARCH
function calculateTotal(items) {
    let total = 0;
    for (let item of items) {
        total += item.price;
    }
    return total;
}
=======
function calculateTotal(items, taxRate = 0.1) {
    let total = 0;
    for (let item of items) {
        total += item.price;
    }
    return total * (1 + taxRate);
}
+++++++ REPLACE""",
        "expected_result": """function calculateTotal(items, taxRate = 0.1) {
    let total = 0;
    for (let item of items) {
        total += item.price;
    }
    return total * (1 + taxRate);
}""",
        "tags": ["JavaScript", "函数修改", "参数添加"]
    }
]


def get_examples_by_criteria(edit_type: str = None, complexity: str = None,
                           language: str = None, scope: str = None) -> List[Dict[str, Any]]:
    """
    根据条件筛选示例

    Args:
        edit_type: 编辑类型
        complexity: 复杂度
        language: 编程语言
        scope: 影响范围

    Returns:
        List[Dict]: 匹配的示例列表
    """
    filtered_examples = CLINE_EXAMPLES

    if edit_type:
        filtered_examples = [ex for ex in filtered_examples if ex["edit_type"] == edit_type]

    if complexity:
        filtered_examples = [ex for ex in filtered_examples if ex["complexity"] == complexity]

    if language:
        filtered_examples = [ex for ex in filtered_examples if ex["language"] == language]

    if scope:
        filtered_examples = [ex for ex in filtered_examples if ex["scope"] == scope]

    return filtered_examples


def get_example_by_id(example_id: str) -> Dict[str, Any]:
    """
    根据ID获取特定示例

    Args:
        example_id: 示例ID

    Returns:
        Dict: 示例数据，如果未找到返回None
    """
    for example in CLINE_EXAMPLES:
        if example["id"] == example_id:
            return example
    return None


def get_relevant_examples(analysis_result: Dict[str, Any], max_examples: int = 3) -> List[Dict[str, Any]]:
    """
    根据分析结果获取最相关的示例

    Args:
        analysis_result: 编辑分析结果
        max_examples: 最大返回示例数

    Returns:
        List[Dict]: 相关示例列表
    """
    edit_type = analysis_result.get("edit_type")
    complexity = analysis_result.get("complexity")

    # 优先匹配编辑类型和复杂度
    examples = get_examples_by_criteria(edit_type=edit_type, complexity=complexity)

    # 如果示例不足，放宽条件
    if len(examples) < max_examples:
        examples.extend(get_examples_by_criteria(edit_type=edit_type))

    # 去重并限制数量
    seen_ids = set()
    unique_examples = []
    for ex in examples:
        if ex["id"] not in seen_ids:
            unique_examples.append(ex)
            seen_ids.add(ex["id"])
            if len(unique_examples) >= max_examples:
                break

    return unique_examples
