from typing import Any, Dict

import httpx

from .feishuproject import FeishuProjectResource


class PortalClient:

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        headers = {
            'Authorization': f'Token {token}',
        }
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers)

        self.feishu_project = FeishuProjectResource(self)

    async def _post(self, url, json: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = await self.client.post(url, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"API request failed with status {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise Exception(f"Request error: {str(e)}") from e

    async def _get(self, url) -> Dict[str, Any]:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"API request failed with status {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise Exception(f"Request error: {str(e)}") from e

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
