from .ep_lpai_service import completion_by_lpai


def test_completion_by_lpai():
    res = completion_by_lpai('vllm-codellama7b-a100-loras',
                             language='python',
                             prefix='def quicksort',
                             suffix='\n\treturn arr',
                             max_tokens=100)
    print('response', res)
