from unittest.mock import patch

from repoutils.repo import Repo, UnsupportedRepoException
from repoutils.repo.base import BaseRepo


def test_repo_path():
    testcases = [
        ('gerrit.it.chehejia.com:29418/ep/web/ep-services',
         '/ep/web/ep-services'),
        ('ssh://a@gerrit.it.chehejia.com:29418/ep/web/ep-services',
         '/ep/web/ep-services'),
        ('git@gitlab.chehejia.com:ep/ep-portal-fe.git', '/ep/ep-portal-fe'),
        ('https://gitlab.chehejia.com/ep/ep-portal-fe.git', '/ep/ep-portal-fe'),
        ('https://github.com/vllm-project/vllm.git', '/vllm-project/vllm'),
    ]
    for tc in testcases:
        try:
            path = Repo.repo_from(tc[0]).repo_path()
        except UnsupportedRepoException:
            path = 'error'
        assert path == tc[1], f'{tc[0]} failed'


def test_repo_clone():
    with patch.object(BaseRepo, 'clone_repo') as mock_clone_repo:
        # Setup the mock to return a path
        mock_clone_repo.return_value = '/tmp/rag_ingest/a/ep-services'

        repo_url = 'gerrit.it.chehejia.com:29418/ep/web/ep-services'
        repo = Repo.repo_from(repo_url)
        dir = '/tmp/rag_ingest/a'
        ssh_key = '/Users/zhangxudong/.ssh/key_for_spapi0001/spapi0001'
        username = 'spapi0001'

        # Call the method that uses clone_repo
        result = repo.clone_repo(dir,
                                 ssh_key_filepath=ssh_key,
                                 username=username)

        # Verify mock was called with expected arguments
        mock_clone_repo.assert_called_once_with(
            dir,
            username=username,
            ssh_key_filepath=ssh_key,
        )

        # Check result
        assert result == '/tmp/rag_ingest/a/ep-services'
