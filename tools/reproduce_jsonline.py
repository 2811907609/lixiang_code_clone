import asyncio
import json
import os

import fire
import pandas as pd

if __name__ == '__main__':
    import sys
    directory = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(directory)
    sys.path.append(parent_dir)

from pkg.utils.ipython import is_in_ipython, enable_auto_reload  # noqa

enable_auto_reload()

from pkg.codebuddy import get_and_update_llm, get_llm
from pkg.config.load import InstanceConfig

_model_path = '/lpai/volumes/zxd-code-complete/data/models/ep-models/deepseek-coder-6.7b-instruct_202404020146-merged-awq'

_default_params = {
    'max_logprobs': 10,
    'quantization': 'awq',
    'max_model_len': 4000,
}

_ngram_params = {
    'max_logprobs': 10,
    'quantization': 'awq',
    'max_model_len': 4000,
    'use_v2_block_manager': True,
    'speculative_model': '[ngram]',
    'num_speculative_tokens': 10,
    'ngram_prompt_lookup_min': 1,
    'ngram_prompt_lookup_max': 8
}

_instance_config = {
    'model_type': 'deepseek_coder',
    'disable_register': True,
    'model_labels': {
        'spec': 'ngram',
        'inference_by': 'vllm',
        'device': 'A100'
    },
    'models': {
        'default': {
            'params': {
                'temperature': 0,
                'logprobs': 5,
                'topk_mean_threshold': 0.8,
                'topk_mean_active_ratio': 1
            }
        }
    }
}


def _load_llm(params=_default_params):
    _instance_config['model_path'] = _model_path
    _instance_config['model_params'] = params
    ins = InstanceConfig.from_dict('offline_bench', _instance_config)
    get_and_update_llm(instance_config=ins)


async def reproduce_jsonlines(infile, outfile, limit=None):
    semaphore = asyncio.Semaphore(1)
    tasks = []
    line_result = {}

    async def gen_line(n, line):
        line = json.loads(line)
        prompt = line.get('prompt')
        prompt = json.loads(prompt)
        language = prompt.get('language', '')
        prefix = prompt.get('segments', {}).get('prefix', '')
        suffix = prompt.get('segments', {}).get('suffix', '')
        stop = prompt.get('stop', [])
        temperature = 0

        async with semaphore:
            result = await get_llm().code_complete_v2(language,
                                                      prefix,
                                                      suffix,
                                                      stop=stop,
                                                      temperature=temperature,
                                                      model_name='default')
            line['spec_result'] = result.model_dump()
            line_result[n] = line

    i = 0
    with open(infile, 'r') as f, open(outfile, 'w') as out:
        for line in f:
            tasks.append(asyncio.create_task(gen_line(i, line)))
            i += 1
            if limit and i >= limit:
                break

        if tasks:
            await asyncio.gather(*tasks)

        for j in range(i):
            line = line_result[j]
            out.write(json.dumps(line) + '\n')


# await reproduce_jsonlines(infile='completion-awq-4.29.jsonl', outfile='ngram-out-n8-completion-awq-4.29.jsonl')


def analyze(input_file, limit=None):
    i = 0
    with open(input_file, 'r') as f:
        arr = []
        for line in f:
            line = json.loads(line)
            line['usage'] = json.loads(line['usage'])
            line['result'] = json.loads(line['result'])
            line['prompt'] = json.loads(line['prompt'])
            spec_result = line['spec_result']
            spec_completion_tokens = spec_result['usage']['completion_tokens']
            spec_duration = spec_result['usage']['duration_sec'] * 1000
            spec_result_text = spec_result['choices'][0]['text']
            o = dict(
                id=line['id'],
                model_name=line['model_name'],
                prompt_tokens=line['usage']['prompt_tokens'],
                completion_tokens=line['usage']['completion_tokens'],
                duration=line['duration'],
                result_text=line['result'][0]['text'],
                spec_completion_tokens=spec_completion_tokens,
                spec_duration=spec_duration,
                spec_result_text=spec_result_text,
            )
            arr.append(o)
            if limit and i >= limit:
                break
        return pd.DataFrame.from_dict(arr)


def show_avg_p90(df, columns):
    average = df[columns].mean()
    median = df[columns].median()
    p80 = df[columns].quantile(0.80)
    p90 = df[columns].quantile(0.90)
    p95 = df[columns].quantile(0.95)
    p98 = df[columns].quantile(0.98)
    comparison_df = pd.DataFrame({
        'Mean': average,
        'Median (50th percentile)': median,
        '80th percentile': p80,
        '90th percentile': p90,
        '95th percentile': p95,
        '98th percentile': p98,
    })
    print(comparison_df)


def report(outfile, limit=None):
    df = analyze(outfile, limit=limit)
    show_avg_p90(df, [
        'duration', 'spec_duration', 'completion_tokens',
        'spec_completion_tokens'
    ])


async def online_regression(infile, outfile, limit=None):
    await reproduce_jsonlines(infile=infile, outfile=outfile, limit=limit)
    return report(outfile, limit=limit)


async def offline_regression(infile, outfile, limit=None):
    _load_llm(_ngram_params)
    await reproduce_jsonlines(infile=infile, outfile=outfile, limit=limit)
    report(outfile, limit=limit)


# df = await online_regression(infile='completion-awq-4.29-logprobs.jsonl',
#                         outfile='ngram-out-n8-completion-awq-4.29.jsonl') # , limit=200)

if not is_in_ipython() and __name__ == '__main__':
    cmds = dict(
        offline_regression=offline_regression,
        report=report,
    )
    fire.Fire(cmds)
