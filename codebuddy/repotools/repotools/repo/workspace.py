import logging
import os
import subprocess
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def trim_path(p: str) -> str:
    return p.rstrip('/')


def path_distance(path1: str, path2: str) -> int:
    '''calculate distance of two path.
    we strip common prefix of the two part, and then sum left parts.
    for example, a/b/c and a/b/d, the distance is 2
    a/b/c and a/, the distance is 3
    '''
    path1 = trim_path(path1)
    path2 = trim_path(path2)

    if path1 == path2:
        return 0
    parts1 = path1.split('/')
    parts2 = path2.split('/')
    min_len = min(len(parts1), len(parts2))
    for i in range(min_len):
        if parts1[i] != parts2[i]:
            return len(parts1) + len(parts2) - 2 * i
    return len(parts1) + len(parts2) - 2 * min_len


@lru_cache(maxsize=None)
def command_exists(cmd):
    return subprocess.call(['which', cmd],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def fd_wrapper(
    typ,
    dir: Optional[str] = None,
    pattern: Optional[str] = None,
    excludes: Optional[list[str]] = None,
    extensions: Optional[list[str]] = None,
    min_size: Optional[str] = None,
    max_size: Optional[str] = None,
    rel_path: bool = True,
) -> list[str]:
    ''' a wrapper for the command fd to get file list'''
    if not command_exists('fd'):
        raise Exception(
            'fd is not installed, we use `fd` to list files, please install it')

    dir = dir or '.'
    cmd = ['fd', '-t', typ, '--base-directory', dir]
    if excludes:
        for e in excludes:
            cmd += ['-E', e]
    if extensions:
        for e in extensions:
            cmd += ['-e', e]
    if min_size:
        cmd += ['-S', '+' + str(min_size)]
    if max_size:
        cmd += ['-S', '-' + str(max_size)]

    cmd.append(pattern or '')

    logger.debug(f'fd cmd: {cmd}')
    try:
        out = subprocess.check_output(cmd)
    except Exception as e:
        logging.error('got error', e)
        return []
    files = out.decode().split('\n')
    if files and files[-1] == '':
        files = files[:-1]
    return files


_common_excludes = ['node_modules/', 'vendor/', 'vendors/', 'logs/', 'tmp/']


class Workspace:

    def __init__(self,
                 workdir,
                 excludes: Optional[list[str]] = None,
                 exitensions: Optional[list[str]] = None) -> None:
        self._workdir = workdir
        self._excludes = excludes or _common_excludes
        self._extensions = exitensions or []
        self._all_files = None

    def _get_all_files(self) -> list[str]:
        return fd_wrapper('f',
                          dir=self._workdir,
                          excludes=self._excludes,
                          extensions=self._extensions)

    @property
    def all_files(self) -> list[str]:
        if self._all_files is not None:
            return self._all_files
        self._all_files = self._get_all_files()
        return self._all_files

    def get_closest_files(self,
                          current_file: str,
                          target_name: str,
                          top_count: int = 10) -> list[str]:
        files = []
        if not (current_file and target_name):
            return []

        for f in self.all_files:
            if not f.endswith(target_name):
                continue
            files.append(f)

        current_dir = os.path.dirname(current_file)

        def path_sort_key(f: str):
            return path_distance(f.removeprefix(target_name), current_dir)

        files.sort(key=path_sort_key)
        return files[:top_count]
