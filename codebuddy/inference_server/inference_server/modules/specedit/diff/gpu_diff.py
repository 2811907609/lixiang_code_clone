import triton
import triton.language as tl
import torch
import time
import numpy as np


@triton.jit
def sequence_matcher_kernel(
    # Pointers to sequences
    a_ptr,
    b_ptr,
    # Pointers to output matching blocks
    matches_ptr,
    match_count_ptr,
    # Sequence lengths
    a_size,
    b_size,
    # Block params
    BLOCK_SIZE: tl.constexpr,
):
    # Thread ID
    pid = tl.program_id(0)  # noqa

    # Initialize local variables
    i, j, size = 0, 0, 0
    match_idx = 0

    # Loop through sequence a
    while i < a_size:
        # Find matching sequence
        j = 0
        while j < b_size:
            # Check if elements match
            if tl.load(a_ptr + i) == tl.load(b_ptr + j):
                # Found a match, try to extend it
                i_start, j_start = i, j
                size = 0

                # Initialize matching loop
                keep_matching = True
                while keep_matching:
                    # Check bounds first
                    check1 = i_start + size < a_size
                    check2 = j_start + size < b_size

                    # Only check equality if bounds are valid
                    if check1 and check2:
                        check3 = tl.load(a_ptr + i_start +
                                         size) == tl.load(b_ptr + j_start +
                                                          size)
                        # If all conditions met, increment size
                        if check3:
                            size += 1
                        else:
                            keep_matching = False
                    else:
                        keep_matching = False

                # Store match if significant (size > 0)
                if size > 0:
                    if match_idx < BLOCK_SIZE:
                        tl.store(matches_ptr + match_idx * 3 + 0, i_start)
                        tl.store(matches_ptr + match_idx * 3 + 1, j_start)
                        tl.store(matches_ptr + match_idx * 3 + 2, size)
                        match_idx += 1

                    # Move indices past this match
                    i = i_start + size
                    j = j_start + size
                else:
                    j += 1
            else:
                j += 1
        i += 1

    # Store the final match count
    tl.store(match_count_ptr, match_idx)


def get_matching_blocks_gpu(a, b, max_matches=1024):
    # Convert sequences to PyTorch tensors if they aren't already
    if not isinstance(a, torch.Tensor):
        a = torch.tensor(a, device='cuda')
    if not isinstance(b, torch.Tensor):
        b = torch.tensor(b, device='cuda')

    # Ensure tensors are on GPU
    a = a.cuda()
    b = b.cuda()

    # Create output tensors
    matches = torch.zeros((max_matches, 3), dtype=torch.int32, device='cuda')
    match_count = torch.zeros(1, dtype=torch.int32, device='cuda')

    # Launch kernel
    grid = (1,)
    sequence_matcher_kernel[grid](
        a,
        b,
        matches.reshape(-1),
        match_count,
        a.numel(),
        b.numel(),
        BLOCK_SIZE=max_matches,
    )

    # Get actual match count
    count = match_count.item()

    # Extract matches
    result_matches = matches[:count].cpu().numpy()

    # Add the dummy final match as difflib does
    final_match = np.array([[a.numel(), b.numel(), 0]])
    result_matches = np.vstack([result_matches, final_match])

    # Convert to difflib's Match objects format
    from collections import namedtuple
    Match = namedtuple('Match', ['a', 'b', 'size'])
    return [Match(int(m[0]), int(m[1]), int(m[2])) for m in result_matches]


class StreamNextChunk:

    def __init__(self, a, b=None):
        starttime = time.perf_counter_ns()
        # Convert a to tensor if it's not already
        if isinstance(a, torch.Tensor):
            self._a = a
        else:
            self._a = torch.tensor(a, device='cuda')

        print(
            f'GPU stream differ....... init in ms {(time.perf_counter_ns() - starttime)/1e6}'
        )

    def next_chunk(self, current_b, chunk_size=40):
        starttime = time.perf_counter_ns()

        # Convert current_b to tensor if needed
        if not isinstance(current_b, torch.Tensor):
            current_b = torch.tensor(current_b, device='cuda')

        # Get matching blocks using our GPU function
        matches = get_matching_blocks_gpu(self._a, current_b)
        for m in matches:
            print('m========', m)

        if len(matches) <= 1:
            # not matched ever
            return self._a[:chunk_size].cpu().numpy().tolist()

        # matches[-1] is dummy
        last_match = matches[-2]
        current_matched = ((last_match.b + last_match.size) == len(current_b))

        if not current_matched:
            return []

        unmatched_offset = last_match.a + last_match.size

        chunk = self._a[unmatched_offset:unmatched_offset +
                        chunk_size].cpu().numpy().tolist()
        print(f'get chunk =========== {chunk}')
        print(
            f'GPU stream differ....... next chunk in ms {(time.perf_counter_ns() - starttime)/1e6}'
        )
        return chunk
