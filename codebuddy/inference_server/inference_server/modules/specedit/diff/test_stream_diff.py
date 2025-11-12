import time
from inference_server.modules.specedit.diff.stream_diff import StreamingDiffer, StreamNextChunk


def test_stream_differ():
    fixed = [1, 2, 3, 4, 5, 6]
    differ = StreamingDiffer(fixed)

    # First update
    new_tokens = [1, 2]
    matches = differ.update_streaming(new_tokens)
    print(f"New tokens: {new_tokens}")
    print(f"Matches: {matches}")

    # Second update
    new_tokens = [5, 6]
    matches = differ.update_streaming(new_tokens)
    print(f"New tokens: {new_tokens}")
    print(f"Matches: {matches}")


def test_stream_next_chunk():
    print('\n')
    fixed_ints = list(range(1, 12))
    stream_ints = [1, 2, 3, 3, 3, 6, 7, 8, 10, 9, 11, 13, 14]

    stream_chunk = StreamNextChunk(fixed_ints, [])
    for i in range(1, len(stream_ints)):
        print('stream..........', stream_ints[:i])
        stream_chunk.next_chunk(stream_ints[:i])


def test_stream_next_chunk1():
    testcases = [
        (list(range(10)), [1, 2], 6, [3, 4, 5, 6, 7,
                                      8]),  # should also work with list
        ([0] * 5000 + list(range(10)), [0] * 5000 + [1, 2], 6,
         [3, 4, 5, 6, 7, 8]),  # should also work with list
    ]
    print('len', len(testcases))
    # numba jit has startup overhead, so we need to warm up
    s = StreamNextChunk([1], [])
    s.next_chunk([2])

    for seq, testcase in enumerate(testcases):
        print('tc ===', seq)
        start_time = time.perf_counter_ns()
        stream_chunk = StreamNextChunk(testcase[0], [])
        chunk = stream_chunk.next_chunk(testcase[1], testcase[2])
        end_time = time.perf_counter_ns()
        duration_ms = (end_time - start_time) / 1e6
        print(f'testcase {seq} took {duration_ms} ms')
        assert chunk == testcase[3], f'testcase {seq} failed'

        # following test time per char update
        for i in range(3):
            start_time = time.perf_counter_ns()
            chunk = stream_chunk.next_chunk(testcase[1] + [i], testcase[2])
            end_time = time.perf_counter_ns()
            duration_ms = (end_time - start_time) / 1e6
            print(f'testcase {seq} took {duration_ms} ms')
    print('end=========')
