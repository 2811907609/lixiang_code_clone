import threading
from collections import OrderedDict
from dataclasses import dataclass, field

from inference_server.utils import getLogger

logger = getLogger(__name__)

# yapf: disable
try:
    import llminfer_rs; StreamNextChunk = llminfer_rs.diff.StreamNextChunk  # noqa
    has_llminfer_rs = True
except ImportError:
    has_llminfer_rs = False
    logger.warning("failed to import llminfer_rs, will use a dummy StreamNextChunk")
    from inference_server.modules.specedit.diff.diff import StreamNextChunk
# yapf: enable



@dataclass
class RequestInfo:
    original_draft_tokens: list[int] = None
    stream_next_chunk: StreamNextChunk = None


@dataclass
class RequestManager:
    max_size: int = 1000
    requests: OrderedDict[str, RequestInfo] = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _add_request(self, request_id: str):
        if len(self.requests) >= self.max_size:
            self.requests.popitem(last=False)
        req = RequestInfo()
        self.requests[request_id] = req
        return req

    def _get_request(self, request_id: str):
        return self.requests.get(request_id)

    def _get_or_create_request(self, request_id: str):
        if req := self.requests.get(request_id):
            return req
        else:
            return self._add_request(request_id)

    def _remove_request(self, request_id: str):
        self.requests.pop(request_id, None)

    def set_original_draft_tokens(self, request_id: str,
                                  original_draft_tokens: list[int]):
        if not request_id:
            return
        with self._lock:
            req = self._get_or_create_request(request_id)
            req.original_draft_tokens = original_draft_tokens

    def set_stream_next_chunk(self, request_id: str,
                              original_draft_tokens: list[int]):
        if not request_id:
            return
        if not has_llminfer_rs:
            return
        # with self._lock:
        req = self._get_or_create_request(request_id)
        s = StreamNextChunk(original_draft_tokens)
        req.stream_next_chunk = s

    def get_original_draft_tokens(self, request_id: str):
        with self._lock:
            req = self._get_request(request_id)
            if req:
                return req.original_draft_tokens

    def get_stream_next_chunk(self, request_id: str):
        # with self._lock:
        req = self._get_request(request_id)
        if req:
            return req.stream_next_chunk

    def remove_request(self, request_id: str):
        with self._lock:
            self._remove_request(request_id)
