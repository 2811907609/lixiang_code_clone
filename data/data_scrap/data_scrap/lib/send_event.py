from typing import Any, Dict

import httpx


async def send_event(client: httpx.AsyncClient, endpoint_url: str, event_data: Dict[str, Any]) -> bool:
    """Send event data to API endpoint asynchronously.

    Args:
        client: httpx async client
        endpoint_url: API endpoint URL
        event_data: Event data to send

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = await client.post(
            endpoint_url,
            json=event_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception:
        return False
