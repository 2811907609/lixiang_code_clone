import logging
import os
import re
import shutil
import subprocess
from abc import abstractmethod
from typing import Optional

from sysutils.xurl import url_parse

from .utils import is_scp_like_uri

logger = logging.getLogger(__name__)

_pattern_scp_like_uri = re.compile(r'^[\w\-]+@[\w\-\.]+:')  # git@xxxx:a/b/c.git


class BaseRepo:

    def __init__(self, repo_url: str, category: str, *args, **kwargs):
        self._repo_url = repo_url
        self.category = category

    def __str__(self):
        return f'{self.__class__.__name__}({self._repo_url})'

    @staticmethod
    def category_type(repo_url: str) -> Optional[str]:
        if 'gerrit' in repo_url:
            return 'gerrit'
        elif 'gitlabee' in repo_url:
            return 'gitlabee'
        elif 'gitlab' in repo_url:
            return 'gitlab'
        elif 'github.com' in repo_url:
            return 'github'

    def repo_path(self):
        # if it is scp style, git@xxxx:a/b/c.git
        if is_scp_like_uri(self._repo_url):
            path = self._repo_url.split(':', 1)[1]
        else:
            # standard URL style
            parsed_url = url_parse(self._repo_url)
            path = parsed_url.path
            # for gerrit repo like http://zhangxudong@gerrit.it.chehejia.com:8080/a/ep/web/ep-services
            # we should remove the /a prefix
            if self.category == 'gerrit':
                if path.startswith('/a/'):
                    path = path[2:]  # keep the first /

        if not path.startswith('/'):
            path = '/' + path
        path = path.removesuffix('.git')
        return path

    @abstractmethod
    def clone_url(self, username: str = None):
        pass

    @property
    def repo_basename(self):
        path = self.repo_path()
        return os.path.basename(path)

    def clone_repo(
        self,
        dir: str,
        remove_if_exists: bool = True,
        username: str = None,
        depth: int = None,
        ssh_key_filepath: str = None,
        disable_host_check: bool = True,
    ):
        basename = self.repo_basename
        clone_target_dir = os.path.join(dir, basename)
        if remove_if_exists and os.path.exists(clone_target_dir):
            # check if it is a git repo, to avoid wrongly removing a directory
            if os.path.isdir(os.path.join(clone_target_dir, '.git')):
                logger.info(f'will remove dir {clone_target_dir}')
                shutil.rmtree(clone_target_dir)

        clone_url = self.clone_url(username=username)
        cmd = ['git', 'clone']
        if depth:
            cmd.extend(['--depth', str(depth)])
        cmd.extend([clone_url, clone_target_dir])

        ssh_options = []
        if ssh_key_filepath:
            ssh_options.append(f'-i {ssh_key_filepath}')
        if disable_host_check:
            ssh_options.append('-o StrictHostKeyChecking=no')
            ssh_options.append('-o UserKnownHostsFile=/dev/null')

        envs = os.environ.copy()
        if ssh_options:
            git_ssh_option = 'ssh ' + ' '.join(ssh_options)
            envs['GIT_SSH_COMMAND'] = git_ssh_option

        return_code = None

        try:
            logger.info(f'will run cmd: {" ".join(cmd)}')
            with subprocess.Popen(cmd,
                                  env=envs,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True) as process:
                for line in process.stdout:
                    line = line.rstrip()
                    logger.info(line)

                return_code = process.wait()
                if return_code != 0:
                    logging.error(
                        f"Error cloning repository, return code {return_code}")

        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            raise
        if return_code != 0:
            logger.error(f'error cloning, command is {cmd}')
            raise Exception(
                f"Error cloning {self._repo_url}, return code {return_code}")
        return clone_target_dir
