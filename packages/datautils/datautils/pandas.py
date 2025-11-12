import logging
import pathlib

import pandas as pd
from commonlibs.encoding import yaml_dump

logger = logging.getLogger(__name__)


def df_to_jsonl(df, target_filename):
    with open(target_filename, 'w') as f:
        f.write(df.to_json(orient='records', lines=True, force_ascii=False))


def df_to_yaml(df, target_filename):
    data_dict = df.to_dict(orient='records')
    with open(target_filename, 'w') as f:
        yaml_dump(data_dict, f, sort_keys=False)


def df_to_parquet(df, target_filename):
    df.to_parquet(target_filename, index=False)


def parquet_to_df(source_filename):
    return pd.read_parquet(source_filename)


def export_df(df, target_filename, format=None):
    if not format:
        file_ext = pathlib.Path(target_filename).suffix
        if file_ext:
            format = file_ext[1:]
        else:
            format = 'jsonl'  # default to jsonl
    if format in ('jsonl', 'json'):
        return df_to_jsonl(df, target_filename)
    if format in ('yaml', 'yml'):
        return df_to_yaml(df, target_filename)


def df_from_sql(sql, sc_uri: str, engine=None):
    from sqlalchemy import create_engine, text
    if not engine:
        engine = create_engine(sc_uri)
    with engine.connect() as connection:
        # Set query timeout
        connection.execute(text("SET query_timeout=18000"))
        result = pd.read_sql(sql, connection)
        return result


def df_from_sql_if_not_exists(sql,
                              sc_uri: str,
                              engine=None,
                              parquet_file: str = None):
    if parquet_file and pathlib.Path(parquet_file).exists():
        return parquet_to_df(parquet_file)

    logger.debug(f'parquet file {parquet_file} not exists, will load from db')
    logger.debug(f'will execute sql.......\n{sql}')
    df = df_from_sql(sql, sc_uri, engine)
    if parquet_file:
        df_to_parquet(df, parquet_file)
    return df
