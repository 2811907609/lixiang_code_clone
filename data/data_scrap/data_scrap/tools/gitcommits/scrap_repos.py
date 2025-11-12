import logging
import shutil
from pathlib import Path
from typing import Optional

from data_scrap.config import config
from data_scrap.tools.gitcommits.scrap_repo import scrap_repo
from data_scrap.tools.gitcommits.scrap_state import RepoStatusManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def scrap_batch_repos(
    batch_size: Optional[int] = None,
    topic: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bootstrap_servers: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
    no_ssl_verify: Optional[bool] = None,
    dry_run: bool = False,
    db_path: Optional[str] = None,
    output_dir: Optional[str] = None
):
    """
    Process a batch of repositories from database

    Args:
        batch_size: Number of repos to process in this batch
        topic: Kafka topic to send commits to
        start_date: Start date in ISO format
        end_date: End date in ISO format
        bootstrap_servers: Kafka brokers
        max_size_bytes: Maximum size for git objects
        no_ssl_verify: Disable SSL verification
        dry_run: Only fetch without sending to Kafka
        db_path: Path to DuckDB database
        output_dir: Directory to save JSON commit data for debugging/replay
    """
    # Use config defaults if not provided
    batch_size = batch_size or config.BATCH_SIZE
    topic = topic or config.TARGET_TOPIC or None
    bootstrap_servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
    max_size_bytes = max_size_bytes or config.MAX_SIZE_BYTES
    no_ssl_verify = no_ssl_verify if no_ssl_verify is not None else config.NO_SSL_VERIFY
    db_path = db_path or config.REPO_DB_PATH

    with RepoStatusManager(db_path) as manager:
        manager.reset_stuck_repos()

        pending_repos = manager.get_pending_repos(batch_size)

        if not pending_repos:
            logging.info("No repositories pending collection")
            return

        logging.info(f"Processing {len(pending_repos)} repositories")

        success_count = 0
        error_count = 0

        for repo in pending_repos:
            repo_id = repo['id']
            repo_name = repo['repo_name']
            repo_url = repo['repo_url']

            logging.info(f"Processing repo: {repo_name} ({repo_url})")

            try:
                manager.start_processing(repo_id)

                scrap_repo(
                    repo_url=repo_url,
                    topic=topic,
                    start_date=start_date,
                    end_date=end_date,
                    bootstrap_servers=bootstrap_servers,
                    max_size_bytes=max_size_bytes,
                    no_ssl_verify=no_ssl_verify,
                    dry_run=dry_run,
                    output_dir=output_dir
                )

                manager.complete_processing(repo_id)
                success_count += 1
                logging.info(f"Successfully processed repo: {repo_name}")

                # Clean up perceval repositories cache
                # TODO 这里把整个 perceval 的 cache 都删掉了，如果以后改成并发的 scrap_repo 的话
                # 这里就会有问题，需要同步调整
                perceval_cache = Path.home() / ".perceval" / "repositories"
                if perceval_cache.exists():
                    shutil.rmtree(perceval_cache)
                    logging.info(f"Cleaned up perceval cache: {perceval_cache}")

            except Exception as e:
                error_message = str(e)
                logging.error(f"Failed to process repo {repo_name}: {error_message}")

                manager.fail_processing(repo_id, error_message)
                error_count += 1

        stats = manager.get_stats()
        logging.info(f"Batch completed: {success_count} successful, {error_count} failed")
        logging.info(f"Total stats: {stats}")


def scrap_all_repos(
    batch_size: Optional[int] = None,
    topic: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bootstrap_servers: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
    no_ssl_verify: Optional[bool] = None,
    dry_run: bool = False,
    db_path: Optional[str] = None,
    output_dir: Optional[str] = None
):
    """
    Continuously process all repositories from database until none are pending

    Args:
        batch_size: Number of repos to process in each batch
        topic: Kafka topic to send commits to
        start_date: Start date in ISO format
        end_date: End date in ISO format
        bootstrap_servers: Kafka brokers
        max_size_bytes: Maximum size for git objects
        no_ssl_verify: Disable SSL verification
        dry_run: Only fetch without sending to Kafka
        db_path: Path to DuckDB database
        output_dir: Directory to save JSON commit data for debugging/replay
    """
    # Use config defaults if not provided
    batch_size = batch_size or config.BATCH_SIZE
    db_path = db_path or config.REPO_DB_PATH

    total_processed = 0
    batch_count = 0

    logging.info("Starting to process all repositories...")

    while True:
        batch_count += 1
        logging.info(f"Starting batch {batch_count}")

        # Check if there are pending repos before processing
        with RepoStatusManager(db_path) as manager:
            pending_repos = manager.get_pending_repos(1)  # Just check if any exist

            if not pending_repos:
                logging.info("No more repositories pending collection")
                break

        # Process a batch
        scrap_batch_repos(
            batch_size=batch_size,
            topic=topic,
            start_date=start_date,
            end_date=end_date,
            bootstrap_servers=bootstrap_servers,
            max_size_bytes=max_size_bytes,
            no_ssl_verify=no_ssl_verify,
            dry_run=dry_run,
            db_path=db_path,
            output_dir=output_dir
        )

        total_processed += batch_size or config.BATCH_SIZE
        logging.info(f"Completed batch {batch_count}, total processed: {total_processed}")

    # Final stats
    with RepoStatusManager(db_path) as manager:
        final_stats = manager.get_stats()
        logging.info(f"All repositories processed! Final stats: {final_stats}")
