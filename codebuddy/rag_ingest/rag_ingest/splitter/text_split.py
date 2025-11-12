import logging

from sysutils.xcollections import list_sliding

logger = logging.getLogger(__name__)

_chunk_size = 5000
_chunk_step = 3000


def text_split(filepath: str = None,
               content: str = None,
               chunk_size: int = _chunk_size,
               chunk_step: int = _chunk_step) -> list[str]:
    if not content:
        content = open(filepath, 'r').read()
    if len(content) >= 30000:
        logger.info(f'file {filepath} is too long, will skip to ingest')
        return []
    if len(content) > _chunk_size:
        chunks = list_sliding(content, chunk_size, chunk_step)
    else:
        chunks = [content]
    return chunks
