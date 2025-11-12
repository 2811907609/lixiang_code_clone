import subprocess
from typing import Optional


def get_origin() -> Optional[str]:
    """
    Get the origin URL of the current git repository by calling git command.

    Returns:
        Optional[str]: The origin URL if successful, None otherwise.
    """
    try:
        # Execute git command to get the origin URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        # Strip any trailing newline characters
        origin_url = result.stdout.strip()
        return origin_url
    except Exception as e:
        print(f"Error getting origin URL: {e}")
        return None
