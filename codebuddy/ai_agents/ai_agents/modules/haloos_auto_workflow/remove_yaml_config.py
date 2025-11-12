#!/usr/bin/env python3
"""
删除项目配置文件中指定测试用例的条件编译配置的工具脚本。
"""

import yaml
import os

def remove_conditional_config_in_yaml_file(file_path: str, test_name: str, is_back_up = False) -> bool:
    """
    从project.yml文件中删除指定测试配置的条件编译设置。

    Args:
        file_path (str): project.yml文件的路径
        test_name (str): 要删除的测试配置名称，如 'test_Os_NextScheduleTable_extended_status'

    Returns:
        bool: 如果成功删除返回True，否则返回False
    """

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return False

    try:
        # 读取YAML文件
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 检查配置结构
        if not config or ':flags' not in config:
            print("错误: 无效的配置文件结构，未找到 ':flags' 节点")
            return False

        if ':test' not in config[':flags']:
            print("错误: 无效的配置文件结构，未找到 'flags:test' 节点")
            return False

        if ':compile' not in config[':flags'][':test']:
            print("错误: 无效的配置文件结构，未找到 'flags:test:compile' 节点")
            return False

        compile_config = config[':flags'][':test'][':compile']

        if not test_name.startswith(':'):
            test_name = ':' + test_name

        # 检查是否存在指定的测试配置
        if test_name not in compile_config:
            print(f"警告: 测试配置 '{test_name}' 不存在")
            return False


        # 删除指定的测试配置
        del compile_config[test_name]
        print(f"成功删除测试配置: {test_name}")

        # 备份原文件
        if is_back_up:
            backup_path = file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                with open(file_path, 'r', encoding='utf-8') as original:
                    f.write(original.read())
            print(f"原文件已备份到: {backup_path}")

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"配置文件已更新: {file_path}")
        return True

    except yaml.YAMLError as e:
        print(f"YAML解析错误: {e}")
        return False
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        return False

def remove_conditional_config_by_name(file_path: str, test_name: str) -> bool:
    """
    便捷函数：删除指定测试配置的条件编译设置。

    Args:
        file_path (str): project.yml文件的路径
        test_name (str): 要删除的测试配置名称
        preserve_format (bool): 是否保持原有文件格式，默认为True

    Returns:
        bool: 如果成功删除返回True，否则返回False
    """
    return remove_conditional_config_in_yaml_file(file_path, test_name)
