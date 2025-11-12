from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class RepoInfo:
    id: str
    name: str
    full_name: str
    description: Optional[str]
    clone_url: str
    web_url: str
    default_branch: str
    visibility: str
    last_activity_at: Optional[str] = None


class RepoProvider(ABC):

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token

    @abstractmethod
    def list_repos(self, page_size: int = 100, limit: Optional[int] = None) -> Iterator[RepoInfo]:
        """List all repositories with pagination support

        Args:
            page_size: Number of repos per page
            limit: Maximum number of repos to return (None for all)
        """
        pass

    @abstractmethod
    def get_repo(self, repo_id: str) -> Optional[RepoInfo]:
        """Get a specific repository by ID"""
        pass
