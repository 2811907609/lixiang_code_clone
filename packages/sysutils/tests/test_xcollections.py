from sysutils.xcollections import list_sliding


def test_list_sliding():
    l1 = [i for i in range(10)]
    r1 = list_sliding(l1, 3, 2)
    assert r1 == [[0, 1, 2], [2, 3, 4], [4, 5, 6], [6, 7, 8], [8, 9]]

    l1 = [i for i in range(9)]
    r1 = list_sliding(l1, 3, 2)
    assert r1 == [[0, 1, 2], [2, 3, 4], [4, 5, 6], [6, 7, 8], [8]]

    l1 = [i for i in range(8)]
    r1 = list_sliding(l1, 3, 2)
    assert r1 == [[0, 1, 2], [2, 3, 4], [4, 5, 6], [6, 7]]

    l1 = [i for i in range(8)]
    r1 = list_sliding(l1, 3, 3)
    assert r1 == [[0, 1, 2], [3, 4, 5], [6, 7]]
