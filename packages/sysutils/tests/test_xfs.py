import os

from sysutils.xfs import count_files


def test_count_files():
    dir = os.getenv('TEST_DIR')
    if not dir:
        dir = '.'
    print(count_files(dir))
