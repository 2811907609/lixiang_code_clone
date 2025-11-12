import logging
import time
from dataclasses import dataclass

import requests
from sysutils.retry import retry

from rag_ingest.envs import env_config
from rag_ingest.state import STORE, embed_text

_session = requests.Session()


@dataclass
class QueryStat:
    '''unit is second.'''
    embed_duration: float = None
    db_query_duration: float = None
    rerank_duration: float = None


@retry(n=2, delay=1)
def rerank_scores(q: str, candidates: list[str]):
    params = dict(model=env_config.RERANK_MODEL_NAME,
                  query=q,
                  inputs=candidates)
    res = _session.post(env_config.RERANK_URL, json=params)
    if res.status_code != 200:
        raise Exception(f'rerank failed: {res.text}')
    result = res.json()
    return result['scores']


def query(q: str,
          namespace: str,
          categories: list[str] = None,
          recall_limit: int = 20,
          rerank_limit: int = 5):
    query_stat = QueryStat()
    start_time = time.perf_counter()
    vector = embed_text(q)
    embed_end_time = time.perf_counter()
    query_stat.embed_duration = embed_end_time - start_time

    records = STORE.search(namespace,
                           vector,
                           categories=categories,
                           limit=recall_limit)
    print(f'record length {len(records)}')
    db_query_end_time = time.perf_counter()
    query_stat.db_query_duration = db_query_end_time - embed_end_time

    if len(records) <= rerank_limit:
        return records, query_stat

    if rerank_limit >= recall_limit:
        logging.warning('rerank is >= recall, no need to do rerank')
        return records, query_stat

    try:
        scores = rerank_scores(q, [r.content() for r in records])
    except Exception as e:
        logging.error(f'rerank failed: {e}')
        return records[:rerank_limit], query_stat

    rerank_end_time = time.perf_counter()
    query_stat.rerank_duration = rerank_end_time - db_query_end_time
    for i, r in enumerate(records):
        r.rerank_score = scores[i]
    # for score, the larger the better
    records.sort(key=lambda x: x.rerank_score, reverse=True)
    return records[:rerank_limit], query_stat
