"""
Codex格式的示例库

包含各种场景下的Codex结构化补丁示例，用于指导AI生成正确的编辑指令。
"""

from typing import List, Dict, Any

# Codex示例数据结构
CODEX_EXAMPLES = [
    {
        "id": "class_method_refactor",
        "description": "类方法重构",
        "edit_type": "重构",
        "complexity": "复杂",
        "scope": "类",
        "language": "python",
        "original_code": """class UserService:
    def __init__(self):
        self.users = []

    def create_user(self, name, email):
        user = {"name": name, "email": email, "id": len(self.users)}
        self.users.append(user)
        return user

    def get_user(self, user_id):
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None""",
        "edit_request": "重构create_user方法，添加邮箱验证和重复检查",
        "codex_instruction": """*** Begin Patch
*** Update File: user_service.py
@@ class UserService:
@@ def create_user(self, name, email):
- user = {"name": name, "email": email, "id": len(self.users)}
- self.users.append(user)
- return user
+ # 验证邮箱格式
+ if not self._is_valid_email(email):
+     raise ValueError("Invalid email format")
+
+ # 检查邮箱是否已存在
+ if self._email_exists(email):
+     raise ValueError("Email already exists")
+
+ user = {
+     "name": name.strip(),
+     "email": email.lower(),
+     "id": len(self.users),
+     "created_at": datetime.now()
+ }
+ self.users.append(user)
+ return user
*** End Patch""",
        "expected_result": """class UserService:
    def __init__(self):
        self.users = []

    def create_user(self, name, email):
        # 验证邮箱格式
        if not self._is_valid_email(email):
            raise ValueError("Invalid email format")

        # 检查邮箱是否已存在
        if self._email_exists(email):
            raise ValueError("Email already exists")

        user = {
            "name": name.strip(),
            "email": email.lower(),
            "id": len(self.users),
            "created_at": datetime.now()
        }
        self.users.append(user)
        return user

    def get_user(self, user_id):
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None""",
        "tags": ["类重构", "方法增强", "验证逻辑", "Python"]
    },

    {
        "id": "function_signature_change",
        "description": "函数签名复杂修改",
        "edit_type": "重构",
        "complexity": "中等",
        "scope": "函数",
        "language": "python",
        "original_code": """def process_payment(amount, currency, card_number):
    if currency not in ["USD", "EUR", "GBP"]:
        raise ValueError("Unsupported currency")

    # 简单的卡号验证
    if len(card_number) != 16:
        raise ValueError("Invalid card number")

    # 处理支付
    result = payment_gateway.charge(amount, currency, card_number)
    return result""",
        "edit_request": "修改函数接受payment_info对象而不是单独的参数",
        "codex_instruction": """*** Begin Patch
*** Update File: payment.py
@@ def process_payment(amount, currency, card_number):
- def process_payment(amount, currency, card_number):
+ def process_payment(payment_info):
+     amount = payment_info.amount
+     currency = payment_info.currency
+     card_number = payment_info.card_number
+
     if currency not in ["USD", "EUR", "GBP"]:
         raise ValueError("Unsupported currency")
*** End Patch""",
        "expected_result": """def process_payment(payment_info):
    amount = payment_info.amount
    currency = payment_info.currency
    card_number = payment_info.card_number

    if currency not in ["USD", "EUR", "GBP"]:
        raise ValueError("Unsupported currency")

    # 简单的卡号验证
    if len(card_number) != 16:
        raise ValueError("Invalid card number")

    # 处理支付
    result = payment_gateway.charge(amount, currency, card_number)
    return result""",
        "tags": ["函数重构", "参数重构", "Python"]
    },

    {
        "id": "error_handling_enhancement",
        "description": "错误处理增强",
        "edit_type": "修改",
        "complexity": "中等",
        "scope": "函数",
        "language": "python",
        "original_code": """def load_config(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 验证必需的配置项
    required_keys = ['database_url', 'api_key', 'debug']
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required config: {key}")

    return config""",
        "edit_request": "增强错误处理，添加日志记录和默认值",
        "codex_instruction": """*** Begin Patch
*** Update File: config.py
@@ def load_config(config_path):
- with open(config_path, 'r') as f:
-     config = json.load(f)
+ try:
+     with open(config_path, 'r') as f:
+         config = json.load(f)
+ except FileNotFoundError:
+     logger.error(f"Config file not found: {config_path}")
+     raise ConfigError(f"Configuration file {config_path} not found")
+ except json.JSONDecodeError as e:
+     logger.error(f"Invalid JSON in config file: {e}")
+     raise ConfigError(f"Invalid JSON in configuration file: {e}")

     # 验证必需的配置项
     required_keys = ['database_url', 'api_key', 'debug']
+     defaults = {'debug': False, 'timeout': 30}
+
     for key in required_keys:
         if key not in config:
-             raise KeyError(f"Missing required config: {key}")
+             if key in defaults:
+                 config[key] = defaults[key]
+                 logger.warning(f"Using default value for {key}: {defaults[key]}")
+             else:
+                 logger.error(f"Missing required config: {key}")
+                 raise ConfigError(f"Missing required configuration: {key}")
*** End Patch""",
        "expected_result": """def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise ConfigError(f"Configuration file {config_path} not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise ConfigError(f"Invalid JSON in configuration file: {e}")

    # 验证必需的配置项
    required_keys = ['database_url', 'api_key', 'debug']
    defaults = {'debug': False, 'timeout': 30}

    for key in required_keys:
        if key not in config:
            if key in defaults:
                config[key] = defaults[key]
                logger.warning(f"Using default value for {key}: {defaults[key]}")
            else:
                logger.error(f"Missing required config: {key}")
                raise ConfigError(f"Missing required configuration: {key}")

    return config""",
        "tags": ["错误处理", "日志记录", "默认值", "Python"]
    },

    {
        "id": "javascript_class_refactor",
        "description": "JavaScript类重构",
        "edit_type": "重构",
        "complexity": "复杂",
        "scope": "类",
        "language": "javascript",
        "original_code": """class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`);
        return response.json();
    }

    async post(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    }
}""",
        "edit_request": "重构为支持请求拦截器和错误处理",
        "codex_instruction": """*** Begin Patch
*** Update File: api_client.js
@@ class ApiClient {
@@ constructor(baseUrl) {
- constructor(baseUrl) {
+ constructor(baseUrl, options = {}) {
     this.baseUrl = baseUrl;
+     this.timeout = options.timeout || 5000;
+     this.interceptors = {
+         request: [],
+         response: []
+     };
 }

@@ async get(endpoint) {
- async get(endpoint) {
-     const response = await fetch(`${this.baseUrl}${endpoint}`);
-     return response.json();
- }
+ async get(endpoint, options = {}) {
+     return this._request('GET', endpoint, null, options);
+ }

@@ async post(endpoint, data) {
- async post(endpoint, data) {
-     const response = await fetch(`${this.baseUrl}${endpoint}`, {
-         method: 'POST',
-         body: JSON.stringify(data)
-     });
-     return response.json();
- }
+ async post(endpoint, data, options = {}) {
+     return this._request('POST', endpoint, data, options);
+ }
+
+ async _request(method, endpoint, data, options) {
+     let config = {
+         method,
+         headers: {
+             'Content-Type': 'application/json',
+             ...options.headers
+         },
+         signal: AbortSignal.timeout(this.timeout)
+     };
+
+     if (data) {
+         config.body = JSON.stringify(data);
+     }
+
+     // 应用请求拦截器
+     for (const interceptor of this.interceptors.request) {
+         config = await interceptor(config);
+     }
+
+     try {
+         const response = await fetch(`${this.baseUrl}${endpoint}`, config);
+
+         if (!response.ok) {
+             throw new Error(`HTTP ${response.status}: ${response.statusText}`);
+         }
+
+         let result = await response.json();
+
+         // 应用响应拦截器
+         for (const interceptor of this.interceptors.response) {
+             result = await interceptor(result, response);
+         }
+
+         return result;
+     } catch (error) {
+         if (error.name === 'AbortError') {
+             throw new Error('Request timeout');
+         }
+         throw error;
+     }
+ }
*** End Patch""",
        "expected_result": """class ApiClient {
    constructor(baseUrl, options = {}) {
        this.baseUrl = baseUrl;
        this.timeout = options.timeout || 5000;
        this.interceptors = {
            request: [],
            response: []
        };
    }

    async get(endpoint, options = {}) {
        return this._request('GET', endpoint, null, options);
    }

    async post(endpoint, data, options = {}) {
        return this._request('POST', endpoint, data, options);
    }

    async _request(method, endpoint, data, options) {
        let config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            signal: AbortSignal.timeout(this.timeout)
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        // 应用请求拦截器
        for (const interceptor of this.interceptors.request) {
            config = await interceptor(config);
        }

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, config);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            let result = await response.json();

            // 应用响应拦截器
            for (const interceptor of this.interceptors.response) {
                result = await interceptor(result, response);
            }

            return result;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }
}""",
        "tags": ["JavaScript", "类重构", "拦截器", "错误处理"]
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
    filtered_examples = CODEX_EXAMPLES

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
    for example in CODEX_EXAMPLES:
        if example["id"] == example_id:
            return example
    return None


def get_relevant_examples(analysis_result: Dict[str, Any], max_examples: int = 2) -> List[Dict[str, Any]]:
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
