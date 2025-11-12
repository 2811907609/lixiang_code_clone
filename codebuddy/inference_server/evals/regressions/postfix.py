import arrow
import pandas as pd

from inference_server.types import PromptComposeInfo, CompletionResponse, CompletionResponseChoice
from inference_server.data.starrocks import load_starrocks_if_not_exists
from inference_server.envs import Config
from inference_server.codebuddy.postprocess import fix_output
from datautils.pandas import df_to_parquet, parquet_to_df


def _dump_sql(date, limit=6000, accepted_only=False):
    accepted_only_clause = ''
    if accepted_only:
        accepted_only_clause = ' AND accepted '
    s = f'''
WITH t as (
    SELECT '{date}' as start_date
),
t_llm as (
    SELECT GET_JSON_STRING(data, '$.id') as comp_id
            ,GET_JSON_STRING(data, '$.choices[0].text') as output_text
            ,GET_JSON_STRING(data, '$.usage.prompt_compose_info.used_prefix') as used_prefix
            ,GET_JSON_STRING(data, '$.usage.prompt_compose_info.used_suffix') as used_suffix
    FROM ep_sr_ods.ods_codebuddy_final_prompt_params,t
    WHERE category = 'prompt_and_response'
        and data_created >= UNIX_TIMESTAMP(t.start_date)
        and length(GET_JSON_STRING(data, '$.choices[0].text')) > 0
),
t_accepted as (
    SELECT GET_JSON_OBJECT(details, '$.id') as comp_id
    FROM ep_sr_ods.ods_event event,t
    WHERE event.time >= UNIX_TIMESTAMP(t.start_date) * 1000
        AND event.name in ('copilot:completion-accepted')
        AND event.platform_family in ('VS Code')
        AND event.plugin_channel in ('alpha', 'stable', 'beta')
        -- AND GET_JSON_OBJECT(event.details, '$.lang') in ('go', 'python', 'c', 'cpp','typescript', 'javascript', 'jsx', 'tsx')
    GROUP BY 1
),
t_result as (
    SELECT t_llm.*
        ,(t_accepted.comp_id is not null) as accepted
    FROM t_llm LEFT JOIN t_accepted ON t_llm.comp_id = t_accepted.comp_id
)
SELECT * FROM t_result
WHERE true
{accepted_only_clause}
LIMIT {limit}
'''
    return s


def dump_cases(start_date: str = None,
               cache_filename: str = None,
               limit=6000,
               accepted_only=False):
    if not start_date:
        start_date = arrow.now().shift(days=-20).format('YYYY-MM-DD')
    sql = _dump_sql(start_date, limit=limit, accepted_only=accepted_only)
    config = Config()
    df = load_starrocks_if_not_exists(sql, config.starrocks_uri, cache_filename)
    return df


def regression_one(row):
    prompt = PromptComposeInfo(used_prefix=row.used_prefix,
                               used_suffix=row.used_suffix)
    choice = CompletionResponseChoice(index=0, text=row.output_text)
    completion = CompletionResponse(choices=[choice], model='')
    fix_output(prompt, completion)
    return pd.Series(
        [choice.text, (choice.choice_info or dict()).get('fix_kinds')])


def regression(df):
    df['fixed_out'] = df.apply(regression_one, axis=1)
    return df


def run(start_date: str = None,
        filename: str = None,
        accepted_only: bool = False):
    if not start_date:
        start_date = arrow.now().shift(days=-20).format('YYYY-MM-DD')
    if not filename:
        if accepted_only:
            filename = f'regression_postfix_accept_{start_date}.parquet'
        else:
            filename = f'regression_postfix_{start_date}.parquet'
    df = dump_cases(start_date, filename, accepted_only=accepted_only)
    df = regression(df)
    outfile = f'out_{filename}'
    df_to_parquet(df, outfile)


def analyze(df_file):
    df = parquet_to_df(df_file)
    accepted_df = df[df.accepted.apply(bool)]
    diff_df = df[df.fixed_out != df.output_text]
    trimmed_df = diff_df[df.fixed_out != '']
    accepted_trimmed_df = trimmed_df[trimmed_df.accepted.apply(bool)]
    print(
        f'total: {len(df)}, accepted: {len(accepted_df)}, diff count: {len(diff_df)}, trimmed and not empty: {len(trimmed_df)}, accepted: {len(accepted_trimmed_df)}'
    )
    print(diff_df[['comp_id', 'accepted', 'fixed_out', 'output_text']])
    print('trimmed df \n',
          trimmed_df[['comp_id', 'accepted', 'fixed_out', 'output_text']])
    for row in trimmed_df[['comp_id', 'fixed_out', 'output_text']].itertuples():
        print('compid: ', row.comp_id)
        print(f'fixed_out: {row.fixed_out}')
        print(f'output_text: {row.output_text}')


if __name__ == '__main__':
    import fire

    # Configure Pandas to show all columns and rows
    pd.set_option('display.max_rows', None)  # Display all rows
    pd.set_option('display.max_columns', None)  # Display all columns
    pd.set_option('display.max_colwidth', None)  # Display full column width

    cmds = dict(dump=dump_cases, run=run, analyze=analyze)
    fire.Fire(cmds)
