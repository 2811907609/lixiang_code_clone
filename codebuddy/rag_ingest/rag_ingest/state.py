import logging

from openai import OpenAI
from sysutils.retry import retry

from rag_ingest.envs import env_config
from rag_ingest.stores import new_store

logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

STORE = new_store(env_config.STORE_TYPE,
                  pg_uri=env_config.STORE_URI,
                  table=env_config.STORE_TABLE)

EMBED_CLIENT = OpenAI(api_key='not set', base_url=env_config.EMBED_BASE_URL)

LLM_CLIENT = OpenAI(api_key='not set', base_url=env_config.LLM_BASE_URL)


def init():
    STORE.test()


@retry(n=10, delay=2)
def embed_text(text: str):
    return EMBED_CLIENT.embeddings.create(
        input=[text], model=env_config.EMBED_MODEL).data[0].embedding
