import logging
import json
import re
import os
from pathlib import Path
from typing import Optional,Dict, Any

def get_json_info_by_key_from_jsonpath(
    jsonpath: str,
    key_name: str,
    key_value: str,
    inner_key: str = "issues"
) -> Dict[str, Any]:
    """
    从JSON文件中根据键值对匹配条件提取特定信息。

    该函数读取JSON文件并在指定的嵌套数组（由inner_key指定）中搜索匹配指定键值对的项，
    返回包含搜索结果状态信息的字典结构。

    Args:
        jsonpath (str): 要读取的JSON文件路径（相对或绝对路径）
        key_name (str): 要匹配的键名
        key_value (str): 要搜索的键值
        inner_key (str, optional): JSON中包含要搜索数组的字段名。默认为"issues"

    Returns:
        Dict[str, Any]: 包含搜索结果的字典，结构如下：
            - bool_find_iter (bool): 是否找到匹配项
            - msg (str): 搜索结果描述信息
            - item (dict | None): 找到的匹配项字典，未找到时为None

    Raises:
        ValueError: 当参数无效、JSON格式错误或结构不符合预期时
        IOError: 当文件不存在或读取失败时
        KeyError: 当指定的键在JSON结构中不存在时
        Exception: 当处理过程中出现其他未预期错误时

    Examples:
        >>> result = get_json_info_by_key_from_jsonpath(
        ...     "/path/to/errors.json",
        ...     "mergeKey",
        ...     "7941d17d1872a3be8f16aac057efd62b",
        ...     "issues"
        ... )
        >>> # 成功找到时：
        >>> # {"bool_find_iter": True, "msg": "success find item by mergeKey=7941d17d...", "item": {...}}
        >>>
        >>> result = get_json_info_by_key_from_jsonpath(
        ...     "/path/to/data.json",
        ...     "id",
        ...     "nonexistent",
        ...     "records"
        ... )
        >>> # 未找到时：
        >>> # {"bool_find_iter": False, "msg": "No item found with id='nonexistent'...", "item": None}
    """
    # Validate inputs
    if not jsonpath or not jsonpath.strip():
        raise ValueError("jsonpath is required and cannot be empty")

    if not key_name or not key_name.strip():
        raise ValueError("key_name is required and cannot be empty")

    if not key_value or not key_value.strip():
        raise ValueError("key_value is required and cannot be empty")

    if not inner_key or not inner_key.strip():
        raise ValueError("inner_key is required and cannot be empty")

    # Check if file exists
    if not os.path.exists(jsonpath):
        raise IOError("JSON file '{}' does not exist".format(jsonpath))

    if not os.path.isfile(jsonpath):
        raise ValueError("Path '{}' is not a file".format(jsonpath))

    try:
        # Read and parse JSON file
        with open(jsonpath, 'r') as f:
            json_data = json.load(f)

        # Validate JSON structure
        if not isinstance(json_data, dict):
            raise ValueError("JSON file '{}' must contain a dictionary at root level".format(jsonpath))

        if inner_key not in json_data:
            raise KeyError("Key '{}' not found in JSON file '{}'".format(inner_key, jsonpath))

        inner_data = json_data[inner_key]
        if not isinstance(inner_data, list):
            raise ValueError("The value of '{}' must be a list/array".format(inner_key))

        # Search for matching item
        for item in inner_data:
            if not isinstance(item, dict):
                continue  # Skip non-dictionary items

            if key_name in item and str(item[key_name]) == str(key_value):
                # Found matching item
                print("Found matching item in {}: {}={}".format(jsonpath, key_name, key_value))
                # return item
                return {"bool_find_iter":True,"msg":f"success find item by {key_name}={key_value}","item":item}

        print_info="No item found with {}='{}' in '{}' array of '{}'".format(key_name, key_value, inner_key, jsonpath)
        # No matching item found
        # raise ValueError()
        return {"bool_find_iter":False,"msg":print_info,"item":None}

    except IOError as e:
        error_msg = "Failed to read JSON file '{}': {}".format(jsonpath, e)
        logging.error(error_msg)
        raise IOError(error_msg)

    except ValueError as e:
        error_msg = "Invalid JSON format in file '{}': {}".format(jsonpath, e)
        logging.error(error_msg)
        raise ValueError(error_msg)

    except Exception as e:
        error_msg = "Unexpected error when processing JSON file '{}': {}".format(jsonpath, e)
        logging.error(error_msg)
        raise Exception(error_msg)

