import json
import logging
import time
import uuid

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import execute_values

from .base import Record, RecordPayload, VectorStoreBase

'''
-- Create table

CREATE TABLE IF NOT EXISTS rag.code_vector (
    id UUID PRIMARY KEY,
    namespace TEXT,
    categories  text[],
    resource_path TEXT, -- like path or url, you can remove/update it accordingly
    vector vector(1024),
    content_md5 TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

'''

logger = logging.getLogger(__name__)


class PGVector(VectorStoreBase):
    reconnect_attempts = 3
    reconnect_wait_time = 2

    def __init__(
        self,
        pg_uri,
        table,
        **kwargs,
    ):
        self._pg_uri = pg_uri
        self._conn = psycopg2.connect(pg_uri)
        self._cur = self._conn.cursor()
        self._table = table

    def test(self):
        sql = 'select 1 as num;'
        self._execute(sql)
        return self._cur.fetchone()

    def connect(self):
        """Establishes a new connection and cursor to the PostgreSQL database."""
        attempt = 0
        while attempt < self.reconnect_attempts:
            try:
                self._conn = psycopg2.connect(self._pg_uri)
                self._cur = self._conn.cursor()
                logger.info("Connection established.")
                return
            except OperationalError as e:
                logger.warning(f"Connection failed: {e}. Retrying...")
                attempt += 1
                time.sleep(self.reconnect_wait_time)

        raise Exception("Failed to reconnect after several attempts.")

    def _execute_values(self, sql, args):
        try:
            execute_values(self._cur, sql, args)
        except OperationalError:
            self.connect()
            execute_values(self._cur, sql, args)

    def _execute(self, sql, args):
        try:
            self._cur.execute(sql, args)
        except OperationalError:
            self.connect()
            self._cur.execute(sql, args)

    def insert(self, records: list[Record]):
        if not records:
            return
        rows = []
        for r in records:
            r.id = str(uuid.uuid4())
            r.update_md5()
            payload_str = json.dumps(r.payload)
            row = (r.id, r.namespace, r.categories, r.resource_path, r.vector,
                   r.content_md5, payload_str)
            rows.append(row)
        sql = f'insert into {self._table} (id, namespace, categories, resource_path, vector, content_md5, payload) values %s'
        self._execute_values(sql, rows)
        self._conn.commit()

    def ingested_resources(self,
                           namespace: str,
                           categories: list[str] = None) -> set[str]:
        condition = 'namespace = %s'
        params = [namespace]
        if categories:
            condition += ' and categories @> %s'
            params.append(categories)
        sql = f'select resource_path from {self._table} where {condition} group by 1'
        self._execute(sql, params)
        results = self._cur.fetchall()
        return set([r[0] for r in results])

    def search(self,
               namespace: str,
               query_vector,
               categories: list[str] = None,
               limit: int = 10) -> list[Record]:
        condition = 'namespace = %s'
        params = [query_vector, namespace]
        if categories:
            condition += ' and categories @> %s'
            params.append(categories)
        params.append(limit)
        # for distance, the smaller the better
        sql = f'''select id, namespace, resource_path, vector <=> %s::vector as distance, payload
            from {self._table}
            where {condition}
            order by distance
            limit %s'''
        logger.info(f'search sql {sql}')
        self._execute(sql, params)
        results = self._cur.fetchall()
        return [
            Record(id=r[0],
                   namespace=r[1],
                   resource_path=r[2],
                   distance=r[3],
                   payload=RecordPayload(r[4])) for r in results
        ]

    def namespace_existed(self, namespace: str) -> bool:
        sql = f'select id from {self._table} where namespace = %s limit 1'
        self._execute(sql, [namespace])
        return self._cur.fetchone() is not None
