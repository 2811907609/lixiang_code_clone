from types import GenericAlias

# spellchecker:off

def find_longest_match(a, b, b2j, alo=0, ahi=None, blo=0, bhi=None):
    """Find longest matching block in a[alo:ahi] and b[blo:bhi].

    By default it will find the longest match in the entirety of a and b.

    Return (i,j,k) such that a[i:i+k] is equal to b[j:j+k], where
        alo <= i <= i+k <= ahi
        blo <= j <= j+k <= bhi
    and for all (i',j',k') meeting those conditions,
        k >= k'
        i <= i'
        and if i == i', j <= j'

    In other words, of all maximal matching blocks, return one that
    starts earliest in a, and of all those maximal matching blocks that
    start earliest in a, return the one that starts earliest in b.
    """

    if ahi is None:
        ahi = len(a)
    if bhi is None:
        bhi = len(b)

    besti, bestj, bestsize = alo, blo, 0
    # find longest junk-free match
    # during an iteration of the loop, j2len[j] = length of longest
    # junk-free match ending with a[i-1] and b[j]
    j2len = {}
    nothing = []

    for i in range(alo, ahi):
        # look at all instances of a[i] in b; note that because
        # b2j has no junk keys, the loop is skipped if a[i] is junk
        j2lenget = j2len.get
        newj2len = {}
        for j in b2j.get(a[i], nothing):
            # a[i] matches b[j]
            if j < blo:
                continue
            if j >= bhi:
                break
            k = newj2len[j] = j2lenget(j-1, 0) + 1
            if k > bestsize:
                besti, bestj, bestsize = i-k+1, j-k+1, k
        j2len = newj2len

    # Extend the best by non-junk elements on each end.  In particular,
    # "popular" non-junk elements aren't in b2j, which greatly speeds
    # the inner loop above, but also means "the best" match so far
    # doesn't contain any junk *or* popular non-junk elements.
    while besti > alo and bestj > blo and \
            a[besti-1] == b[bestj-1]:
        besti, bestj, bestsize = besti-1, bestj-1, bestsize+1
    while besti+bestsize < ahi and bestj+bestsize < bhi and \
            a[besti+bestsize] == b[bestj+bestsize]:
        bestsize += 1

    return besti, bestj, bestsize


class SequenceMatcher:

    """
    SequenceMatcher is a flexible class for comparing pairs of sequences of
    any type, so long as the sequence elements are hashable.  The basic
    algorithm predates, and is a little fancier than, an algorithm
    published in the late 1980's by Ratcliff and Obershelp under the
    hyperbolic name "gestalt pattern matching".  The basic idea is to find
    the longest contiguous matching subsequence that contains no "junk"
    elements (R-O doesn't address junk).  The same idea is then applied
    recursively to the pieces of the sequences to the left and to the right
    of the matching subsequence.  This does not yield minimal edit
    sequences, but does tend to yield matches that "look right" to people.

    Example, comparing two strings, and considering blanks to be "junk":

    >>> s = SequenceMatcher(lambda x: x == " ",
    ...                     "private Thread currentThread;",
    ...                     "private volatile Thread currentThread;")
    >>>

    Timing:  Basic R-O is cubic time worst case and quadratic time expected
    case.  SequenceMatcher is quadratic time for the worst case and has
    expected-case behavior dependent in a complicated way on how many
    elements the sequences have in common; best case time is linear.
    """

    def __init__(self, a='', b=''):
        self.a = self.b = None
        self.set_seqs(a, b)

    def set_seqs(self, a, b):
        """Set the two sequences to be compared.

        >>> s = SequenceMatcher()
        >>> s.set_seqs("abcd", "bcde")
        >>> s.ratio()
        0.75
        """

        self.set_seq1(a)
        self.set_seq2(b)

    def set_seq1(self, a):
        """Set the first sequence to be compared.

        The second sequence to be compared is not changed.

        SequenceMatcher computes and caches detailed information about the
        second sequence, so if you want to compare one sequence S against
        many sequences, use .set_seq2(S) once and call .set_seq1(x)
        repeatedly for each of the other sequences.

        See also set_seqs() and set_seq2().
        """

        if a is self.a:
            return
        self.a = a

    def set_seq2(self, b):
        if b is self.b:
            return
        self.__chain_b(b)
        self.b = b

    def __chain_b(self, newb):
        old_b = self.b
        if old_b is not None and len(old_b) > 0 and old_b == newb[:len(old_b)]:
            # b is update incrementally, no need to do full enumerate
            b2j = self.b2j # use old b2j
            for i in range(len(old_b), len(newb)):
                elt = newb[i]
                indices = b2j.setdefault(elt, [])
                indices.append(i)
            return

        self.b2j = b2j = {}

        for i, elt in enumerate(newb):
            indices = b2j.setdefault(elt, [])
            indices.append(i)

    def get_last_match_in_diff(self):
        la, lb = len(self.a), len(self.b)

        queue = [(0, la, 0, lb)]
        last_match = [0, 0, 0]
        while queue:
            alo, ahi, blo, bhi = queue.pop()
            i, j, k = x = find_longest_match(self.a, self.b, self.b2j, alo, ahi, blo, bhi)
            if k:   # if k is 0, there was no matching block
                if i >= last_match[0]:
                    last_match = x
                if alo < i and blo < j:
                    queue.append((alo, i, blo, j))
                if i+k < ahi and j+k < bhi:
                    queue.append((i+k, ahi, j+k, bhi))
        return last_match

    __class_getitem__ = classmethod(GenericAlias)

# spellchecker:on

class StreamNextChunk:

    def __init__(self, a, b=None):
        self._a = a
        self._window_size = int(len(a)/15)
        self._matcher = SequenceMatcher(self._a, [])

    def next_chunk(self, current_b, chunk_size=40):
        a = self._a
        if current_b and self._window_size > 100 and len(current_b) >= self._window_size:
            trim_len = len(current_b) - self._window_size
            # we keep more of a, since b may have many increments
            a_lower_len = max(0, trim_len - self._window_size)
            a_upper_len = a_lower_len + self._window_size * 3
            a = self._a[a_lower_len:a_upper_len]
            self._matcher = SequenceMatcher(a)
            current_b = current_b[trim_len:]

        self._matcher.set_seq2(current_b)

        last_match = self._matcher.get_last_match_in_diff()
        if not last_match:
            return self._a[:chunk_size]
        current_matched = (last_match[1] + last_match[2]) == len(current_b)
        if not current_matched:
            return []
        unmatched_offset = last_match[0] + last_match[2]
        return a[unmatched_offset:unmatched_offset + chunk_size]
