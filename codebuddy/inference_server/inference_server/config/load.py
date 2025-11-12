import json
import os
import re

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

from inference_server.const import lpai_endpoint


def extract_end_number(s):
    if not s:
        return None
    # Use a regular expression to search for digits at the end of the string
    match = re.search(r'(\d+)$', s)
    if match:
        return match.group(1)
    return None


@dataclass
class InstanceConfig:
    name: str
    model_type: str = ''
    model_path: str = ''
    disable_register: bool = False
    register_clusters: List[str] = field(default_factory=list)
    lpai_endpoint: str = ''
    model_labels: Dict[str, str] = field(default_factory=dict)
    embeddings: bool = False
    multiple_instances: List[str] = field(default_factory=list)
    model_params: Dict[str, Any] = field(default_factory=dict)
    _other_attrs: dict = field(default_factory=dict, repr=False)
    subinstances: 'Dict[InstanceConfig]' = field(default_factory=dict)

    _ft_model_info: dict = None

    @property
    def is_multi_instance(self):
        return bool(self.multiple_instances)

    @property
    def ft_model_info(self):
        '''fine tune model info, path and date'''
        if self._ft_model_info is None:
            real_model_path = os.path.realpath(self.model_path)
            model_date = extract_end_number(real_model_path)
            self._ft_model_info = {
                'model_path': real_model_path,
                'model_date': model_date,
            }
        return self._ft_model_info

    def get_model_params(self, model_name: str):
        return self.get('models', {}).get(model_name, {})

    def get(self, key, default=None):
        return self._other_attrs.get(key, default)

    def __getattr__(self, item):
        # Attempt to return the value from the internal dictionary if the attribute isn't found
        if item in self._other_attrs:
            return self._other_attrs[item]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{item}'")

    @staticmethod
    def from_dict(name: str, c: dict) -> 'InstanceConfig':
        instance_config = (c or {}).copy()
        ins = InstanceConfig(
            name=name,
            model_type=instance_config.get('model_type'),
            model_path=instance_config.get('model_path'),
            model_labels=instance_config.get('model_labels', {}),
            register_clusters=instance_config.get('register_clusters', []),
            lpai_endpoint=instance_config.get('lpai_endpoint', lpai_endpoint),
            embeddings=instance_config.get('embeddings'),
            multiple_instances=instance_config.get('multiple_instances'),
            model_params=instance_config.get('model_params', {}),
            _other_attrs=instance_config)
        return ins


class Config:

    def __init__(self, config_path=None) -> None:
        if not config_path:
            this_dir = Path(__file__).parent
            config_path = this_dir / '../../' / 'conf/config.json'

        with open(config_path, 'r') as f:
            self._config = json.load(f)

    @property
    def config(self):
        return self._config

    def _load_instance(self, instance) -> InstanceConfig:
        instance_config = self._config.get('instances', {}).get(instance, {})
        return InstanceConfig.from_dict(instance, instance_config)

    def load_instance(self, instance) -> InstanceConfig:
        ins = self._load_instance(instance)
        if not ins.is_multi_instance:
            return ins
        for i in ins.multiple_instances:
            ins.subinstances[i] = self._load_instance(i)
        return ins
