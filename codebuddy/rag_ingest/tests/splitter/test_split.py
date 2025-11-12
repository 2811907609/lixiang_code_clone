import os

from rag_ingest.splitter import code_split, llm_code_summary
from rag_ingest.state import LLM_CLIENT


def test_code_split():
    rag_file = os.getenv('RAG_FILE')
    rag_lang = os.getenv('RAG_LANG')
    chunks = code_split(rag_lang, rag_file)
    for chunk in chunks:
        print("chunk..==================..\n", chunk)


def test_llm_summary():
    rag_file = os.getenv('RAG_FILE')
    rag_lang = os.getenv('RAG_LANG')
    chunks = llm_code_summary(LLM_CLIENT, rag_lang, rag_file)
    print(f'chunks {chunks}')
