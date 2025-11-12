
# a simple krew algorithm to build suffix array in O(n)

def build_suffix_array(s):
    """
    Builds the suffix array for the given string using the Kärkkäinen-Sanders algorithm.
    :param s: Input string
    :return: Suffix array
    """
    n = len(s)
    s += chr(0) * 3  # Append sentinel characters to handle edge cases
    SA = _ks_algorithm(list(map(ord, s)), n)
    return [i for i in SA if i < n]  # Remove entries for sentinel characters


def _ks_algorithm(s, n):
    """
    The core Kärkkäinen-Sanders algorithm.
    :param s: List of ASCII values of the input string
    :param n: Length of the original string
    :return: Suffix array
    """
    # Step 1: Recursively sort the suffixes starting at positions i mod 3 != 0
    SA12 = [i for i in range(n) if i % 3 != 0]
    SA12 = sorted(SA12, key=lambda i: _get_triplet(s, i))

    # Step 2: Sort the suffixes starting at positions i mod 3 == 0
    SA0 = [i for i in range(0, n, 3)]
    SA0 = sorted(SA0, key=lambda i: s[i:i + 3])

    # Step 3: Merge the two sorted lists
    return _merge(s, SA12, SA0)



def _get_triplet(s, i):
    """
    Helper function to get the triplet starting at position i.
    """
    return s[i:i + 3]


def _merge(s, SA12, SA0):
    """
    Merges the two sorted suffix arrays SA12 and SA0.
    """
    SA = []
    i, j = 0, 0
    while i < len(SA12) and j < len(SA0):
        if _compare_suffixes(s, SA12[i], SA0[j]) < 0:
            SA.append(SA12[i])
            i += 1
        else:
            SA.append(SA0[j])
            j += 1
    SA.extend(SA12[i:])
    SA.extend(SA0[j:])
    return SA


def _compare_suffixes(s, i, j):
    """
    Compares two suffixes starting at positions i and j.
    """
    while i < len(s) and j < len(s):
        if s[i] < s[j]:
            return -1
        elif s[i] > s[j]:
            return 1
        i += 1
        j += 1
    return 0


# Example usage
if __name__ == "__main__":
    input_string = "banana"
    suffix_array = build_suffix_array(input_string)
    print("Suffix Array:", suffix_array)
    for idx in suffix_array:
        print('suffix', input_string[idx:])
