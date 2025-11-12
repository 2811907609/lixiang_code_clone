from typing import Any, Dict

from .base_resource import BaseResource


class FeishuProjectResource(BaseResource):

    async def get_all_item_types(self, project_key: str) -> list[Dict]:
        path = '/feishuproject/work-item/all-types'
        url = f'{self.base_url}{path}?projectKey={project_key}'
        result = await self.client._get(url)
        return result

    async def create_work_item(self, project_key: str, user_key: str,
                               json: Dict[str, Any]) -> Dict[str, Any]:
        url = f'{self.base_url}/feishuproject/create-work-item?projectKey={project_key}&userKey={user_key}'
        result = await self.client._post(url, json=json)
        return result

    async def get_work_item_fields(self, project_key: str,
                                   item_type_key: str) -> Dict[str, Any]:
        path = '/feishuproject/work-item/all-fields-info'
        url = f'{self.base_url}{path}?projectKey={project_key}&workItemTypeKey={item_type_key}'
        result = await self.client._get(url)
        return result
