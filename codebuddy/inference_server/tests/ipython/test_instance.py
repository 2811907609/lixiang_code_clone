# ruff: noqa: F401

import logging

logging.basicConfig(level=logging.DEBUG)

from inference_server.utils.ipython import enable_auto_reload

enable_auto_reload()

from inference_server.codebuddy import get_llm, load_model_by_instance

# yapf: disable

async def test_instance(instance, config_path=None):
    await load_model_by_instance(instance, config_path=config_path)
    result = await get_llm().code_complete_v2(
        'python', 'def fib(n)', '',
        max_tokens=10, model_name='default')
    print('llm result:\n', result)



#await test_instance('test.opt125m', 'conf/test.json')
#await test_instance('test.opt125m-spec', 'conf/test.json')
await test_instance('prod.dp-6_7B-ep-202406100308-awq-ngram')






async def test_quicksort():
    result = await get_llm().code_complete_v2('python', 'def quicksort(arr):\n', '')
    print('llm result: ', result)

await test_quicksort()


async def test_long_output():
    result = await get_llm().code_complete_v2('', 'write fibonacci sequence till 10000.\n 1 1 2 ', ' finished.')
    print('llm result: ', result)

await test_long_output()


async def test_hello(model_name='default'):
    result = await get_llm().code_complete_v2('', 'hello', '', max_tokens=20, model_name=model_name)
    print('llm result: ', result)

await test_hello('dp-6_7b-ep-0610-awq-ngram')

# yapf: enable
