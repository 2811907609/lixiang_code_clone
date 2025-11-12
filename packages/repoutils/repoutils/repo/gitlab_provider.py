import logging
from typing import Any, Dict, Iterator, Optional
from urllib.parse import urljoin

import requests

from .provider import RepoInfo, RepoProvider

logger = logging.getLogger(__name__)


class GitLabProvider(RepoProvider):

    def __init__(self, base_url: str, token: str):
        super().__init__(base_url, token)
        self.api_url = urljoin(self.base_url, '/api/v4/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = urljoin(self.api_url, endpoint)
        response = requests.get(url, headers=self.headers, params=params or {})
        response.raise_for_status()
        return response

    def list_repos(self, page_size: int = 100, limit: Optional[int] = None) -> Iterator[RepoInfo]:
        page = 1
        yielded_count = 0

        while True:
            params = {
                'per_page': page_size,
                'page': page,
                'simple': True,
                # 'membership': True, # membership=true 表示只列出当前用户是它的memberd项目，而我们是用管理员账号获取所有的
                'order_by': 'id',
                'sort': 'asc'
            }

            try:
                logger.info(f"Fetching page {page} with {page_size} repos per page")
                response = self._make_request('projects', params)
                projects = response.json()

                if not projects:
                    break

                for project in projects:
                    if limit is not None and yielded_count >= limit:
                        return
                    yield self._project_to_repo_info(project)
                    yielded_count += 1

                if len(projects) < page_size:
                    break

                page += 1

            except requests.RequestException as e:
                logger.error(f"Error fetching repositories page {page}: {e}")
                break

    def get_repo(self, repo_id: str) -> Optional[RepoInfo]:
        try:
            response = self._make_request(f'projects/{repo_id}')
            project = response.json()
            return self._project_to_repo_info(project)
        except requests.RequestException as e:
            logger.error(f"Error fetching repository {repo_id}: {e}")
            return None

    def _project_to_repo_info(self, project: Dict[str, Any]) -> RepoInfo:
        return RepoInfo(
            id=str(project['id']),
            name=project['name'],
            full_name=project['path_with_namespace'],
            description=project.get('description', ''),
            clone_url=project['ssh_url_to_repo'],
            web_url=project['web_url'],
            default_branch=project.get('default_branch', 'master'),
            visibility=project.get('visibility', 'private'),
            last_activity_at=project.get('last_activity_at')
        )
