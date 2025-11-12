import os

from repotools.repo.workspace import (
    Workspace,
    fd_wrapper,
    path_distance,
)


def test_path_distance():
    testcases = [
        ('', '', 0),
        ('a', 'a', 0),
        ('a', 'b', 2),
        ('a/b', 'a/c', 2),
        ('a', 'a/b', 1),
        ('a', 'a/b/c/d', 3),
        ('a', 'a/b/c/d/', 3),
    ]
    for t in testcases:
        assert path_distance(t[0], t[1]) == t[2]


def test_fd_wrapper():
    workdir = os.getenv('WORKSPACE')
    files = fd_wrapper('f', workdir, extensions=['c', 'h'])
    print('file list:\n', files)


def test_get_closest_files():
    workdir = os.getenv('WORKSPACE')
    current_file = os.getenv('CURRENT_FILE')
    target_name = os.getenv('TARGET_NAME')
    w = Workspace(workdir)
    files = w.get_closest_files(current_file, target_name)
    print(f'file list: {files}')
