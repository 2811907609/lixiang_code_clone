from pathlib import Path

import pandas as pd
from commonlibs.encoding import yaml_load_dir
from datautils.pandas import df_from_sql_if_not_exists
from repoutils.git.repo import GitRepo

from inference_server.backend.models.fulledit_utils import (
    extract_draft_from_prompt,
)
from inference_server.backend.models.zed import gen_edit_prediction_prompt
from inference_server.envs import config

_script_model = bool(globals().get('__file__'))
_dataset_dir = Path(__file__).parent / 'datasets'


def create_dataset_from_repo(repo_dir,
                             exts=None,
                             min_lines: int = None,
                             max_lines: int = None):
    repo = GitRepo(repo_dir)
    if exts:
        exts = exts.split(',')
    files = repo.get_all_managed_files(exts=exts)

    dataset = []
    id = 1
    for file in files:
        with open(f"{repo_dir}/{file}", 'r') as f:
            lines = f.readlines()
            if (min_lines is not None and
                    len(lines) < min_lines) or (max_lines is not None and
                                                len(lines) > max_lines):
                continue
            dataset.append(
                pd.Series({
                    'id': id,
                    'file_path': file,
                    'content': ''.join(lines)
                }))
            id += 1

    df = pd.DataFrame(dataset)
    return df


def load_local_dataset(min_len=1000):
    arrs = yaml_load_dir(_dataset_dir)
    arr = []
    for el in arrs:
        arr.extend(el)
    arr = [{**v, 'id': i + 1} for i, v in enumerate(arr)]
    df = pd.DataFrame(arr)
    if min_len:
        df = df[df.input.str.len() > min_len]
    df = df.rename(columns={'original_text': 'content'})
    return df


def load_instruct_coder():
    from datasets import load_dataset

    ds = load_dataset("likaixin/InstructCoder")['validation']
    df = ds.to_pandas()
    df = df.reset_index().rename(columns={"index": "id"})
    df = df.rename(columns={'input': 'content', 'instruction': 'task'})
    return df


def sql_load_fulledit_online_data():
    return """
SELECT id,
	GET_JSON_OBJECT(data, '$.input_events') as input_events,
	GET_JSON_OBJECT(data, '$.input_excerpt') as input_excerpt,
	GET_JSON_OBJECT(data, '$.response.choices[0].text') as output,
	GET_JSON_DOUBLE(data, '$.response.usage.duration_sec') * 1000 as duration_ms
FROM (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY data_created, id) as rn
    FROM ep_sr_ods.ods_codebuddy_final_prompt_params
    WHERE true
        AND category = 'fulledit'
        AND GET_JSON_OBJECT(data, '$.response') IS NOT NULL
        AND GET_JSON_OBJECT(data, '$.original_draft_text') IS NOT NULL
        AND data_created >= UNIX_TIMESTAMP('2025-06-20')
        AND data_created < UNIX_TIMESTAMP('2025-07-25')
) t
WHERE rn % 10 = 1  -- 取第1, 11, 21, 31... 条记录
ORDER BY data_created limit 1000;
"""


def load_fulledit_online_data():
    sql = sql_load_fulledit_online_data()
    df = df_from_sql_if_not_exists(sql, sc_uri=config.starrocks_uri)
    df['prompt'] = df.apply(lambda row: gen_edit_prediction_prompt(
        row['input_events'],
        row['input_excerpt'],
    ), axis=1)
    df['draft'] = df.apply(lambda row: extract_draft_from_prompt(
        row['input_excerpt'],
    ), axis=1)
    return df

def create_dataset(repo_dir,
                   exts=None,
                   min_lines: int = None,
                   max_lines: int = None,
                   outfile=None):
    if repo_dir == 'yamltask':
        df = load_local_dataset()
        outfile = 'builtinyaml.parquet'
    elif repo_dir == 'instructcoder':
        df = load_instruct_coder()
        outfile = 'instructcoder.parquet'
    elif repo_dir == 'fulledit_online':
        df = load_fulledit_online_data()
        outfile = 'fulledit_online.parquet'
    else:
        df = create_dataset_from_repo(repo_dir, exts, min_lines, max_lines)

    if outfile:
        df.to_parquet(outfile)

    if _script_model:
        return None

    return df


if __name__ == '__main__':
    import fire

    cmds = dict(create_dataset=create_dataset)
    fire.Fire(cmds)
'''

uv run inference_server/modules/specedit/dataset.py create_dataset ~/code/li/ep-service-clean \
        --exts=go --min_lines 200 --max_lines 500 --outfile dataset_spec_edit.parquet


'''
