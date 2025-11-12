import os
from dataclasses import dataclass, field
from urllib.parse import quote_plus


@dataclass
class Config:
    PORT: int = field(init=False)
    CONFIG_PATH: str = field(init=False)
    INSTANCE_NAME: str = field(init=False)
    LPAI_SERVICE_NAME: str = field(init=False)

    OPENAI_ENDPOINT: str = field(init=False)
    OPENAI_KEY: str = field(init=False)

    STARROCKS_HOST: str = field(init=False)
    STARROCKS_PORT: int = field(init=False)
    STARROCKS_USER: str = field(init=False)
    STARROCKS_PASSWORD: str = field(init=False)
    STARROCKS_DATABASE: str = field(init=False)

    CLICKHOUSE_HOST: str = field(init=False)
    CLICKHOUSE_PORT: int = field(init=False)
    CLICKHOUSE_USER: str = field(init=False)
    CLICKHOUSE_PASSWORD: str = field(init=False)

    def __post_init__(self):
        self.PORT = int(os.environ.get('PORT', 8080))
        self.CONFIG_PATH = os.environ.get('CONFIG_PATH', '')
        self.INSTANCE_NAME = os.environ.get('INSTANCE_NAME', '')
        self.LPAI_SERVICE_NAME = os.environ.get('LPAI_SERVICE_NAME', '')

        self.OPENAI_ENDPOINT = os.environ.get('OPENAI_ENDPOINT', '')
        self.OPENAI_KEY = os.environ.get('OPENAI_KEY', '')

        self.STARROCKS_HOST = os.environ.get('STARROCKS_HOST', '')
        self.STARROCKS_PORT = os.environ.get('STARROCKS_PORT')
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


config = Config()
