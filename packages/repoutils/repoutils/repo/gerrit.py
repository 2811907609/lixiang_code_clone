from .base import BaseRepo


class GerritRepo(BaseRepo):
    ''' repo_url
    'gerrit.it.chehejia.com:29418/ep/web/ep-services', # ssh://user@gerrit/project_path
    '''

    def clone_url(self, username: str = None):
        u = ''
        if username:
            u = f'{username}@'
        return f'ssh://{u}{self._repo_url}'
