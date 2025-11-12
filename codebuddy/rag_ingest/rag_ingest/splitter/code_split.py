import logging
from functools import lru_cache

from llama_index.core.node_parser import CodeSplitter
from openai import OpenAI
from sysutils.retry import retry

from rag_ingest.prompts import render
from rag_ingest.state import LLM_CLIENT

from .text_split import text_split

logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def get_splitter(lang: str):
    return CodeSplitter(lang,
                        chunk_lines=80,
                        chunk_lines_overlap=30,
                        max_chars=4000)


def code_split(lang: str, filepath: str = None, content: str = None):
    '''当前的CodeSplitter 似乎并不会在语法断点切分，后续需要优化. '''
    if not content:
        content = open(filepath, 'r').read()
    chunks = get_splitter(lang).split_text(content)
    return chunks


_chunk_size = 5000
_chunk_step = 3000

_try_encoding = ['utf-8', 'iso8859', 'gbk']


def try_read_file(filepath: str) -> str:
    for encoding in _try_encoding:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    logger.info(f'file {filepath} is not readable')
    return ''


def code_split_as_text(filepath: str = None,
                       content: str = None,
                       chunk_size: int = _chunk_size) -> list[str]:
    if not content:
        content = try_read_file(filepath)
    if len(content) >= 30000:
        logger.info(f'file {filepath} is too long, will skip to ingest')
        return []
    if len(content) <= _chunk_size:
        return [content]
    lines: list[str] = content.split('\n')
    small_chunks: list[str] = []
    current_chunk: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_chunk.append(line)
            continue
        # has indent
        if line[:1].isspace():
            current_chunk.append(line)
        else:
            if current_chunk:
                small_chunks.append('\n'.join(current_chunk))
                current_chunk = []
            current_chunk.append(line)
    if current_chunk:
        small_chunks.append('\n'.join(current_chunk))

    # merge small chunks to chunks that each chunk <= _chunk_size
    if not small_chunks:
        return []
    chunks = []
    current_chunk = small_chunks[0]
    for small_chunk in small_chunks[1:]:
        if len(current_chunk) + len(small_chunk) <= chunk_size:
            current_chunk += '\n' + small_chunk
        else:
            chunks.append(current_chunk)
            current_chunk = small_chunk
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


@retry(n=10, delay=2)
def _llm_code_summary(llm_client: OpenAI,
                      lang: str,
                      filepath: str = None,
                      chunk: str = None):
    prompt = render('code_summary.jinja2', lang=lang, path=filepath, code=chunk)
    logger.info(f'prompt length {len(prompt)}')
    messages = [{'role': 'user', 'content': prompt}]
    chat_completion = LLM_CLIENT.chat.completions.create(
        model='gpt4-o',
        stream=False,
        messages=messages,
    )
    print(chat_completion)
    choices = chat_completion.choices
    if choices:
        return choices[0].message.content
    else:
        return None


def llm_code_summary(llm_client: OpenAI,
                     lang: str,
                     filepath: str = None,
                     content: str = None):
    '''使用llm 能力来总结/分割文件的代码'''
    chunks = text_split(filepath, content)
    results = []
    for chunk in chunks:
        result = _llm_code_summary(llm_client, lang, filepath, chunk)
        if result:
            results.append(result)
    return results
