from repoutils.repo import Repo

_default_ns_prefix = 'repo'


def get_ns_from_repo(repo: Repo):
    return f'{_default_ns_prefix}##{repo.category}##{repo.repo_path()}'


def get_ns_from_repo_url(url):
    repo = Repo.repo_from(url)
    return get_ns_from_repo(repo)
