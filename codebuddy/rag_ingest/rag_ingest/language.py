import fnmatch
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

import yaml
from sysutils.xtypes import dataclass_from_dict

logger = logging.getLogger(__name__)


@dataclass
class LangConfig:
    file_exts: Optional[list] = None
    ignore_glob_patterns: Optional[list] = None

    def _valid_ext(self, filepath: str):
        for ext in self.file_exts:
            if filepath.endswith(ext):
                return True
        return False

    def should_ignore(self, filepath: str):
        if not self._valid_ext(filepath):
            return True
        for pattern in self.ignore_glob_patterns:
            if fnmatch.fnmatch(filepath, pattern):
                return True
        return False


_language_configs: Dict[str, LangConfig] = {}


def _load_config():
    if _language_configs:
        return _language_configs
    config_file = os.path.join(os.path.dirname(__file__), 'language.yaml')
    with open(config_file, 'r') as f:
        configs: dict = yaml.load(f.read(), Loader=yaml.Loader)
        lang_configs: dict = configs.get('languages', {})
        for k, v in lang_configs.items():
            _language_configs[k] = dataclass_from_dict(LangConfig, v)


def get_language_config(language: str) -> Optional[LangConfig]:
    _load_config()
    c = _language_configs.get(language)
    if not c:
        raise Exception(f'no config for language {language}')
    return c


_ext_lang_map: dict[str, str] = {
    '.go': 'go',
    '.py': 'python',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.rs': 'rust',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.kt': 'kotlin',
    '.lua': 'lua',
    '.vue': 'vue',
}


def get_language_config_by_file(file: str) -> Optional[LangConfig]:
    _, ext = os.path.splitext(file)
    if ext in _ext_lang_map:
        return get_language_config(_ext_lang_map[ext])
    logger.info(f'file {file} has no language config')
    return None
