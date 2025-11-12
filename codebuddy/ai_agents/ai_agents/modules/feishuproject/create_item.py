import json
import logging

from smolagents import CodeAgent, OpenAIServerModel, tool

from externalapis.portal.client import PortalClient

import ai_agents.modules.otel.phoenix  # noqa
from ai_agents.config import config

logging.basicConfig(level=logging.DEBUG)

_portal_client = PortalClient(config.PORTAL_BASE_URL, config.PORTAL_TOKEN)

_project = 'vsm'
_user_key = '6979392816912810012'  # zhangxudong
_sr_type_id = '65a0a51458158fc74f1c2baa'
_ar_type_id = '65a0b332091743b58a1f6108'

_ir = 5820509913

_openai_model = OpenAIServerModel(
    api_base=config.LLM_API_BASE,
    model_id='deepseek-v3',
    api_key=config.LLM_API_KEY,
)

_prompt_parse_text = '''
请将以下需求列表转换为格式良好的JSON数组格式，遵循以下规则：
2. 优先级标记（如P0）应该被忽略
3. 输出格式应为：
[
  {'type': '需求类型', 'title': '需求标题'},
  ...
]
4. 保持原始需求的顺序
5. 如果需求前面有 AR 或 SR 前缀，请在 title 里面去掉该前缀
6. 需求类型只保留'SR'或'AR'部分（去掉冒号）
7. title 里面如果有不适合放在title里面的内容，可以去掉或者帮忙改写优化
8. AR 嵌套放在 SR 里面，使用 children 作为 key

示例输入：
SR：构建全文投机编辑性能评测集
AR：性能评测方案
AR：性能评测数据集生产（可以复用模型训练数据集） P0

示例输出：
{
    "type": "SR",
    "title": "构建全文投机编辑性能评测集",
    "children": [
        {"type": "AR", "title": "性能评测方案"},
        {"type": "AR", "title": "性能评测数据集生产"}
    ]
}
'''


def parse_items_from_text(text: str):
    '''将需求文本解析为JSON数组格式

    Args:
        text (str): 包含多个需求的文本

    Returns:
        list: 包含解析后需求的JSON数组
    '''
    if not text:
        return None

    # 使用模型解析文本
    messages = [{
        'role': 'system',
        'content': _prompt_parse_text
    }, {
        'role': 'user',
        'content': text
    }]
    response = _openai_model(messages=messages, max_tokens=1000, temperature=0)

    # 尝试直接解析
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        pass

    return None


async def get_item_type_key(item_type: str):
    item_types = await _portal_client.feishu_project.get_all_item_types(
        _project,)
    types = []
    for t in item_types:
        if t.get('is_disable') == 2:
            types.append({
                'api_name': t['api_name'],
                'name': t['name'],
                'type_key': t['type_key']
            })
    if not types:
        return None
    types_str = json.dumps(types, indent=2)
    _prompt = f'''
下面是 item type 的列表，请根据 type 名字返回匹配的 type_key
<JSON_DATA>
{types_str}
</JSON_DATA>

注意
1. 名字可能匹配 name 或者 api_name
2. 名字可能不完全匹配，请返回表达意思一样的条目
3. 请仅返回 item_type 对应的字符串，不要有任何其他信息
4. 如何没有匹配的结果，请返回NULL
'''

    messages = [{
        'role': 'system',
        'content': _prompt
    }, {
        'role': 'user',
        'content': f'name: {item_type}'
    }]
    response = _openai_model(messages=messages, max_tokens=100, temperature=0)

    response = response.strip(' "')
    if not response:
        return None
    if response.upper() == 'NULL':
        return None

    return response


async def create_sr_item(name: str, priority: str = None):
    field_value_pairs = [{
        'field_key': 'field_75e210',
        'field_value': [{
            'value': 'f0gzirwh8',
        }],
    }, {
        'field_key': 'business',
        'field_value': '65a8ad2dedb589130731d65f',
    }, {
        'desc': '关联项目 copilot RD',
        'field_key': 'field_f4700e',
        'field_value': [3002936011],
    }, {
        'desc': '关联IR',
        'field_key': 'field_11979c',
        'field_value': [_ir],
    }, {
        'field_key': 'role_owners',
        'field_value': [],
    }]

    item = {
        'work_item_type_key': _sr_type_id,
        'name': name,
        'field_value_pairs': field_value_pairs,
    }
    return await _portal_client.feishu_project.create_work_item(
        _project, _user_key, item)


async def create_ar_item(name: str, related_sr: int):
    field_value_pairs = [
        {
            'desc': '需求交付周期',
            'field_key': 'field_45de0b',
            'field_value': [{
                'value': 'zqeppttrx'
            }]
        },
        {
            'desc': '关联SR',
            'field_key': 'field_4faee0',
            'field_value': [related_sr]
        },
        {
            'desc': '关联IR',
            'field_key': 'field_168d24',
            'field_value': [_ir]
        },
        {
            'field_key': 'business',
            'field_value': '65a8ad2dedb589130731d65f'  # copilot
        },
        {
            'desc': '关联项目 copilot RD',
            'field_key': 'field_1603a2',
            'field_value': [3002936011]
        },
        {
            'field_key': 'role_owners',
            'field_value': []
        }
    ]

    item = {
        'work_item_type_key': _ar_type_id,
        'name': name,
        'template_id': 787134,  # 技术需求
        'field_value_pairs': field_value_pairs,
    }
    return await _portal_client.feishu_project.create_work_item(
        _project, _user_key, item)


# this cannot be async since smolagents do not support async ATM
async def _create_sr_and_ars(sr: dict):
    if not (sr and sr['title']):
        print('no valid sr, sr:', sr)
        return
    sr_item = await create_sr_item(sr['title'])
    print('sr_item:', sr_item, type(sr_item))
    for ar in sr['children']:
        ar_title = ar['title']
        if not ar_title:
            print('no valid ar, ar:', ar)
            continue
        ar_item = await create_ar_item(ar_title, sr_item)
    print('ar_item:', ar_item, type(ar_item))


@tool
def create_sr_and_ars(sr: dict) -> None:
    """
    根据提供的 SR 和 AR 信息创建 SR 和相关的 AR。
    每次只能创建一个SR 以及关联的多个AR。
    如果标题里面有优先级，如P1，请从标题中去掉优先级。

    Args:
        sr: 包含 SR 和 AR 信息的字典，格式为：
            {
                "type": "SR",
                "title": "SR 标题",
                "children": [
                    {"type": "AR", "title": "AR 标题"},
                    ...
                ]
            }

    Returns:
        None
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_create_sr_and_ars(sr))


code_agent = CodeAgent(
    tools=[create_sr_and_ars],
    model=_openai_model,
    additional_authorized_imports=['asyncio'],
)
