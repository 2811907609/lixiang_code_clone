import os
import yaml


def load_prompt(prompt_name, **params):
    dirname = os.path.dirname(__file__)
    path = os.path.join(dirname, f"{prompt_name}.yaml")
    with open(path, "r", encoding="utf-8") as file:
        prompt_data = yaml.safe_load(file)

    # 合并参数和需要原样显示的内容
    all_params = dict(params)
    return prompt_data["content"].format(**all_params)
