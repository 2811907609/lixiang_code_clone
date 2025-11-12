#!/usr/bin/env python3
import logging
import os

import fire
from data_scrap.config import config
from data_scrap.tools.gitcommits.scrap_repo import scrap_repo
from data_scrap.tools.gitcommits.scrap_repos import (
    scrap_all_repos,
    scrap_batch_repos,
)
from data_scrap.tools.gitcommits.scrap_state import RepoStatusManager
from data_scrap.tools.gitcommits.send_jsons import send_jsons
from data_scrap.tools.gitcommits.sync_projects import ProjectSync

logging.basicConfig(level=logging.INFO)

def validate_db_path(db_path: str = None, require_exists: bool = True) -> str:
    """Validate and return database path.

    Args:
        db_path: Database path (uses config if not provided)
        require_exists: Whether the database file must exist

    Returns:
        Valid database path

    Raises:
        SystemExit: If validation fails
    """
    db_path = db_path or config.REPO_DB_PATH

    if not db_path:
        print("Error: No database path specified. Set REPO_DB_PATH in config or provide --db_path")
        exit(1)

    if require_exists and not os.path.exists(db_path):
        print(f"Error: Database file does not exist: {db_path}")
        print("Run 'sync_projects' first to create and populate the database")
        exit(1)

    return db_path


def sync_projects(gitlab_url: str = None,
                 gitlab_token: str = None,
                 db_path: str = None,
                 page_size: int = 100,
                 limit: int = 20):
    """Sync GitLab projects to local database.

    Args:
        gitlab_url: GitLab instance URL (uses config if not provided)
        gitlab_token: GitLab API token (uses config if not provided)
        db_path: Database path (uses config if not provided)
        page_size: Number of repos to fetch per page
        limit: Maximum number of repos to sync (no limit if not specified)
    """

    try:
        db_path = validate_db_path(db_path, require_exists=False)
        sync = ProjectSync(gitlab_url, gitlab_token, db_path)
        count = sync.sync_all_repos(page_size=page_size, limit=limit)

        print(f"Successfully added {count} new repositories")
        return count

    except Exception as e:
        print(f"Failed to sync projects: {e}")
        return 1


def reset_all_repos(db_path: str = None):
    """Reset all repositories to pending status for re-scraping.

    Args:
        db_path: Database path (uses config if not provided)
    """
    db_path = validate_db_path(db_path)

    try:
        with RepoStatusManager(db_path) as manager:
            count = manager.reset_all_repos()
            stats = manager.get_stats()

            print(f"Successfully reset {count} repositories to pending status")
            print(f"Current stats: {stats}")
            return count

    except Exception as e:
        print(f"Failed to reset repositories: {e}")
        return 1


def list_pending(db_path: str = None, limit: int = None):
    """List pending repositories to scrap.

    Args:
        db_path: Database path (uses config if not provided)
        limit: Maximum number of repos to display (all if not specified)
    """
    db_path = validate_db_path(db_path)

    try:
        with RepoStatusManager(db_path) as manager:
            stats = manager.get_stats()
            pending_count = stats.get('pending', 0) + stats.get('failed', 0)

            print(f"Database: {db_path}")
            print(f"Total pending repositories: {pending_count}")
            print(f"Stats: {stats}")

            if pending_count > 0:
                pending_repos = manager.get_pending_repos(limit=limit or 1000)
                print(f"\nPending repositories ({len(pending_repos)} shown):")
                for repo in pending_repos:
                    status = repo['status']
                    error_info = f" (Error: {repo['error_message'][:50]}...)" if repo['error_message'] else ""
                    print(f"  - {repo['repo_name']} [{status}]{error_info}")

            return pending_count

    except Exception as e:
        print(f"Failed to list pending repositories: {e}")
        return 1


def sql(query: str, db_path: str = None):
    """Execute SQL query against the repository database.

    Args:
        query: SQL query to execute
        db_path: Database path (uses config if not provided)
    """
    db_path = validate_db_path(db_path)

    try:
        with RepoStatusManager(db_path) as manager:
            results = manager.execute_sql(query)

            if results:
                import json
                print(json.dumps(results, indent=2, default=str))
            else:
                print("No results returned")

            return 0

    except Exception as e:
        print(f"Failed to execute SQL query: {e}")
        return 1


def main():
    fire.Fire({
        'sync_projects': sync_projects,
        'scrap_repos': scrap_batch_repos,
        'scrap_all': scrap_all_repos,
        'scrap_repo': scrap_repo,
        'reset_all_repos': reset_all_repos,
        'list_pending': list_pending,
        'send_jsons': send_jsons,
        'sql': sql
    })


if __name__ == "__main__":
    main()
