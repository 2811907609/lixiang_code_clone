from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


# Define a custom representer for multi-line strings
def _yaml_str_presenter(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def yaml_load_dir(dir_path, file_pattern='*.yaml', recursive=False):
    """
    从目录中加载多个 YAML 文件

    Args:
        dir_path: 目录路径
        file_pattern: 文件匹配模式，默认为 '*.yaml'
        recursive: 是否递归搜索子目录，默认为 False

    Returns:
        字典，其中键是文件名（不包括扩展名），值是加载的 YAML 内容
    """
    yaml = YAML(typ='safe')
    yaml.allow_unicode = True

    dir_path = Path(dir_path)
    result = []

    # 确定搜索模式
    if recursive:
        glob_pattern = f"**/{file_pattern}"
    else:
        glob_pattern = file_pattern

    # 搜索并加载文件
    for yaml_file in dir_path.glob(glob_pattern):
        if yaml_file.is_file():
            # 加载 YAML 内容
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = yaml.load(f)
                result.append(content)

    return result


def yaml_dump(obj, file_handler=None, pretty_print=True, **kwargs):
    # Create a YAML instance
    yaml = YAML()
    yaml.allow_unicode = True  # Avoid unicode escape sequences like \uFF5C

    # Disable flow style (use block style instead)
    yaml.default_flow_style = False

    if pretty_print:
        # Add the custom string representer to handle multi-line strings
        yaml.representer.add_representer(str, _yaml_str_presenter)

    if file_handler is None:
        # If no file handler is provided, dump to a string
        stream = StringIO()
        yaml.dump(obj, stream, **kwargs)
        return stream.getvalue()
    else:
        # Dump to the provided file handler
        yaml.dump(obj, file_handler, **kwargs)


def yaml_print(obj):
    print(yaml_dump(obj))
