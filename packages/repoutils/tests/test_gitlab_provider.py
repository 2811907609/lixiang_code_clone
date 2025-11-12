import os
from unittest.mock import patch

import pytest
from repoutils.repo import GitLabProvider, ProviderFactory, RepoInfo


@pytest.fixture
def mock_response():
    projects_data = [
        {
            'id': 1,
            'name': 'project1',
            'path_with_namespace': 'group/project1',
            'description': 'Test project 1',
            'ssh_url_to_repo': 'git@gitlab.example.com:group/project1.git',
            'web_url': 'https://gitlab.example.com/group/project1',
            'default_branch': 'main',
            'visibility': 'private'
        },
        {
            'id': 2,
            'name': 'project2',
            'path_with_namespace': 'group/project2',
            'description': 'Test project 2',
            'ssh_url_to_repo': 'git@gitlab.example.com:group/project2.git',
            'web_url': 'https://gitlab.example.com/group/project2',
            'default_branch': 'master',
            'visibility': 'public'
        }
    ]
    return projects_data


@patch('repoutils.repo.gitlab_provider.requests.get')
def test_list_repos(mock_get, mock_response):
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    provider = GitLabProvider('https://gitlab.example.com', 'test-token')
    repos = list(provider.list_repos(page_size=100))

    assert len(repos) == 2
    assert repos[0].name == 'project1'
    assert repos[0].full_name == 'group/project1'
    assert repos[1].name == 'project2'
    assert repos[1].visibility == 'public'


@patch('repoutils.repo.gitlab_provider.requests.get')
def test_list_repos_pagination(mock_get):
    # First page
    first_page = [{'id': i, 'name': f'project{i}', 'path_with_namespace': f'group/project{i}',
                  'ssh_url_to_repo': f'git@gitlab.example.com:group/project{i}.git',
                  'web_url': f'https://gitlab.example.com/group/project{i}',
                  'default_branch': 'main', 'visibility': 'private'} for i in range(1, 3)]

    # Second page (empty)
    second_page = []

    mock_get.return_value.json.side_effect = [first_page, second_page]
    mock_get.return_value.raise_for_status.return_value = None

    provider = GitLabProvider('https://gitlab.example.com', 'test-token')
    repos = list(provider.list_repos(page_size=2))

    assert len(repos) == 2
    assert mock_get.call_count == 2


@patch('repoutils.repo.gitlab_provider.requests.get')
def test_get_repo(mock_get, mock_response):
    mock_get.return_value.json.return_value = mock_response[0]
    mock_get.return_value.raise_for_status.return_value = None

    provider = GitLabProvider('https://gitlab.example.com', 'test-token')
    repo = provider.get_repo('1')

    assert repo is not None
    assert repo.id == '1'
    assert repo.name == 'project1'
    assert repo.clone_url == 'git@gitlab.example.com:group/project1.git'


def test_factory_create_gitlab_provider():
    provider = ProviderFactory.create_provider('gitlab', 'https://gitlab.example.com', 'token')
    assert isinstance(provider, GitLabProvider)


def test_factory_auto_detect_gitlab():
    provider_type = ProviderFactory.auto_detect_provider('https://gitlab.example.com')
    assert provider_type == 'gitlab'


def test_factory_unsupported_provider():
    with pytest.raises(ValueError):
        ProviderFactory.create_provider('unsupported', 'https://example.com', 'token')


def test_repo_info_dataclass():
    repo = RepoInfo(
        id='1',
        name='test',
        full_name='group/test',
        description='Test repo',
        clone_url='git@gitlab.com:group/test.git',
        web_url='https://gitlab.com/group/test',
        default_branch='main',
        visibility='private'
    )

    assert repo.id == '1'
    assert repo.name == 'test'
    assert repo.visibility == 'private'


@pytest.mark.skipif(
    not os.getenv('GITLAB_URL') or not os.getenv('GITLAB_TOKEN'),
    reason="GITLAB_URL and GITLAB_TOKEN environment variables required"
)
def test_list_repos_real():
    """Real test case for list_repos using actual GitLab API"""
    host = os.getenv('GITLAB_URL')
    token = os.getenv('GITLAB_TOKEN')

    provider = GitLabProvider(host, token)
    repos = list(provider.list_repos(limit=20))

    assert len(repos) == 20
    for repo in repos:
        print('repo=========', repo)
        assert isinstance(repo, RepoInfo)
        assert repo.id
        assert repo.name
        assert repo.full_name
        assert repo.clone_url
        assert repo.web_url
        assert repo.visibility in ['private', 'public', 'internal']
