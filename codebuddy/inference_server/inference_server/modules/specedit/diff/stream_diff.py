# from inference_server.modules.specedit.diff._stream_diff import FastIncrementalDiffIntArray

import logging
from typing import Tuple

import numpy as np
# import numba as nb
# from numba import jit, njit, types
from numba.typed import List

logger = logging.getLogger('numba')
logger.setLevel(logging.WARNING)


# @nb.njit
def build_suffix_array(text: np.ndarray) -> np.ndarray:
    """Build a suffix array for the given text using a Numba-compatible approach."""
    n = len(text)
    # Create indices
    sa = np.arange(n, dtype=np.int64)

    # Sort indices based on the first character
    for i in range(n):
        for j in range(i + 1, n):
            if text[sa[i]] > text[sa[j]] or (text[sa[i]] == text[sa[j]] and
                                             sa[i] > sa[j]):
                sa[i], sa[j] = sa[j], sa[i]

    return sa


# @nb.njit
def binary_search_in_suffix_array(suffix_array: np.ndarray, fixed: np.ndarray,
                                  pattern: np.ndarray) -> Tuple[int, int]:
    """
    Binary search in the suffix array for a pattern.
    Returns the position in fixed array and match length.
    """
    n = len(suffix_array)
    best_match_pos = -1
    best_match_len = 0

    for i in range(n):  # For simplicity, we use linear search in suffix array
        pos = suffix_array[i]
        match_len = 0

        while (match_len < len(pattern) and pos + match_len < len(fixed) and
               fixed[pos + match_len] == pattern[match_len]):
            match_len += 1

        if match_len > best_match_len:
            best_match_len = match_len
            best_match_pos = pos

    return best_match_pos, best_match_len


# @nb.njit
def optimized_matches(fixed: np.ndarray, suffix_array: np.ndarray,
                      streaming: np.ndarray,
                      start_index: int) -> List[Tuple[int, int, int]]:
    """
    Find matches using the suffix array for better performance

    Args:
        fixed: The fixed array to compare against
        suffix_array: Precomputed suffix array of the fixed array
        streaming: The current streaming array (including new tokens)
        start_index: Index where new tokens start in the streaming array

    Returns:
        List of tuples (fixed_start, stream_start, length) for matching blocks
    """
    matches = []
    stream_len = len(streaming)
    i = max(0, start_index - 2)  # Look back a bit to catch overlapping matches

    while i < stream_len:
        # Extract a pattern starting from current position
        max_pattern_len = min(32, stream_len - i)
        pattern = streaming[i:i + max_pattern_len]

        # Find best match for this pattern
        match_pos, match_len = binary_search_in_suffix_array(
            suffix_array, fixed, pattern)

        if match_len > 0:
            matches.append((match_pos, i, match_len))
            i += match_len
        else:
            i += 1

    return matches


class StreamingDiffer:

    def __init__(self, fixed_array: List[int]):
        # Convert to numpy array for better performance
        self.fixed = np.array(fixed_array, dtype=np.int64)
        self.n = len(self.fixed)

        # Pre-compute suffix array
        self.suffix_array = build_suffix_array(self.fixed)

        # Initialize empty streaming array
        self.streaming = np.array([], dtype=np.int64)
        self.prev_matches = []

    def update_streaming(self,
                         new_tokens: List[int]) -> List[Tuple[int, int, int]]:
        """
        Update the streaming array with new tokens and find matching blocks.
        Returns: List of (fixed_start, stream_start, length) for matching blocks
        """
        if not new_tokens:
            return []

        # Add new tokens to streaming array
        new_arr = np.array(new_tokens, dtype=np.int64)
        old_len = len(self.streaming)
        self.streaming = np.concatenate((self.streaming, new_arr))

        # Find all matches in the current streaming array
        all_matches = optimized_matches(self.fixed, self.suffix_array,
                                        self.streaming, max(0, old_len - 2))
        return all_matches


class StreamNextChunk:

    def __init__(self, a, b=None):
        self._a = a
        self._b = b or []

        self._diff = StreamingDiffer(a)

    def next_chunk(self, current_b, chunk_size=40):
        delta = current_b[len(self._b):]
        self._b = current_b
        if not delta:
            # no change
            return []

        matches = self._diff.update_streaming(delta)
        if not matches:
            return []
        last_match = matches[-1]
        if last_match[1] + last_match[2] != len(current_b):
            # end of current_b is not matched
            return []
        offset = last_match[0] + last_match[2]
        return self._a[offset:offset + chunk_size]
