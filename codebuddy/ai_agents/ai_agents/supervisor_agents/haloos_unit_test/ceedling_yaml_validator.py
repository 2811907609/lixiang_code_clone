# This Python file uses the following encoding: utf-8
# ##############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ##############################################################################

import yaml
import os
from typing import Dict, List, Any, Tuple


class CeedlingYamlValidator:
    """验证 Ceedling project.yml 文件修改的合法性"""

    def __init__(self, initial_yaml_path: str):
        """
        初始化验证器

        Args:
            initial_yaml_path: 初始 YAML 文件的路径
        """
        self.initial_yaml_path = initial_yaml_path
        self.initial_data = self._load_yaml(initial_yaml_path)
        self.allowed_modify_path = [':flags', ':test', ':compile']  # 允许修改的路径

    def _load_yaml(self, file_path: str) -> Dict:
        """加载 YAML 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"无法加载 YAML 文件 {file_path}: {e}")

    def _get_nested_value(self, data: Dict, path: List[str]) -> Any:
        """获取嵌套字典中的值"""
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _set_nested_value(self, data: Dict, path: List[str], value: Any) -> None:
        """设置嵌套字典中的值"""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _compare_nested_dict(self, initial: Any, modified: Any, current_path: List[str] = None) -> List[str]:
        """
        递归比较两个嵌套字典的差异

        Args:
            initial: 初始数据
            modified: 修改后的数据
            current_path: 当前路径

        Returns:
            违规修改的路径列表
        """
        if current_path is None:
            current_path = []

        violations = []

        # 如果当前路径是 :flags -> :test -> :compile，需要特殊处理
        if self._is_compile_flags_path(current_path):
            return self._validate_compile_flags_changes(initial, modified, current_path)

        # 检查类型是否一致
        if type(initial) is not type(modified):
            violations.append(f"路径 {' -> '.join(current_path) if current_path else '根路径'} 类型发生变化: {type(initial).__name__} -> {type(modified).__name__}")
            return violations

        if isinstance(initial, dict):
            # 检查删除的键
            for key in initial:
                if key not in modified:
                    key_path = current_path + [str(key)]
                    if not self._is_in_allowed_edit_path(key_path):
                        violations.append(f"路径 {' -> '.join(key_path)} 被删除：原来 {initial[key]}，现在 无")

            # 检查新增的键
            for key in modified:
                if key not in initial:
                    key_path = current_path + [str(key)]
                    if not self._is_in_allowed_edit_path(key_path):
                        violations.append(f"路径 {' -> '.join(key_path)} 被新增：原来 无，现在 {modified[key]}")

            # 递归检查共同的键
            for key in set(initial.keys()) & set(modified.keys()):
                violations.extend(
                    self._compare_nested_dict(
                        initial[key],
                        modified[key],
                        current_path + [str(key)]
                    )
                )

        elif isinstance(initial, list):
            if initial != modified:
                path_str = ' -> '.join(current_path) if current_path else '根路径'
                if not self._is_in_allowed_edit_path(current_path):
                    violations.append(f"路径 {path_str} 列表内容发生变化：原来 {initial}，现在 {modified}")

        else:
            # 基本类型比较
            if initial != modified:
                path_str = ' -> '.join(current_path) if current_path else '根路径'
                if not self._is_in_allowed_edit_path(current_path):
                    violations.append(f"路径 {path_str} 值发生变化：原来 {initial}，现在 {modified}")

        return violations

    def _is_compile_flags_path(self, path: List[str]) -> bool:
        """
        检查当前路径是否为编译标志路径

        编译标志路径: :flags -> :test -> :compile
        """
        return (len(path) >= 3 and
                path[0] == ':flags' and
                path[1] == ':test' and
                path[2] == ':compile')

    def _is_in_allowed_edit_path(self, path: List[str]) -> bool:
        """
        检查当前路径是否在允许编辑的路径内

        允许编辑的路径: :flags -> :test -> :compile 及其子路径
        """
        if len(path) < 3:
            return False

        # 检查是否在 :flags -> :test -> :compile 路径下
        if not (path[0] == ':flags' and path[1] == ':test' and path[2] == ':compile'):
            return False

        # 如果恰好是 :flags -> :test -> :compile 路径，允许
        if len(path) == 3:
            return True

        # 如果是子路径（第4个元素开始），允许以test开头的字段或特殊字段:*
        if len(path) >= 4:
            key_str = str(path[3])
            clean_key = key_str.lstrip(':')
            # 允许test开头的字段或者 :* 通配符
            return clean_key.startswith('test') or key_str == ':*'

        return False

    def _paths_equal(self, obj1: Any, obj2: Any) -> bool:
        """深度比较两个对象是否相等"""
        if type(obj1) is not type(obj2):
            return False

        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._paths_equal(obj1[k], obj2[k]) for k in obj1.keys())

        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._paths_equal(a, b) for a, b in zip(obj1, obj2))

        else:
            return obj1 == obj2

    def _validate_compile_flags_changes(self, initial: Any, modified: Any, current_path: List[str]) -> List[str]:
        """
        验证编译标志的修改是否合法
        只允许修改以 'test' 开头的字段
        """
        violations = []

        if not isinstance(initial, dict) or not isinstance(modified, dict):
            if initial != modified:
                violations.append(f"路径 {' -> '.join(current_path)} 类型必须为字典")
            return violations

        # 检查删除的键
        for key in initial:
            if key not in modified:
                key_str = str(key)
                clean_key = key_str.lstrip(':')
                # 允许test开头的字段或者 :* 通配符
                if not (clean_key.startswith('test') or key_str == ':*'):
                    violations.append(f"路径 {' -> '.join(current_path + [str(key)])} 不允许删除非test开头的字段：原来 {initial[key]}，现在 无")

        # 检查新增的键
        for key in modified:
            if key not in initial:
                key_str = str(key)
                clean_key = key_str.lstrip(':')
                # 允许test开头的字段或者 :* 通配符
                if not (clean_key.startswith('test') or key_str == ':*'):
                    violations.append(f"路径 {' -> '.join(current_path + [str(key)])} 不允许新增非test开头的字段：原来 无，现在 {modified[key]}")

        # 检查修改的键
        for key in set(initial.keys()) & set(modified.keys()):
            if initial[key] != modified[key]:
                key_str = str(key)
                clean_key = key_str.lstrip(':')
                # 允许test开头的字段或者 :* 通配符
                if not (clean_key.startswith('test') or key_str == ':*'):
                    violations.append(f"路径 {' -> '.join(current_path + [str(key)])} 不允许修改非test开头的字段：原来 {initial[key]}，现在 {modified[key]}")

        # 注意：以test开头的字段可以自由增删改，不产生违规
        return violations

    def validate_yaml_file(self, modified_yaml_path: str) -> Tuple[bool, List[str]]:
        """
        验证修改后的 YAML 文件是否合法

        Args:
            modified_yaml_path: 修改后的 YAML 文件路径

        Returns:
            (是否合法, 违规信息列表)
        """
        try:
            modified_data = self._load_yaml(modified_yaml_path)
            violations = self._compare_nested_dict(self.initial_data, modified_data)
            return len(violations) == 0, violations
        except Exception as e:
            return False, [f"文件加载错误: {e}"]

    def validate_yaml_dict(self, modified_data: Dict) -> Tuple[bool, List[str]]:
        """
        验证修改后的 YAML 数据字典是否合法

        Args:
            modified_data: 修改后的数据字典

        Returns:
            (是否合法, 违规信息列表)
        """
        try:
            violations = self._compare_nested_dict(self.initial_data, modified_data)

            if len(violations) == 0:
                return True, violations
            else:
                return False, violations
        except Exception as e:
            return False, [f"数据验证错误: {e}"]

    def get_compile_flags_dict(self) -> Dict:
        """获取当前编译标志字典"""
        compile_flags = self._get_nested_value(
            self.initial_data,
            [':flags', ':test', ':compile']
        )
        return compile_flags if compile_flags else {}

    def valid_ceedling_yaml(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        验证 Ceedling YAML 文件的合法性

        Args:
            file_path: YAML 文件路径

        Returns:
            (是否合法, 错误信息列表)

        注意:
            1. 文件读取错误时，返回错误结果
            2. 内容错误检测时，返回错误结果
        """
        errors = []

        # 1. 文件读取错误处理
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_msg = f"文件不存在: {file_path}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
                return False, errors

            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                error_msg = f"文件无读取权限: {file_path}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
                return False, errors

            # 尝试打开并读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查文件是否为空
            if not content.strip():
                error_msg = f"文件内容为空: {file_path}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
                return False, errors

        except FileNotFoundError:
            error_msg = f"文件未找到: {file_path}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
        except PermissionError:
            error_msg = f"文件访问权限不足: {file_path}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
        except UnicodeDecodeError as e:
            error_msg = f"文件编码错误: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
        except IOError as e:
            error_msg = f"文件读取IO错误: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
        except Exception as e:
            error_msg = f"文件读取未知错误: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors

        # 2. YAML内容解析错误处理
        try:
            legal_data = yaml.safe_load(content)

            # 检查YAML解析结果
            if legal_data is None:
                error_msg = f"YAML文件解析结果为空: {file_path}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
                return False, errors

            # 检查是否为字典类型（Ceedling配置应该是字典）
            if not isinstance(legal_data, dict):
                error_msg = f"YAML文件格式错误，应为字典格式: {file_path}, 实际类型: {type(legal_data).__name__}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
                return False, errors

        except yaml.YAMLError as e:
            error_msg = f"YAML语法错误: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
        except Exception as e:
            error_msg = f"YAML解析未知错误: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors

        # 3. 内容合法性验证
        try:
            is_valid, violations = self.validate_yaml_dict(legal_data)

            print(f"合法性: {is_valid}")
            if violations:
                for violation in violations:
                    if violation and violation.strip():  # 只输出非空的违规项
                        errors.append(f"配置文件被修改，除了:flags:下:compile:下添加测试文件的条件编译宏，其他字段不要修改：{violation}")
                print(errors)
                return False, errors
            else:
                return True, []

        except Exception as e:
            error_msg = f"内容验证过程出错: {file_path}, 详情: {e}"
            errors.append(error_msg)
            print(f"错误: {error_msg}")
            return False, errors
