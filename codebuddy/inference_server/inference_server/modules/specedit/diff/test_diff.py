import time

from inference_server.modules.specedit.diff.diff import StreamNextChunk


def test_next_chunk_predict():
    testcases = [
        # each case is tuple of original_text, current_text, chunk_size, expected_result
        ('aabbccdd', '', 6, 'aabbcc'
        ),  # current is empty, will give chunk_size from beginning
        ('aabbccddeeffgg', 'aabbzz', 6, 'ccdde'),  # current not match at end
        ('aabbccddeeffgg', 'aacc', 6, 'ddeeff'),  # current match at end
        ('a' * 5000 + 'aabbccddeeffgg', 'a' * 5000 + 'aacc', 6,
         'ddeeff'),  # test very long text
        (list(range(10)), [1, 2], 6, [3, 4, 5, 6, 7,
                                      8]),  # should also work with list
        ([0] * 5000 + list(range(10)), [0] * 5000 + [1, 2], 6,
         [3, 4, 5, 6, 7, 8]),  # should also work with list
    ]
    for seq, testcase in enumerate(testcases):
        start_time = time.perf_counter_ns()
        s = StreamNextChunk(testcase[0], [])
        chunk = s.next_chunk(testcase[1], testcase[2])
        end_time = time.perf_counter_ns()
        duration_ms = (end_time - start_time) / 1e6
        print(f'testcase {seq} took {duration_ms} ms')
        assert chunk == testcase[3], f'testcase {seq} failed'
