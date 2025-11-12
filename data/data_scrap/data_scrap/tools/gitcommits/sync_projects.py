import logging
from typing import Optional

from data_scrap.config import config
from repoutils.repo import GitLabProvider

from .scrap_state import RepoStatusManager

logger = logging.getLogger(__name__)


class ProjectSync:
    def __init__(self,
                 gitlab_url: Optional[str] = None,
                 gitlab_token: Optional[str] = None,
                 db_path: Optional[str] = None):
        self.gitlab_url = gitlab_url or config.GITLAB_URL
        self.gitlab_token = gitlab_token or config.GITLAB_TOKEN
        self.db_path = db_path or config.REPO_DB_PATH
        self.provider = GitLabProvider(self.gitlab_url, self.gitlab_token)

    def sync_all_repos(self, page_size: int = 100, limit: Optional[int] = None) -> int:
        """
        Fetch all GitLab repositories and save them to the state database.
        Returns the number of new repositories added.
        """
        added_count = 0

        with RepoStatusManager(self.db_path) as state_manager:
            logger.info("Starting repository sync from GitLab")

            try:
                for repo_info in self.provider.list_repos(page_size=page_size, limit=limit):
                    existing = state_manager.get_repo_status(repo_info.full_name)

                    if not existing:
                        repo_id = state_manager.add_repo(
                            repo_name=repo_info.full_name,
                            repo_url=repo_info.clone_url,
                            last_activity_at=repo_info.last_activity_at
                        )
                        if repo_id:
                            added_count += 1
                            logger.info(f"Added new repo: {repo_info.full_name}")
                    else:
                        logger.debug(f"Repo already exists: {repo_info.full_name}")

                logger.info(f"Sync completed. Added {added_count} new repositories")

            except Exception as e:
                logger.error(f"Error during repository sync: {e}")
                raise

        return added_count

    def get_sync_stats(self) -> dict:
        """Get current repository statistics from the database."""
        with RepoStatusManager(self.db_path) as state_manager:
            return state_manager.get_stats()
