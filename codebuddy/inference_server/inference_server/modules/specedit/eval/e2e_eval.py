# ruff: noqa: E402  # Module level import not at top of file
import os
import time
from typing import Tuple

import arrow
import Levenshtein
import pandas as pd
import inference_server.utils.ipython  # noqa: F401

from datautils.pandas import df_to_parquet, parquet_to_df

from inference_server.evalhelper.report import distribution_report
from inference_server.modules.specedit.lib import (
    disable_ngram_spec,
    disable_spec_edit,
    enable_ngram_spec,
    enable_spec_edit,
)
from inference_server.utils import getLogger

_script_model = bool(globals().get('__file__'))
logger = getLogger(__name__)

today_str = arrow.now().to('Asia/Shanghai').format('YYYYMMDD')


def prompt_template(code: str):
    now = arrow.now().isoformat()
    # add a now time to avoid prefix cache, it may not need since I disabled prefix cache, add it to assure
    return f'''Now time is {now}.
Please refactor the following code. Your task is to add `EP_` prefix to each function.

The code to be modified is enclosed within the `<code_start>` and `<code_end>` tags:

<code_start>
{code}
<code_end>

It is crucial that you return the **entire** modified code, from the very beginning to the very end.  Your response should consist **solely** of the modified code. Do not include any introductory or concluding sentences, explanations, or any text other than the code itself.

Return the complete, modified code here:
'''


def gen_prompt_messages(row):
    code_content = row['content']
    prompt = prompt_template(code_content)
    messages = [
        dict(role='user', content=prompt),
    ]
    return messages


async def regression_one_fulledit(row,
                               model_name: str = 'default',
                               enable_spec_edit: bool = False):
    from inference_server.backend import get_llm

    llm = get_llm()
    start_time = time.perf_counter()

    # For fulledit cases, use raw_generate with input_events and input_excerpt
    params = dict(
        max_tokens=1500,
        temperature=0,
        input_events=row['input_events'],
        input_excerpt=row['input_excerpt'],
        original_draft_text=row['draft'],
    )

    if enable_spec_edit and 'draft' in row:
        params['original_draft_text'] = row['draft']

    res = await llm.raw_generate(
        None,  # prompt is generated inside raw_generate for fulledit
        **params
    )
    output_text = res.choices[0].text
    usage = res.usage.model_dump()
    duration_sec = time.perf_counter() - start_time
    usage['duration_sec'] = duration_sec
    result = dict(output_text=output_text, usage=usage)
    return result


async def regression_one(row,
                         model_name: str = 'default',
                         enable_spec_edit: bool = False):
    from inference_server.backend import get_llm

    # Check if this is a fulledit case by looking for fulledit-specific columns
    if 'input_events' in row and 'input_excerpt' in row:
        return await regression_one_fulledit(row, model_name, enable_spec_edit)

    messages = gen_prompt_messages(row)
    code_content = row['content']
    llm = get_llm()
    start_time = time.perf_counter()
    chat_params = dict(max_tokens=10000, temperature=0, stream=False)
    # chat_params = dict(max_tokens=100, temperature=0, stream=False)
    if enable_spec_edit:
        chat_params['original_draft_text'] = code_content
    generator = llm.chat_complete(
        messages,
        **chat_params,
    )
    output_text, usage = await anext(generator)
    duration_sec = time.perf_counter() - start_time
    usage['duration_sec'] = duration_sec
    result = dict(output_text=output_text, usage=usage)
    return result


async def regression(df, model_name='default', enable_spec_edit=False):
    rows = []
    for index, row_ in df.iterrows():
        print(f'running the {index+1} case======================')
        row = row_.to_dict()
        result = await regression_one(row,
                                      model_name,
                                      enable_spec_edit=enable_spec_edit)
        row['eval_result'] = result
        rows.append(pd.Series(row))
    return pd.DataFrame(rows)


async def run(
    filename: str = None,
    outfile: str = None,
    spec_edit: bool = False,
    model_name: str = 'default',
    speculative_model: str = None,
    instance: str = None,
    config_path: str = None,
    limit=None,
    num_speculative_tokens=None,
):

    case_df = parquet_to_df(filename)
    if limit:
        case_df = case_df.head(limit)
        print(f'will run {len(case_df)} cases')

    if instance:
        # put it here to fast startup time of analyze (vllm loading is slow, analyze do not need it)
        from inference_server.backend import load_model_by_instance

        await load_model_by_instance(
            instance=instance,
            config_path=config_path,
            max_model_len=11000,  # set a large max_model_len
            enable_spec_edit=spec_edit,
            speculative_model=speculative_model,
            num_speculative_tokens=num_speculative_tokens)

    # warmup
    await regression(case_df.head(3),
                     model_name,
                     enable_spec_edit=enable_spec_edit)

    out_df = await regression(case_df,
                              model_name,
                              enable_spec_edit=enable_spec_edit)
    if outfile:
        df_to_parquet(out_df, outfile)
    if _script_model:
        return None
    return out_df


