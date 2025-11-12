from .base import Record, RecordPayload
from .pgvector import PGVector

_supported_stores = {
    'pgvector': PGVector,
}


def new_store(store_type, *args, **kwargs):
    cls = _supported_stores.get(store_type)
    if not cls:
        raise ValueError(f'Unsupported store type: {store_type}')
    return cls(*args, **kwargs)


__all__ = [
    'new_store',
    'Record',
    'RecordPayload',
]
