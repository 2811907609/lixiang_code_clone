import os
from dataclasses import dataclass, field


@dataclass
class Config:
    REPO_LANG_CONFIG_FILE: str = field(init=False)

    def __post_init__(self):
        '''use post init so that we can update it at runtime using os.environ[x]=y'''
        self.REPO_LANG_CONFIG_FILE = os.environ.get('REPO_LANG_CONFIG_FILE', '')


env_config = Config()