async def online_diff(
    filename: str = None,
    model_name: str = 'default',
    gpu_memory_utilization: float = None,
    limit=None,
    instance: str = None,
    config_path: str = None,
    model_path: str = None,
    num_speculative_tokens=None,
    skip_no_spec: bool = False,
    skip_warm_up: bool = False,
    skip_ngram: bool = False,
    out_model_name: str = None,
):
    case_df = parquet_to_df(filename)
    if limit:
        case_df = case_df.head(limit)
    if instance:
        # put it here to fast startup time of analyze (vllm loading is slow, analyze do not need it)
        from inference_server.backend import get_llm, load_model_by_instance

        m = get_llm()
        if m:
            logger.warning("==llm is already inited==")
        else:
            await load_model_by_instance(
                instance=instance,
                config_path=config_path,
                model_path=model_path,
                max_model_len=11000,  # set a large max_model_len
                enable_spec_edit=True,
                gpu_memory_utilization=gpu_memory_utilization,
                num_speculative_tokens=num_speculative_tokens)

    def save_df(df, type: str) -> str:
        if not out_model_name:
            return None
        if type == 'no_spec':
            outfile = f'out_{today_str}_{out_model_name}_{type}.parquet'
        else:
            outfile = f'out_{today_str}_{out_model_name}_{type}_lookup_{num_speculative_tokens}.parquet'
        df_to_parquet(df, outfile)

    dfs = []
    disable_spec_edit()
    if not skip_warm_up:
        await regression(case_df.head(1), model_name,
                         enable_spec_edit=False)  # warmup

    if not skip_ngram:
        ngram_out_df = await regression(case_df,
                                        model_name,
                                        enable_spec_edit=False)
        dfs.append((ngram_out_df, '_ngram'))
        save_df(ngram_out_df, 'ngram')

    enable_spec_edit()
    enable_ngram_spec()
    specedit_out_df = await regression(case_df,
                                       model_name,
                                       enable_spec_edit=True)
    dfs.append((specedit_out_df, '_specedit'))
    save_df(specedit_out_df, 'specedit')

    if not skip_no_spec:
        print('============================== no spec')
        disable_ngram_spec()
        nospec_out_df = await regression(case_df,
                                         model_name,
                                         enable_spec_edit=False)
        dfs.append((nospec_out_df, '_nospec'))
        save_df(nospec_out_df, 'no_spec')

    return analyze_df(dfs)


def format_df_for_analyze(df: pd.DataFrame):

    def process_row(row):
        eval_result = row.eval_result
        output = eval_result['output_text']
        usage = eval_result['usage']
        output_stat = usage['output_stat']
        draft = ''
        if hasattr(row, 'draft'):
            draft = row.draft
        else:
            draft = row.content
        edit_distance = Levenshtein.distance(draft, output)
        completion_tokens = usage['completion_tokens']
        duration = usage['duration_sec']
        tps = completion_tokens / duration

        return pd.Series({
            'id': row.id,
            'content_len': len(draft),
            'output_len': len(output),
            'distance': edit_distance,
            'prompt_tokens': usage['prompt_tokens'],
            'completion_tokens': completion_tokens,
            'first_token_latency': output_stat['first_token_latency'],
            'per_token_time': output_stat['per_token_time'],
            'decoding_steps': usage.get('decoding_steps', -1),
            'duration': duration,
            'tps': tps,
        })

    return df.apply(process_row, axis=1).dropna().reset_index(drop=True)


def analyze_df(dfs: list[Tuple[pd.DataFrame, str]], max_prompt_tokens=7000):
    merged_df = None
    for index, (out_df, suffix) in enumerate(dfs):
        out_df = format_df_for_analyze(out_df)
        out_df = out_df[out_df.prompt_tokens <= max_prompt_tokens]
        out_df = out_df.rename(columns={
            col: col + suffix for col in out_df.columns if col not in ['id']
        })
        if index == 0:
            merged_df = out_df
        else:
            merged_df = pd.merge(merged_df,
                                 out_df,
                                 on=['id'],
                                 how='left',
                                 suffixes=('', ''))
    return _report(merged_df)


def analyze(outfiles, max_prompt_tokens=7000, limit=None):
    """max_prompt_tokens: will filter out prompt_tokens >= 7000 content, thus tooooo long"""

    outfiles = outfiles.split(',')
    dfs = []

    for outfile in outfiles:
        col_suffix, _ = os.path.splitext(outfile)
        col_suffix = os.path.basename(col_suffix)
        out_suffix = f'_{col_suffix}'
        print(f'analyzing {outfile}, out_suffix {out_suffix}')
        out_df = parquet_to_df(outfile)
        if limit:
            out_df = out_df.head(limit)
        dfs.append((out_df, out_suffix))
    result_df = analyze_df(dfs, max_prompt_tokens=max_prompt_tokens)
    if _script_model:
        return None
    return result_df


def _report(df):
    agg_column_prefixes = ('content_len', 'output_len', 'prompt_tokens',
                           'completion_tokens', 'decoding_steps', 'distance',
                           'first_token_latency', 'per_token_time', 'duration',
                           'tps')
    report_df = distribution_report(df, column_prefixes=agg_column_prefixes)
    print(report_df.to_string(line_width=None))
    return report_df


if __name__ == '__main__' and _script_model:
    import fire

    cmds = dict(run=run, analyze=analyze)
    fire.Fire(cmds)