def _extract_rule_number(checkerName: str) -> Optional[str]:
    """
    Extract rule number from MISRA checker name.

    Args:
        checkerName (str): Checker name like "MISRA C-2012 Rule 20.10"

    Returns:
        Optional[str]: Extracted rule number like "20.10" or None if not found
    """
    # Pattern to match various MISRA rule formats
    patterns = [
        r'Rule\s+(\d+\.\d+)',  # "Rule 20.10"
        r'rule\s+(\d+\.\d+)',  # "rule 20.10"
        r'(\d+\.\d+)',         # Just "20.10"
        r'Rule\s+(\d+)',       # "Rule 20"
        r'rule\s+(\d+)',       # "rule 20"
    ]

    for pattern in patterns:
        match = re.search(pattern, checkerName, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _find_matching_rule_key(rule_number: str, rule_keys: list) -> Optional[str]:
    """
    Find the best matching rule key from available keys.

    Args:
        rule_number (str): Rule number like "20.10"
        rule_keys (list): List of available rule keys like ["rule_20_10", "rule_1_1", ...]

    Returns:
        Optional[str]: Best matching key or None if not found
    """
    # Convert rule number to expected key format
    normalized_number = rule_number.replace('.', '_')
    expected_key = f"rule_{normalized_number}"

    # Direct match first
    if expected_key in rule_keys:
        return expected_key

    # Fuzzy matching - find keys that contain the rule number
    candidates = []
    for key in rule_keys:
        if normalized_number in key:
            candidates.append(key)

    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]

    # If multiple candidates, prefer exact format match
    for candidate in candidates:
        if candidate == expected_key:
            return candidate

    # Return first candidate if any
    if candidates:
        return candidates[0]

    return None

def match_misra_rule(checkerName: str, misra_rules_jsonpath: str) -> Dict[str, Any]:
    """
    Match a MISRA C checker name against rules in JSON file and return rule information.

    This function performs fuzzy matching to find the most appropriate MISRA rule
    based on the checker name provided, typically from static analysis tools like Coverity.

    Args:
        checkerName (str): MISRA C standard definition name (e.g., "MISRA C-2012 Rule 20.10")
        misra_rules_jsonpath (str): Path to JSON file containing MISRA rules data

    Returns:
        Dict[str, Any]: Dictionary containing the matched MISRA rule information.
                       Returns empty dict if no match found.

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        json.JSONDecodeError: If the JSON file is malformed
        ValueError: If inputs are invalid

    Examples:
        >>> info = match_misra_rule("MISRA C-2012 Rule 20.10", "/path/to/misra_rules.json")
        >>> print(info['category'])  # 'Required'
        >>> print(info['Rationale'])  # Rule rationale text
    """
    # Input validation
    if not checkerName or not checkerName.strip():
        raise ValueError("checkerName cannot be empty")

    if not misra_rules_jsonpath or not misra_rules_jsonpath.strip():
        raise ValueError("misra_rules_jsonpath cannot be empty")

    # Check if JSON file exists
    json_path = Path(misra_rules_jsonpath)
    if not json_path.exists():
        raise FileNotFoundError(f"MISRA rules JSON file not found: {misra_rules_jsonpath}")

    if not json_path.is_file():
        raise ValueError(f"Path is not a file: {misra_rules_jsonpath}")

    # Load JSON data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            misra_rules = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {misra_rules_jsonpath}: {e}")
    except Exception as e:
        raise OSError(f"Error reading file {misra_rules_jsonpath}: {e}")

    if not isinstance(misra_rules, dict):
        raise ValueError("JSON file must contain a dictionary at root level")

    # Extract rule number from checker name
    rule_number = _extract_rule_number(checkerName)
    if not rule_number:
        return {}

    # Find matching rule key
    matched_key = _find_matching_rule_key(rule_number, misra_rules.keys())
    if not matched_key:
        return {}

    # Return the matched rule information
    rule_info = misra_rules[matched_key].copy()
    rule_info['matched_key'] = matched_key
    rule_info['original_checker_name'] = checkerName

    return rule_info


def extract_info_from_common_jsonfile_by_key(filepath: str, key: str)->str:
    """
    从JSON文件中根据指定key提取对应的值。

    这个工具从JSON文件中读取数据，并返回指定key对应的值。
    如果key不存在，则抛出ValueError异常。

    Args:
        filepath: JSON文件的路径 (相对或绝对路径)
        key: 要提取的JSON对象中的key名称

    Returns:
        Any: 指定key对应的值，可以是任何JSON支持的数据类型

    Raises:
        ValueError: 如果指定的key在JSON文件中不存在
        FileNotFoundError: 如果文件不存在
        PermissionError: 如果没有足够权限读取文件
        json.JSONDecodeError: 如果文件不是有效的JSON格式
        UnicodeDecodeError: 如果文件无法用UTF-8编码解码

    Examples:
        >>> extract_info_from_common_jsonfile_by_key("config.json", "version")
        "1.0.0"
        >>> extract_info_from_common_jsonfile_by_key("data.json", "users")
        [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        >>> extract_info_from_common_jsonfile_by_key("settings.json", "database")
        {"host": "localhost", "port": 5432}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if key in data:
            return data[key]
    raise ValueError(f'key={key} 不存在于filepath={filepath}')
