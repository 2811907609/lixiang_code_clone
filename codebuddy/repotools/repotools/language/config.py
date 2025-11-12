import os
from dataclasses import dataclass
from typing import Dict, Optional

import toml
from sysutils.xtypes import dataclass_from_dict

from repotools.envs import env_config


@dataclass
class Tokenizer:
    with_common_ignore_keywords: bool = True
    ignore_keywords: Optional[list[str]] = None


@dataclass
class ParseNameEntities:
    query: Optional[str] = None


@dataclass
class ParseIncludes:
    query: Optional[str] = None
    trim_prefixes: Optional[list[str]] = None
    trim_suffixes: Optional[list[str]] = None


@dataclass
class OutlineChunkFormatter:
    type_name: Optional[str] = None
    fmt: Optional[str] = None


@dataclass
class ParseOutlines:
    query: Optional[str] = None
    formatter: Optional[Dict[str, OutlineChunkFormatter]] = None


@dataclass
class OutlineChunk:
    type: str = ''
    sig_name: str = ''
    text: str = ''


@dataclass
class CurrentSnippet:
    '''当前代码块提取相关的配置'''
    node_kinds: Optional[list[str]] = None


@dataclass
class LangConfig:
    name: Optional[str] = None
    file_extensions: Optional[list[str]] = None
    tokenizer: Optional[Tokenizer] = None
    parse_name_entities: Optional[ParseNameEntities] = None
    parse_includes: Optional[ParseIncludes] = None
    current_snippet: Optional[CurrentSnippet] = None
    parse_outlines: Optional[ParseOutlines] = None


_language_configs: Dict[str, LangConfig] = {}
_common_config: LangConfig


def _load_config():
    if _language_configs:
        return _language_configs
    config_file = os.path.join(os.path.dirname(__file__), 'config.toml')
    if env_config.REPO_LANG_CONFIG_FILE:
        config_file = env_config.REPO_LANG_CONFIG_FILE
    with open(config_file, 'r') as f:
        configs: dict = toml.load(f)
        lang_configs: dict = configs.get('languages', {})
        for k, v in lang_configs.items():
            _language_configs[k] = dataclass_from_dict(LangConfig, v)
        global _common_config
        _common_config = _language_configs['common']


def get_lang_config(lang: str) -> Optional[LangConfig]:
    _load_config()
    return _language_configs.get(lang)
