# ruff: noqa: E702

import llminfer_rs; StreamNextChunk = llminfer_rs.diff.StreamNextChunk


def test_simple():
    s = StreamNextChunk(list(range(8)))
    chunk = s.next_chunk([1, 2, 2, 3, 5], 30)
    assert chunk == [6, 7]
