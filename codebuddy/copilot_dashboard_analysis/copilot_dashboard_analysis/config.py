import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote_plus

from sysutils.xenv import load_env_file


@dataclass
class Config:
    OPENAI_ENDPOINT: str = field(init=False)
    OPENAI_KEY: str = field(init=False)

    STARROCKS_HOST: str = field(init=False)
    STARROCKS_PORT: int = field(init=False)
    STARROCKS_USER: str = field(init=False)
    STARROCKS_PASSWORD: str = field(init=False)
    STARROCKS_DATABASE: str = field(init=False)

    CLICKHOUSE_HOST: str = field(init=False)
    CLICKHOUSE_PORT: str = field(init=False)
    CLICKHOUSE_USER: str = field(init=False)
    CLICKHOUSE_PASSWORD: str = field(init=False)

    def __post_init__(self):
        self.OPENAI_ENDPOINT = os.environ.get('OPENAI_ENDPOINT', '')
        self.OPENAI_KEY = os.environ.get('OPENAI_KEY', '')

        self.STARROCKS_HOST = os.environ.get('STARROCKS_HOST', '')
        self.STARROCKS_PORT = int(os.environ.get('STARROCKS_PORT'))
        self.STARROCKS_USER = os.environ.get('STARROCKS_USER', '')
        self.STARROCKS_PASSWORD = os.environ.get('STARROCKS_PASSWORD', '')
        self.STARROCKS_DATABASE = os.environ.get('STARROCKS_DATABASE', '')

        self.CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', '')
        self.CLICKHOUSE_PORT = os.environ.get('CLICKHOUSE_PORT', '')
        self.CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', '')
        self.CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')

    @property
    def starrocks_uri(self):
        password = quote_plus(self.STARROCKS_PASSWORD)
        return f'mysql+mysqlconnector://{self.STARROCKS_USER}:{password}@{self.STARROCKS_HOST}:{self.STARROCKS_PORT}'

    # @property
    # def clickhouse_uri(self):
    #     password = quote_plus(self.CLICKHOUSE_PASSWORD)
    #     return f'clickhouse+native://{self.CLICKHOUSE_USER}:{password}@{self.CLICKHOUSE_HOST}:{self.CLICKHOUSE_PORT}'


def init_config_from_env(env_filename: str):
    relative_dirs = ['.', '..']
    for relative_dir in relative_dirs:
        current_dir = Path(__file__).parent
        env_file_path = current_dir / relative_dir / env_filename
        if env_file_path.exists():
            load_env_file(env_file_path)
            return
    raise Exception('failed to load env file')
