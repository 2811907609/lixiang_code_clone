import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


class RecordPayload(dict):

    def content(self):
        return self['content']


@dataclass
class Record:
    id: str = None
    namespace: str = None
    categories: list[str] = None
    resource_path: str = None
    vector: list[float] = None
    content_md5: str = None
    payload: RecordPayload = None
    # distance is the vector distance of query
    distance: float = None
    rerank_score: float = None  # higher is better

    def content(self):
        return self.payload.content()

    def update_md5(self):
        if self.content_md5:
            return
        m = hashlib.md5()
        content = self.payload.content()
        m.update(content.encode('utf-8'))
        self.content_md5 = m.hexdigest()

    def output(self):
        return dict(id=self.id,
                    resource_path=self.resource_path,
                    payload=self.payload)


class VectorStoreBase(ABC):
    buf_size = 100
    buffer_records: list[Record] = None

    @abstractmethod
    def test(self):
        pass

    @abstractmethod
    def insert(self, records: list[Record]):
        pass

    @abstractmethod
    def ingested_resources(self, namespace: str) -> set[str]:
        '''获取已经ingest的资源(文件)，便于做断点续传之类的处理'''
        pass

    @abstractmethod
    def search(self,
               namespace: str,
               query_vector,
               categories: list[str] = None,
               limit: int = 10):
        pass

    @abstractmethod
    def namespace_existed(self, namespace: str) -> bool:
        pass

    def buf_and_insert(self, records: list[Record]):
        if not self.buffer_records:
            self.buffer_records = []
        self.buffer_records.extend(records)
        if len(self.buffer_records) >= self.buf_size:
            self.insert(self.buffer_records[:self.buf_size])
            self.buffer_records = self.buffer_records[self.buf_size:]

    def buf_flush(self):
        '''flush buffer records'''
        if self.buffer_records:
            self.insert(self.buffer_records)
            self.buffer_records = []
