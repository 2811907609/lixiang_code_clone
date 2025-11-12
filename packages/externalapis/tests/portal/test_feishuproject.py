import pytest
from externalapis.portal.client import PortalClient
from tests.test_config import Config

config = Config()

_client = PortalClient(config.PORTAL_BASE_URL, config.PORTAL_TOKEN)


@pytest.mark.asyncio
async def test_get_work_item_fields():
    project_key = 'vsm'
    item_type_key = '65a0a51458158fc74f1c2baa'  # sr
    result = await _client.feishu_project.get_work_item_fields(
        project_key, item_type_key)
    print(f'result.......{result}')


@pytest.mark.asyncio
async def test_get_all_item_types():
    project_key = 'vsm'
    result = await _client.feishu_project.get_all_item_types(project_key)
    print(f'result.......{result}')


async def test_create_work_item():
    project_key = 'vsm'
    userKey = '6979392816912810012'  # userKey of zhangxudong
    data = dict(
        work_item_type_key='65a0a51458158fc74f1c2baa',  # sr
        # template_id='123', # template_id is not required
        name='hello1',
        field_value_pairs=[],
    )
    result = await _client.feishu_project.create_work_item(
        project_key, userKey, data)
    print(f'result.......{result}')
