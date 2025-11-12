import json

from rag_ingest.stores import Record, RecordPayload


def test_record_jsonify():
    p1 = RecordPayload(a=1)
    r1 = json.dumps(p1)
    print(f'r1 {r1}')

    rec1 = Record(id='abc', payload=p1)
    r2 = json.dumps(rec1.output())
    print(f'r2 {r2}')
