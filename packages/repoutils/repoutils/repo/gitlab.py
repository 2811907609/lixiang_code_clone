from .base import BaseRepo
from .utils import is_scp_like_uri


class GitlabRepo(BaseRepo):
    '''repo_url
    'git@gitlabee.chehejia.com:ep/integration/codebuddy-agent.git',
    '''

    def to_scp_url(self):
        if is_scp_like_uri(self._repo_url):
            return self._repo_url
        else:
            repo_path = self.repo_path()
            if repo_path.startswith('/'):
                repo_path = repo_path[1:]
            return f'git@{self.category}.chehejia.com:{repo_path}.git'

    def clone_url(self, username: str = None):
        '''we use git ssh clone for gitlab CE&EE'''
        return self.to_scp_url()
