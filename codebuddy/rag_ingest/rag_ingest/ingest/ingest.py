import asyncio
import logging
import os
import time
from typing import Callable

from sysutils.xcollections import yield_agg

from rag_ingest.language import get_language_config, get_language_config_by_file
from rag_ingest.splitter import code_split_as_text, llm_code_summary
from rag_ingest.state import LLM_CLIENT, STORE, embed_text
from rag_ingest.stores import Record, RecordPayload

logger = logging.getLogger(__name__)
STOP_WALKING = object()


def walk_dir(dir: str, callback: Callable[[str, str], None]):
    git_dir = os.path.join(dir, '.git')
    for root, _dirs, files in os.walk(dir):
        if root.startswith(git_dir):
            continue
        for file in files:
            filepath = os.path.join(root, file)
            r = callback(filepath, file=file, root=root)
            if r is STOP_WALKING:
                return
            yield r


def _relative_path(dir, filepath):
    p = filepath.removeprefix(dir)
    if p.startswith('/'):
        p = p[1:]
    return p


def dir_to_chunks(dir: str, skip_files: set[str] = None):

    def f(filepath, *args, file=None, **kwargs):
        rel_path = _relative_path(dir, filepath)
        if skip_files and (rel_path in skip_files):
            return
        lang_config = get_language_config_by_file(file)
        if not lang_config:
            return
        if lang_config.should_ignore(filepath):
            return
        logger.info(f'get filepath {rel_path}')
        chunks = code_split_as_text(filepath=filepath)
        for chunk in chunks:
            if not chunk:
                continue
            # # llama index 的切分似乎并不太好，有时候会有一些很小的无意义的片，过滤掉
            # if len(chunk) < 20:
            #     continue
            yield filepath, chunk

    for result in walk_dir(dir, callback=f):
        yield from result


async def ingest_dir(dir: str,
                     namespace: str = None,
                     categories: list[str] = None,
                     batch_size: int = 50):
    ingested_paths = STORE.ingested_resources(namespace, categories=categories)
    g = yield_agg(dir_to_chunks(dir, skip_files=ingested_paths), batch_size)
    for chunks in g:
        records: list[Record] = []
        for (f, chunk) in chunks:
            resource_path = _relative_path(dir, f)
            logger.info(f'filepath {resource_path}{"=" * 20}\n{chunk}')
            if not chunk:
                continue
            embed_chunk = f'// filepath: {resource_path}\n{chunk}'
            vector = embed_text(embed_chunk)
            payload = RecordPayload(content=embed_chunk)
            record = Record(namespace=namespace,
                            resource_path=resource_path,
                            categories=categories,
                            vector=vector,
                            payload=payload)
            records.append(record)
        STORE.buf_and_insert(records)
        await asyncio.sleep(0.5)  # Use asyncio.sleep instead of time.sleep
        yield
    STORE.buf_flush()


def ingest_file(lang: str, filepath: str, namespace: str = None):
    logger.info(f'will ingest file {filepath}')
    chunks = llm_code_summary(LLM_CLIENT, lang=lang, filepath=filepath)
    records: list[Record] = []
    categories = ['split.llm_qwen_32B']
    for chunk in chunks:
        if not chunk:
            continue
        text_tobe_embedded = f'filepath: {filepath}\n{chunk}'
        vector = embed_text(text_tobe_embedded)
        payload = RecordPayload(content=chunk)
        record = Record(namespace=namespace,
                        resource_path=filepath,
                        vector=vector,
                        categories=categories,
                        payload=payload)
        records.append(record)
        time.sleep(0.1)
    return records


def ingest_dir_v2(dir: str,
                  lang: str,
                  namespace: str = None,
                  categories: list[str] = None):
    ingested_paths = STORE.ingested_resources(namespace, categories=categories)
    lang_config = get_language_config(lang)
    for root, _dirs, files in os.walk(dir):
        for file in files:
            if lang_config.should_ignore(file):
                continue
            filepath = os.path.join(root, file)
            if filepath in ingested_paths:
                continue
            records = ingest_file(lang, filepath, namespace=namespace)
            STORE.buf_and_insert(records)
    STORE.buf_flush()
