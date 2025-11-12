import logging
import os

import pandas as pd
from sqlalchemy import create_engine

from datautils.pandas import export_df, df_to_parquet, parquet_to_df

logger = logging.getLogger(__name__)


def load_starrocks_data(sql, sc_uri: str):
    '''sc_uri is sth like mysql+mysqlconnector://sc_ep_rw:{password}@192.168.4.60:33333
    '''
    engine = create_engine(sc_uri)
    return pd.read_sql(sql, engine)


def load_starrocks_if_not_exists(sql: str,
                                 sc_uri: str,
                                 parquet_file: str = None):
    if parquet_file and os.path.exists(parquet_file):
        df = parquet_to_df(parquet_file)
        return df
    logger.debug(f'parquet file {parquet_file} not exists, will load from db')
    print('will execute sql.......\n', sql)
    df = load_starrocks_data(sql, sc_uri)
    df_to_parquet(df, parquet_file)
    return df


def export_starrocks_data(sql: str, target_filename: str, password: str = None):
    df = load_starrocks_data(sql, password)
    export_df(df, target_filename)
