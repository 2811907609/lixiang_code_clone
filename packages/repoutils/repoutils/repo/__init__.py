from .base import BaseRepo
from .factory import ProviderFactory
from .gerrit import GerritRepo
from .github import GithubRepo
from .gitlab import GitlabRepo
from .gitlab_provider import GitLabProvider
from .provider import RepoInfo, RepoProvider

_category_map = {
    'gerrit': GerritRepo,
    'gitlab': GitlabRepo,
    'gitlabee': GitlabRepo,
    'github': GithubRepo,
}


class UnsupportedRepoException(Exception):
    pass


class Repo(BaseRepo):

    @staticmethod
    def repo_from(repo_url: str, *args, **kwargs) -> BaseRepo:
        ''' repo_url: like following
        'gerrit.it.chehejia.com:29418/ep/web/ep-services', # ssh://user@gerrit/project_path
        'git@gitlabee.chehejia.com:ep/integration/codebuddy-agent.git',
        https://github.com/huggingface/smolagents.git
        '''
        category = Repo.category_type(repo_url)
        cls = _category_map.get(category)
        if not cls:
            raise UnsupportedRepoException(f'Unsupported repo type: {category}')
        return cls(repo_url, *args, category=category, **kwargs)


__all__ = [
    'Repo',
    'UnsupportedRepoException',
    'RepoProvider',
    'RepoInfo',
    'GitLabProvider',
    'ProviderFactory',
]
