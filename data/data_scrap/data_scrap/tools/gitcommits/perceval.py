import json
import os
import subprocess
from typing import Any, Dict, List, Optional

import arrow


def run_perceval_git(
    origin: str,
    start_datetime: str,
    finish_datetime: str,
    max_size_bytes: int = 1024000,
    no_ssl_verify: bool = True,
    zone: str = None,
    output_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Wrapper function for perceval git command.

    Args:
        origin: Git repository URL
        start_datetime: Start date in ISO format (e.g., "2023-01-01T00:00:00")
        finish_datetime: End date in ISO format (e.g., "2023-12-31T23:59:59")
        max_size_bytes: Maximum size in bytes for git objects (default: 1024000)
        no_ssl_verify: Disable SSL verification (default: True)
        zone: fsd, chip, None
        output_dir: Directory to save JSON commit data for debugging/replay (optional)

    Returns:
        List of dictionaries containing git commit data

    Raises:
        subprocess.CalledProcessError: If perceval command fails
        json.JSONDecodeError: If output is not valid JSON
    """
    cmd = ["perceval", "git"]

    if no_ssl_verify:
        cmd.append("--no-ssl-verify")

    cmd.extend([origin])

    if start_datetime:
        cmd.extend(["--from-date", start_datetime])
    if finish_datetime:
        cmd.extend(["--to-date", finish_datetime])

    cmd.extend([
        "--max-size-bytes", str(max_size_bytes),
        "--json-line"
    ])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse JSON lines output, filtering out log messages
        commits = []
        today = arrow.now('Asia/Shanghai').format('YYYY-MM-DD')

        # Create output directory if specified
        output_file = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            # Create filename based on repo name and timestamp
            repo_name = origin.split('/')[-1].replace('.git', '')
            timestamp = arrow.now('Asia/Shanghai').format('YYYYMMDD_HHmmss')
            output_file = os.path.join(output_dir, f"{repo_name}_{timestamp}.jsonl")

        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line and line.startswith('{'):  # Only process lines that start with JSON
                try:
                    commit_data = json.loads(line)
                    if zone:
                        commit_data['zone'] = zone
                    # Add snapshotOn to data field
                    if 'data' in commit_data:
                        commit_data['data']['snapshotOn'] = today
                    commits.append(commit_data)

                    # Save to file if output_file is specified
                    if output_file:
                        with open(output_file, 'a', encoding='utf-8') as f:
                            json.dump(commit_data, f, ensure_ascii=False)
                            f.write('\n')

                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue

        return commits

    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode,
            e.cmd,
            f"Perceval command failed: {e.stderr}"
        ) from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Failed to parse perceval output as JSON: {e.msg}",
            e.doc,
            e.pos
        ) from e
