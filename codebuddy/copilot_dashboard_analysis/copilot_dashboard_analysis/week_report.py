import pathlib

import pandas as pd
from datautils.pandas import df_from_sql_if_not_exists

from copilot_dashboard_analysis.config import Config
from copilot_dashboard_analysis.sqls.sr_events import (
    sql_code_completion_events,
    sql_user_login_details,
)

_cache_dir = pathlib.Path(__file__).parent.parent / '.cache_data'

_department_main_languages = {
    '软件效率': ['go', 'python'],
    '基础软件': ['c'],
    '平台质量': ['python'],
    '数据闭环': ['python'],
    '智能OS': ['cpp', 'c'],
    '车控OS': ['c', 'python'],
    '系统软件': ['cpp', 'c', 'python'],
}


def filter_df(df):
    filtered_df = df[(df['copilot_model'] != '') & (df['scene'] != 'panel') &
                     (df['topn'].str.contains('Top5')) &
                     (df['accepted_days_cnt'] >= 10) & (df['use_days'] >= 7)]

    return filtered_df


class WeekReport:

    def __init__(
        self,
        prev_dates: tuple[str, str] = None,
        this_dates: tuple[str, str] = None,
    ):
        self._config = Config()
        self._prev_dates = prev_dates
        self._this_dates = this_dates

    def prepare(self):
        self.loaddata()
        print('data loaded')
        self._prev_filtered_df = filter_df(self._prev_df)
        self._this_filtered_df = filter_df(self._this_df)

    def loaddata(self):
        prev_sql = sql_code_completion_events(self._prev_dates[0],
                                              self._prev_dates[1])
        this_sql = sql_code_completion_events(self._this_dates[0],
                                              self._this_dates[1])
        sc_uri = self._config.starrocks_uri
        prev_cache_filename = _cache_dir / f'code_completion_{self._prev_dates[0]}_{self._prev_dates[1]}.parquet'
        self._prev_df = df_from_sql_if_not_exists(
            prev_sql, sc_uri=sc_uri, parquet_file=prev_cache_filename)

        this_cache_filename = _cache_dir / f'code_completion_{self._this_dates[0]}_{self._this_dates[1]}.parquet'
        self._this_df = df_from_sql_if_not_exists(
            this_sql, sc_uri=sc_uri, parquet_file=this_cache_filename)

        prev_login_sql = sql_user_login_details(self._prev_dates[0],
                                                self._prev_dates[1])
        this_login_sql = sql_user_login_details(self._this_dates[0],
                                                self._this_dates[1])

        prev_login_cache = _cache_dir / f'user_login_{self._prev_dates[0]}_{self._prev_dates[1]}.parquet'
        this_login_cache = _cache_dir / f'user_login_{self._this_dates[0]}_{self._this_dates[1]}.parquet'

        self._prev_login_df = df_from_sql_if_not_exists(
            prev_login_sql, sc_uri=sc_uri, parquet_file=prev_login_cache)
        self._this_login_df = df_from_sql_if_not_exists(
            this_login_sql, sc_uri=sc_uri, parquet_file=this_login_cache)

    def analyze_recent_7d_by_column(self,
                                    column: str,
                                    prev_df,
                                    this_df,
                                    shown_gt=None):
        '''
        shown_gt: int, 本周期和上周期的shown count需要大于等于shown_gt，过滤掉比较小的数。None 表示不过滤
        '''

        def groupby(df):
            df = df.groupby(column).agg(
                accepted_count=pd.NamedAgg(column='is_accepted', aggfunc='sum'),
                completion_shown_count=pd.NamedAgg(
                    column='is_completion_shown',
                    aggfunc='sum')).reset_index().sort_values(by=column)
            df['accept_ratio'] = (df['accepted_count'] /
                                  df['completion_shown_count']).round(4)
            return df

        prev_agg_df = groupby(prev_df)
        this_agg_df = groupby(this_df)

        merged_df = pd.merge(prev_agg_df,
                             this_agg_df,
                             on=column,
                             how='outer',
                             suffixes=('_prev', '_this'))
        merged_df['diff'] = (merged_df['accept_ratio_this'] -
                             merged_df['accept_ratio_prev']).round(4)
        if shown_gt:
            merged_df = merged_df[merged_df['completion_shown_count_this'] +
                                  merged_df['completion_shown_count_prev'] >=
                                  shown_gt]
        return merged_df

    def analyze_recent_7d_by_user(self):
        return self.analyze_recent_7d_by_column('user_name',
                                                self._prev_filtered_df,
                                                self._this_filtered_df)

    def analyze_recent_7d_by_l2department(self):
        return self.analyze_recent_7d_by_column('department_2',
                                                self._prev_filtered_df,
                                                self._this_filtered_df)

    def analyze_recent_7d_by_lang(self):
        return self.analyze_recent_7d_by_column('lang', self._prev_filtered_df,
                                                self._this_filtered_df)

    def analyze_recent_7d_by_depart_lang(self):
        df = self.analyze_recent_7d_by_column(['department_2', 'lang'],
                                              self._prev_filtered_df,
                                              self._this_filtered_df,
                                              shown_gt=200)

        def is_main_lang(row):
            ok = row['lang'] in _department_main_languages.get(
                row['department_2'], [])
            return 'Y' if ok else 'N'

        df['is_main_lang'] = df.apply(is_main_lang, axis=1)
        df.sort_values(by=['department_2', 'is_main_lang', 'lang'],
                       inplace=True)
        return df

    def analyze_recent_7d_by_depart_lang_topk_users(self, topk=3):
        df = self.analyze_recent_7d_by_column(
            ['department_2', 'lang', 'user_name'],
            self._prev_filtered_df,
            self._this_filtered_df,
            shown_gt=50)
        df['total_completion_shown_count'] = df[
            'completion_shown_count_this'] + df['completion_shown_count_prev']
        df = df.sort_values(by='total_completion_shown_count', ascending=False)

        # Group by 'department_2' and 'lang' and get the top 3 rows for each group
        df = df.groupby(['department_2', 'lang']).head(3).reset_index(drop=True)

        def is_main_lang(row):
            ok = row['lang'] in _department_main_languages.get(
                row['department_2'], [])
            return 'Y' if ok else 'N'

        df['is_main_lang'] = df.apply(is_main_lang, axis=1)
        df.sort_values(by=[
            'department_2', 'is_main_lang', 'lang',
            'total_completion_shown_count'
        ],
                       inplace=True)
        df.drop(columns=['total_completion_shown_count'], inplace=True)
        return df

    def analyze_recent_7d_by_model(self):
        df = self.analyze_recent_7d_by_column(['copilot_model'],
                                              self._prev_filtered_df,
                                              self._this_filtered_df)
        return df

    def analyze_7d_user_activity(self):
        """分析用户活跃变化情况"""
        # 1.从两个周期数据中提取用户和部门信息
        prev_users = self._prev_login_df[['user_email',
                                          'department_2']].drop_duplicates()
        this_users = self._this_login_df[['user_email',
                                          'department_2']].drop_duplicates()

        #2.合并数据并标记状态
        merged_users = pd.merge(prev_users,
                                this_users,
                                on=['user_email', 'department_2'],
                                how='outer',
                                indicator=True)

        #3.添加状态标记
        merged_users['status'] = merged_users['_merge'].map({
            'left_only': '仅上周',  # 流失用户
            'right_only': '仅本周',  # 新增用户
            'both': '持续活跃'  # 留存用户
        })

        #4.设置状态排序顺序
        status_order = ['持续活跃', '仅本周', '仅上周']
        merged_users['status'] = pd.Categorical(merged_users['status'],
                                                categories=status_order,
                                                ordered=True)

        #5.清理并按自定义顺序排序
        result = (merged_users.drop('_merge', axis=1).sort_values(
            ['status', 'department_2', 'user_email'],
            ascending=[True, True, True]))
        return result
