'''
make _llm a global variable so that it can be reused in ipython even
the source code auto reload, by this way, we can save a lot of model
loading time.

why make it a standalone module?
ipython autoreload will reinitialized global variable if file changed.
'''

from typing import Dict, Optional, TypeVar

from inference_server.backend.basemodel import BaseModel

T = TypeVar('T', bound=BaseModel)

_llm: Dict[str, T] = {}


def set_llm(m: T, instance_name='default'):
    _llm[instance_name] = m


def get_llm(instance_name='default') -> Optional[T]:
    return _llm.get(instance_name, None)


def get_all_llm():
    return _llm.copy()
