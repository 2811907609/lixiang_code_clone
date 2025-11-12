#!/usr/bin/env python3
import logging
from typing import Optional

import fire
from data_scrap.config import config
from data_scrap.lib.kafka import create_kafka_helper
from data_scrap.tools.gitcommits.perceval import run_perceval_git

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def scrap_repo(
    repo_url: str,
    topic: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bootstrap_servers: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
    no_ssl_verify: Optional[bool] = None,
    dry_run: bool = False,
    output_dir: Optional[str] = None
):
    """
    Scrape git commits from a repository and send to Kafka

    Args:
        repo_url: Git repository URL
        topic: Kafka topic to send commits to (if None, won't send to Kafka)
        start_date: Start date in ISO format (e.g., "2023-01-01T00:00:00")
        end_date: End date in ISO format (e.g., "2023-12-31T23:59:59")
        bootstrap_servers: Comma-separated list of Kafka brokers
        max_size_bytes: Maximum size in bytes for git objects
        no_ssl_verify: Disable SSL verification
        dry_run: If True, only fetch commits without sending to Kafka
        output_dir: Directory to save JSON commit data for debugging/replay
    """
    # Use config defaults if not provided
    bootstrap_servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
    topic = topic or config.TARGET_TOPIC or None
    max_size_bytes = max_size_bytes or config.MAX_SIZE_BYTES
    no_ssl_verify = no_ssl_verify if no_ssl_verify is not None else config.NO_SSL_VERIFY

    # Set default date range if not provided
    # beijing_tz = 'Asia/Shanghai'
    # if not start_date:
    #     start_date = config.START_DATE or arrow.now(beijing_tz).shift(days=-30).isoformat()
    # if not end_date:
    #     end_date = config.END_DATE or arrow.now(beijing_tz).isoformat()

    # Determine if we should send to Kafka
    send_to_kafka = not dry_run and topic is not None

    logging.info(f"Starting to scrape repository: {repo_url}")
    logging.info(f"Date range: {start_date} to {end_date}")
    logging.info(f"Dry run: {dry_run}")
    if send_to_kafka:
        logging.info(f"Target topic: {topic}")
    else:
        logging.info("Will not send to Kafka (dry run or no topic specified)")

    try:
        # Get commits using perceval
        logging.info("Fetching commits with perceval...")
        commits = run_perceval_git(
            origin=repo_url,
            start_datetime=start_date,
            finish_datetime=end_date,
            max_size_bytes=max_size_bytes,
            no_ssl_verify=no_ssl_verify,
            zone=config.RD_ZONE,
            output_dir=output_dir,
        )

        logging.info(f"Found {len(commits)} commits")

        if not commits:
            logging.info("No commits found in the specified date range")
            return

        if not send_to_kafka:
            logging.info(f"Dry run completed: found {len(commits)} commits")
            return

        # Initialize Kafka helper
        kafka = create_kafka_helper(bootstrap_servers)

        # Send each commit to Kafka
        success_count = 0
        error_count = 0

        for i, commit in enumerate(commits):
            try:
                # Use commit hash as message key for partitioning
                key = commit.get('data', {}).get('commit', '')

                kafka.send_json(topic, commit, key=key)
                success_count += 1

                if (i + 1) % 100 == 0:
                    logging.info(f"Sent {i + 1}/{len(commits)} commits")

            except Exception as e:
                logging.error(f"Failed to send commit {i}: {e}")
                error_count += 1
                continue

        # Wait for all messages to be delivered
        logging.info("Flushing remaining messages...")
        kafka.flush()
        kafka.close()

        logging.info(f"Completed: {success_count} sent, {error_count} failed")

    except Exception as e:
        logging.error(f"Failed to scrape repository {repo_url}: {e}")
        raise


def main():
    """Main entry point for fire CLI"""
    fire.Fire(scrap_repo)


if __name__ == '__main__':
    main()
