import os

from rag_ingest.ingest import (
    dir_to_chunks,
    embed_text,
    ingest_dir,
    ingest_dir_v2,
    walk_dir,
)
from rag_ingest.ingest.utils import get_ns_from_repo_url
from repoutils.repo import UnsupportedRepoException
from sysutils.xfs import print_tree


def test_get_ns_from_repo_url():
    testcases = [
        ('gerrit.it.chehejia.com:29418/ep/web/ep-services',
         'repo##gerrit##/ep/web/ep-services'),
        ('ssh://a@gerrit.it.chehejia.com:29418/ep/web/ep-services',
         'repo##gerrit##/ep/web/ep-services'),
        ('http://zhangxudong@gerrit.it.chehejia.com:8080/a/ep/web/ep-services',
         'repo##gerrit##/ep/web/ep-services'),
        ('git@gitlab.chehejia.com:ep/ep-portal-fe.git',
         'repo##gitlab##/ep/ep-portal-fe'),
        ('https://gitlab.chehejia.com/ep/ep-portal-fe.git',
         'repo##gitlab##/ep/ep-portal-fe'),
        ('https://github.com/vllm-project/vllm.git',
         'repo##github##/vllm-project/vllm'),
    ]
    for tc in testcases:
        try:
            ns = get_ns_from_repo_url(tc[0])
        except UnsupportedRepoException:
            ns = 'error'
        assert ns == tc[1], f'{tc[0]} get ns error'


def test_walk_dir():
    rag_dir = os.getenv('RAG_DIR')
    for f in walk_dir(rag_dir):
        print('filepath ........', f)


def test_dir_to_chunks():
    rag_dir = os.getenv('RAG_DIR')
    chunk_result = dir_to_chunks(
        rag_dir,
        skip_files=set([
            '/Users/zhangxudong/code/li/ep-services/services/buildfarm/services/rpc/rpc-server.go'
        ]))
    for f, _chunk in chunk_result:
        print('f...........', f)
        break


def test_embed():
    rag_lang = os.getenv('RAG_LANG')
    rag_dir = os.getenv('RAG_DIR')
    chunk_result = dir_to_chunks(rag_dir, rag_lang)
    for _f, chunk in chunk_result:
        embed_result = embed_text(chunk)
        print('embed result', embed_result)
        # break


async def test_ingest_dir():
    rag_lang = os.getenv('RAG_LANG')
    rag_dir = os.getenv('RAG_DIR')
    rag_ns = os.getenv('RAG_NS')
    print_tree(rag_dir)
    async for r in ingest_dir(rag_dir, rag_lang, namespace=rag_ns):
        print('result...........', r)


def test_v2_ingest_dir():
    rag_lang = os.getenv('RAG_LANG')
    rag_dir = os.getenv('RAG_DIR')
    ingest_dir_v2(rag_dir,
                  rag_lang,
                  namespace='ep-portal',
                  categories=['split.llm_qwen_32B'])
