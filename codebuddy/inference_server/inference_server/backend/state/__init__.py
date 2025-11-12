from .request import RequestManager
from .llm_instances import set_llm, get_llm, get_all_llm

request_manager = RequestManager()


__all__ = [
    "request_manager",
    "get_llm",
    "get_all_llm",
    "set_llm",
]
