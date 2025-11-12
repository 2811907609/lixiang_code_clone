from inference_server.utils import ipython  # noqa

from inference_server.testhelper import (
    reproduce_by_completion_id,
    reproduce_completion_id_by_lpai_service,
)


async def test_fim_token_in_prompt():
    completion_id = 'cmpl-3bfcd93e-e85d-40e1-ba30-eb75ac9d1a07'
    await reproduce_by_completion_id(completion_id)


# await test_fim_token_in_prompt() # noqa


def test_reproduce_completion_id_by_lpai_service():
    completion_id = 'cmpl-61ddf1ad-53cf-4c06-85fb-019024054aa2'
    service_name = 'vllm-codellama7b-a100-loras'
    res = reproduce_completion_id_by_lpai_service(service_name, completion_id)
    print(res)


# test_reproduce_completion_id_by_lpai_service()
