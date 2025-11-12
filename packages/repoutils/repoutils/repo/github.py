from .base import BaseRepo


class GithubRepo(BaseRepo):
    '''repo_url
    https://github.com/huggingface/smolagents.git
    '''

    def clone_url(self, username: str = None):
        return self._repo_url
