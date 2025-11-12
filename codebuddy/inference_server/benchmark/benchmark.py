import asyncio
import os
import random
import time
from datetime import datetime
from itertools import product

from pkg.codebuddy import BaseModel, feature_gate, get_llm
from pkg.codebuddy.load_model import load_model_by_instance
from pkg.telemetry.event import collect_benchmark
from pkg.types import BenchmarkItem, UsageInfo

from .dummy_tokenizer import Dummytokenizer


def get_tokenizer(m: BaseModel):
    if 'TokenizerGroup' in str(type(m.tokenizer)):
        return m.tokenizer.tokenizer
    return m.tokenizer


def gen_test_prompt(tokenizer, length):
    if isinstance(tokenizer, Dummytokenizer):
        return 'a' * length
    result = ''
    vocabs = list(tokenizer.get_vocab().keys())
    for _ in range(0, length):
        random_index = random.randint(0, len(vocabs) - 1)
        result += vocabs[random_index]
    return result


async def benchmark(iterations,
                    input_len=128,
                    max_tokens=128,
                    use_dummy=False) -> BenchmarkItem:
    m = get_llm()
    if use_dummy:
        if not hasattr(m, 'old_tokenizer'):
            m.old_tokenizer = m.tokenizer
        m.tokenizer = Dummytokenizer()

    tokenizer = get_tokenizer(m)
    prompt = gen_test_prompt(tokenizer, input_len)
    print('tokenizer prompt length', len(prompt))
    print('tokenizer ids length', len(m.tokenizer.encode(prompt)))
    print('tokenizer ids length', m.tokenizer.encode(prompt)[:400])

    tasks = []
    starttime = time.time()
    for _ in range(0, iterations):
        task = asyncio.create_task(
            m.code_complete_v2('', prompt, '', max_tokens=max_tokens, stop=[]))
        tasks.append(task)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    walltime_duration = time.time() - starttime

    valid_results = []
    for r in results:
        if isinstance(r, Exception):
            print('get exception: ', r)
            continue
        valid_results.append(r)

    total_completion_tokens = 0
    total_duration = 0
    for r in valid_results:
        usage: UsageInfo = r.usage
        # 这里算TPS只算生成的新tokens
        total_completion_tokens += usage.completion_tokens
        total_duration += usage.duration_sec
    if len(valid_results) == 0:
        return None

    benchmark_infos = BenchmarkItem(
        runtime_info=m.runtime_info(),
        benchmark_time=datetime.now().isoformat(),
        input_len=input_len,
        iterations=iterations,
        max_new_tokens=max_tokens,
        total_completion_tokens=total_completion_tokens,
        walltime_duration=walltime_duration,
        tokens_per_second=total_completion_tokens / walltime_duration,
        latency_sec=total_duration / len(valid_results),
        use_dummy_tokenizer=use_dummy,
    )
    return benchmark_infos


async def run_benchmark(instance,
                        iterations=5,
                        input_len=None,
                        max_tokens=None,
                        use_dummy=False,
                        **kwargs):
    feature_gate.benchmark = True
    instance_config, _ = load_model_by_instance(instance)

    modelsize = instance_config.model_labels.get('size', '')
    modelpath = instance_config.model_path
    modeltype = instance_config.model_type
    modelname = os.path.basename(modelpath.strip('/'))
    epoch = time.time()
    baseinfo = {
        'epoch': int(epoch),
        'modeltype': modeltype,
        'modelpath': modelpath,
        'modelname': modelname,
        'modesize': modelsize,
    }
    max_tokens_list = [64, 128, 256, 512]
    input_len_list = [64, 256]
    for i in range(7):
        input_len_list.append(500 * i)

    if input_len:
        input_len_list = [input_len]
    if max_tokens:
        max_tokens_list = [max_tokens]

    all_cases = product(max_tokens_list, input_len_list)
    for _, case in enumerate(all_cases):
        args = {
            'max_tokens': case[0],
            'input_len': case[1],
            'use_dummy': use_dummy,
        }
        info = await benchmark(iterations, **args)
        if not info:
            continue
        # info |= baseinfo
        info = info.model_copy(update=baseinfo)
        print('benchmark info:', info)
        await collect_benchmark(info)


class Benchmark:

    async def run(self, config=None, instance=None, iterations=5):
        '''
        这个函数加载一个配置文件，并根据配置文件中的设置运行一个基准测试。

        参数:
        config (str): 配置文件的路径。
        instance (str): 要运行的基准测试的实例的名称。


        返回:
        None: 如果配置文件中没有指定的实例，或者配置文件为空。
        '''
        await run_benchmark(instance, iterations=iterations, no_save=False)
