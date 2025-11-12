import asyncio
import json
import logging
from pathlib import Path
from typing import Set, Tuple

import httpx
from data_scrap.config import config
from data_scrap.lib.send_event import send_event


def send_jsons(json_dir: str = None, json_file: str = None):
    """Send collected JSON files to API endpoint.

    Args:
        json_dir: Directory containing JSON files to send
        json_file: Specific JSON file to send

    """
    logging.basicConfig(level=logging.INFO)

    if not json_dir and not json_file:
        print("Error: Must specify either json_dir or json_file")
        return 1

    if json_dir and json_file:
        print("Error: Cannot specify both json_dir and json_file")
        return 1

    try:
        if json_file:
            success_count, error_count = asyncio.run(send_json_files(json_dir=None, json_file=json_file))
        else:
            success_count, error_count = asyncio.run(send_json_files(json_dir=json_dir, json_file=None))

        print(f"Summary: {success_count} sent, {error_count} failed")
        return error_count

    except Exception as e:
        print(f"Failed to send JSON files: {e}")
        return 1


def load_sent_files(sent_file_path: Path) -> Set[str]:
    """Load list of already sent files."""
    if sent_file_path.exists():
        with open(sent_file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def mark_file_sent(sent_file_path: Path, filename: str):
    """Mark a file as sent by appending to the sent files list."""
    with open(sent_file_path, 'a') as f:
        f.write(f"{filename}\n")


async def send_json_files(json_dir: str = None, json_file: str = None, max_concurrent: int = 20) -> Tuple[int, int]:
    """Send JSON files to API endpoint concurrently.

    Args:
        json_dir: Directory containing JSON files to send
        json_file: Single JSON file to send
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Tuple of (success_count, error_count)
    """
    endpoint_url = config.EVENT_RECEIVER_URL
    if not endpoint_url:
        raise ValueError("No EVENT_RECEIVER_URL configured")

    if json_file:
        # Single file mode
        json_path = Path(json_file)
        if not json_path.exists() or not json_path.is_file():
            raise ValueError(f"File {json_file} does not exist")

        # Create sent_file_path in the same directory as the single file
        sent_file_path = json_path.parent / ".sent_files.txt"
        sent_files = load_sent_files(sent_file_path)

        # Check if the file has already been sent
        if json_path.name in sent_files:
            logging.info(f"File {json_path.name} has already been sent")
            return 0, 0

        json_files = [json_path]
    else:
        # Directory mode
        json_path = Path(json_dir)
        if not json_path.exists() or not json_path.is_dir():
            raise ValueError(f"Directory {json_dir} does not exist")

        sent_file_path = json_path / ".sent_files.txt"
        sent_files = load_sent_files(sent_file_path)

        json_files = list(json_path.glob("*.jsonl"))
        if not json_files:
            logging.info(f"No JSON files found in {json_dir}")
            return 0, 0

        # Filter out already sent files
        json_files = [f for f in json_files if f.name not in sent_files]
        if not json_files:
            logging.info(f"All JSON files in {json_dir} have already been sent")
            return 0, 0

        logging.info(f"Found {len(json_files)} unsent files")

    success_count = 0
    error_count = 0

    async with httpx.AsyncClient() as client:
        for json_file_path in json_files:
            try:
                events = []
                with open(json_file_path, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            try:
                                event_data = json.loads(line)
                                events.append((line_num, event_data))
                            except json.JSONDecodeError as e:
                                logging.error(f"Invalid JSON on line {line_num} in {json_file_path.name}: {e}")
                                error_count += 1

                # Send events concurrently with limited concurrency
                semaphore = asyncio.Semaphore(max_concurrent)  # Limit concurrent requests

                async def send_with_semaphore(event_data, sem):
                    async with sem:
                        return await send_event(client, endpoint_url, event_data)

                tasks = [
                    send_with_semaphore(event_data, semaphore)
                    for line_num, event_data in events
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    line_num = events[i][0]
                    if isinstance(result, Exception):
                        logging.error(f"Failed to send line {line_num}: {json_file_path.name}")
                        error_count += 1
                    elif result:
                        logging.debug(f"Successfully sent line {line_num}: {json_file_path.name}")
                    else:
                        logging.error(f"Failed to send line {line_num}: {json_file_path.name}")
                        error_count += 1

                logging.info(f"Successfully processed: {json_file_path.name}")
                if sent_file_path:
                    mark_file_sent(sent_file_path, json_file_path.name)
                success_count += 1

            except Exception as e:
                logging.error(f"Error processing {json_file_path.name}: {e}")
                error_count += 1

    return success_count, error_count
