import os
from dataclasses import dataclass


@dataclass
class Config:
    EMBED_BASE_URL: str = os.environ.get('EMBED_BASE_URL')
    EMBED_MODEL: str = os.environ.get('EMBED_MODEL')

    LLM_BASE_URL: str = os.environ.get('LLM_BASE_URL')
    LLM_MODEL: str = os.environ.get('LLM_MODEL')

    STORE_TYPE: str = os.environ.get('RAG_STORE_TYPE')
    STORE_URI: str = os.environ.get('RAG_STORE_URI')
    STORE_TABLE: str = os.environ.get('RAG_STORE_TABLE')

    RERANK_URL: str = os.environ.get('RAG_RERANK_URL')
    RERANK_MODEL_NAME: str = os.environ.get('RAG_RERANK_MODEL_NAME')


env_config = Config()
