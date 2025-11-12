from typing import Any

import aiohttp
from Levenshtein import distance

from inference_server.types import BenchmarkItem, CompletionResponse
from inference_server.utils import random_uuid

_prompt_and_response_endpoint = 'https://portal-k8s-staging.ep.chehejia.com/webhook-receiver/v1.0/invoke/webhook-receiver/method/webhook-receiver?uuid=57228971-c093-498f-b168-4a49130eb277&name=llm-prompt-params'

_session = None


def _get_session():
    global _session
    if not _session:
        _session = aiohttp.ClientSession()
    return _session


async def send_event(payload: dict):
    session = _get_session()
    try:
        async with session.post(_prompt_and_response_endpoint,
                                json=payload) as response:
            if response.status != 200:
                print(f'Failed to send event: {payload}')
            else:
                print(f'Successfully sent event: {payload}')
    except Exception as e:
        print(f'Failed to send event: {e}')


_prompt_and_response_category = 'prompt_and_response'


async def collect_prompt_and_response(id: str, completion: CompletionResponse):
    session = _get_session()
    payload = dict(
        id=id,
        category=_prompt_and_response_category,
        data=completion.model_dump(),
    )
    try:
        async with session.post(_prompt_and_response_endpoint,
                                json=payload) as response:
            if response.status != 200:
                print(f'failed to send event, status code {response.status}')
            else:
                print('event sent successfully')
    except Exception as e:
        print(f'failed to send event, {e}')


_fulledit_category = 'fulledit'

async def collect_fulledit(id: str, data: Any):
    session = _get_session()
    response = data.get('response', {})
    choices = response.get('choices')
    if choices:
        output_text = choices[0].get('text', '')
    else:
        output_text = ''
    original_draft_text = data.get('original_draft_text', '')
    output_distance = distance(original_draft_text, output_text)
    max_length = max(len(original_draft_text), len(output_text))
    if max_length > 0:
        change_ratio = output_distance / max_length
        data['change_ratio'] = change_ratio
    else:
        data['change_ratio'] = 0.0
    payload = dict(
        id=id,
        category=_fulledit_category,
        data=data,
    )
    try:
        async with session.post(_prompt_and_response_endpoint,
                                json=payload) as response:
            if response.status != 200:
                print(f'failed to send event, status code {response.status}')
            else:
                print('event sent successfully')
    except Exception as e:
        print(f'failed to send event, {e}')


_benchmark_category = 'benchmark'


async def collect_benchmark(item: BenchmarkItem):
    item_id = random_uuid()
    payload = dict(
        id=item_id,
        category=_benchmark_category,
        data=item.model_dump(),
    )
    await send_event(payload)
