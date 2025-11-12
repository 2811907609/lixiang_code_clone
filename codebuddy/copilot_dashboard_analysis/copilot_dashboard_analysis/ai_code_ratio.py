
import json
import os
import pathlib
import re

import pandas as pd
from datautils.pandas import df_from_sql_if_not_exists

from copilot_dashboard_analysis.config import Config
from copilot_dashboard_analysis.sqls.ai_code_ratio import (
    sql_ai_generated_code,
    sql_gerrit_changes,
    sql_gitlab_commits,
)

_cache_dir = pathlib.Path(__file__).parent.parent / '.cache_data'

_very_large_repos = [
    'git@gitlab.chehejia.com:emb_group/emb_project.git',
    'git@gitlab.chehejia.com:qcraft_external/vehicles.git',
    'git@gitlab.chehejia.com:wuwenze_verify/kernel_monitor/linux-6.12.13.git',
    'git@gitlabee.chehejia.com:rust-lang/crates.io-index.git',
    'git@gitlab.chehejia.com:ad/production/lios/mcu/ad5_max_mcu_tc397.git',
    'git@gitlab.chehejia.com:battery_management_system_project/supplier_project/x04.git',
    'git@gitlab.chehejia.com:huangtianyuan/genv2_tms.git',
]

_common_generated_file_patterns = [
    '/COMMIT_MSG',  # gerrit commit message
    'generated_',
    'grpc.pb',
    'mock_',
]

_top5_languages = [
    'python', 'java', 'go', 'c', 'cpp', 'rust', 'javascript', 'js',
    'typescript', 'ts'
]

_languages = {
    'python': {
        'extensions': ['.py'],
        'excluded_files': ['/migrations/'],
    },
    'go': {
        'extensions': ['.go'],
        'excluded_files': [
            '/ent/',  # ent.go framework
        ],
    },
    'javascript': {
        'extensions': ['.js', '.jsx'],
        'excluded_files': [
            'node_modules',
            'generated_',
            'mock_',
        ],
    },
    'typescript': {
        'extensions': ['.ts', '.tsx'],
        'excluded_files': [
            'node_modules',
            'generated_',
            'mock_',
        ],
    },
    'rust': {
        'extensions': ['.rs'],
        'excluded_files': [
            '/target/',
            '/tests/',
        ],
    },
    'java': {
        'extensions': ['.java'],
        'excluded_files': [
            '/target/',
            '/build/',
            '/src/test/',
        ],
    },
    'c': {
        'extensions': ['.c', '.h'],
        'excluded_files': [
            'generated_',
            '/vendor/',
        ],
    },
    'cpp': {
        'extensions': ['.cpp', '.hpp', '.cxx'],
        'excluded_files': [
            'generated_',
            '/vendor/',
        ],
    },
}

_extension_lang_map = {}

for lang, lang_info in _languages.items():
    for extension in lang_info['extensions']:
        _extension_lang_map[extension] = lang


def get_lang_from_path(p: str):
    if not p:
        return None
    _, ext = os.path.splitext(p)
    return _extension_lang_map.get(ext, None)


def get_excluded_patterns(lang: str):
    lang_info = _languages[lang]
    return lang_info['excluded_files'] + _common_generated_file_patterns


def should_ignore_file(p: str, lang: str = None):
    if not lang:
        lang = get_lang_from_path(p)
    if not lang:
        return True
    excluded_patterns = get_excluded_patterns(lang)
    for excluded_file in excluded_patterns:
        if excluded_file in p:
            return True
    return False


def format_gerrit_row(row):
    if row.patch_files:
        patch_files = json.loads(row.patch_files)
    else:
        patch_files = []
    if row.owner:
        owner = json.loads(row.owner)
        author_email = owner.get('email', '')
    else:
        author_email = ''
    rows = []
    for patch_file in patch_files:
        rows.append({
            'id': row.change_id,
            'date': row.date,
            'change_id': row.change_id,
            'project': row.project,
            'branch': row.branch,
            'author_email': author_email,
            'deletions': patch_file.get('deletions', 0),
            'file': patch_file.get('file', ''),
            'insertions': patch_file.get('insertions', 0),
            'type': patch_file.get('type', ''),
        })
    return pd.DataFrame(rows)


_email_pattern = re.compile(r'<(.*?)>')


def extract_email(s):
    if not s:
        return None
    match = _email_pattern.search(s)
    if match:
        return match.group(1)
    return None


def format_gitlab_row(row):
    author_email = extract_email(row.author)
    new_row = {
        'id': row.commit,
        'date': row.date,
        'commit': row.commit,
        'commit_date': row.commitdate,
        'project': row.origin,
        'author_email': author_email,
        'file': row.file,
        'insertions': row.added,
        'deletions': row.removed,
    }
    return pd.Series(new_row)


def filter_gitlab_row(df, user_emails):
    user_emails = set(user_emails)

    def filter(row):
        author_email = extract_email(row.author)
        if author_email in user_emails:
            return True
        if row.origin in _very_large_repos:
            return False
        return False

    return df[df.apply(filter, axis=1)]


def to_int(s):
    try:
        return int(s)
    except Exception:
        return 0


class AICodeRatioData:

    def __init__(
        self,
        start_date: str = None,
    ):
        self._config = Config()
        self._start_date = start_date

    def loaddata(self):
        sc_uri = self._config.starrocks_uri

        ai_code_sql = sql_ai_generated_code(self._start_date)
        ai_code_cache_file = _cache_dir / f'ai_code_{self._start_date}.parquet'
        self._ai_code_df = df_from_sql_if_not_exists(
            ai_code_sql, sc_uri=sc_uri, parquet_file=ai_code_cache_file)

        copilot_user_emails = self._ai_code_df.user_email.tolist()

        gerrit_commit_sql = sql_gerrit_changes(self._start_date)
        gerrit_commit_cache_file = _cache_dir / f'gerrit_commit_{self._start_date}.parquet'
        self._gerrit_commit_df = df_from_sql_if_not_exists(
            gerrit_commit_sql,
            sc_uri=sc_uri,
            parquet_file=gerrit_commit_cache_file)
        # dedup by change_id since a CR may be cherry-picked to multiple branches
        self._gerrit_commit_df.drop_duplicates(subset=['change_id'],
                                               inplace=True)

        df = self._gerrit_commit_df.apply(format_gerrit_row, axis=1)
        self._gerrit_commit_df = pd.concat(df.tolist(), ignore_index=True)

        gitlab_cache_file = _cache_dir / f'filtered_gitlab_commits_{self._start_date}.parquet'
        if pathlib.Path(gitlab_cache_file).exists():
            print('will load gitlab commits from cache')
            self._gitlab_commit_df = pd.read_parquet(gitlab_cache_file)
        else:
            gitlab_commit_sql = sql_gitlab_commits(self._start_date)
            gitlab_commit_cache_file = _cache_dir / f'gitlab_commit_{self._start_date}.parquet'
            df = df_from_sql_if_not_exists(
                gitlab_commit_sql,
                sc_uri=sc_uri,
                parquet_file=gitlab_commit_cache_file)

            print('len gitlab', len(df))
            df = filter_gitlab_row(df, copilot_user_emails)

            print('len gitlab', len(df))
            self._gitlab_commit_df = df
            df.to_parquet(gitlab_cache_file)

        self._gitlab_commit_df = self._gitlab_commit_df.apply(format_gitlab_row,
                                                              axis=1)
        self.combined_df = self.merge_commits()

    def user_email_department_map(self):
        m = self._ai_code_df.set_index('user_email')['department_2'].to_dict()
        return m

    def merge_commits(self):
        gerrit_df = self._gerrit_commit_df
        gitlab_df = self._gitlab_commit_df
        # 添加来源标识列
        gerrit_df['source'] = 'gerrit'
        gitlab_df['source'] = 'gitlab'

        # 合并时保留所有列，缺失值用NaN填充
        combined_df = pd.concat([gerrit_df, gitlab_df], ignore_index=True)

        # 移除原始的change_id和commit字段（可选）
        combined_df.drop(columns=['change_id', 'commit'], inplace=True)

        return combined_df


class AICodeRatioAnalysis:
    """将数据获取部分和数据处理部分分开，这样 AICodeRatioAnalysis 可以随时修改hotreload，同时可以继续用
    之前加载进来的数据.
    """

    def __init__(self, data: AICodeRatioData):
        self._data = data

    def __getattr__(self, name):
        try:
            return getattr(self._data, name)
        except AttributeError as e:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            ) from e

    def calc_user_commit_code(self, startdate=None):
        result = {}
        commit_df = self.combined_df
        if startdate:
            commit_df['date'] = pd.to_datetime(commit_df['date'])
            commit_df = commit_df[commit_df['date'] >= startdate]
        for _, row in commit_df.iterrows():
            user_code = result.setdefault(row.author_email, {})
            file = row.file
            lang = get_lang_from_path(file)
            if not lang:
                user_lang_code = user_code.setdefault('ignored', {})
            else:
                if should_ignore_file(file, lang=lang):
                    user_lang_code = user_code.setdefault('ignored', {})
                else:
                    user_lang_code = user_code.setdefault(lang, {})
            deletions = to_int(row.deletions)
            insertions = to_int(row.insertions)
            if insertions >= 1000:
                # skip if single added file is too large
                continue
            user_lang_code['deletions'] = user_lang_code.get('deletions',
                                                             0) + deletions
            user_lang_code['insertions'] = user_lang_code.get('insertions',
                                                              0) + insertions

        return result

    def calc_accepted_code(self, startdate=None):
        ai_code_df = self._ai_code_df
        if startdate:
            ai_code_df['date'] = pd.to_datetime(ai_code_df['date'])
            ai_code_df = ai_code_df[ai_code_df['date'] >= startdate]
        result = {}
        for _, row in ai_code_df.iterrows():
            user_code = result.setdefault(row.user_email, {})
            user_lang_code = user_code.setdefault(row.lang, {})
            user_lang_code['insertions'] = user_lang_code.get(
                'insertions', 0) + to_int(row.line_count)

        return result

    def calc_user_ai_gen_ratio(self, ai_generated, all_user_committed):
        result = []

        email_department_map = self.user_email_department_map()

        for email, generated in ai_generated.items():
            department = email_department_map.get(email)
            for lang in _languages:
                accepted_sum = generated.get(lang, {}).get('insertions', 0)

                committed = all_user_committed.get(email)
                if not committed:
                    continue

                user_added = committed.get(lang, {}).get('insertions', 0)
                if accepted_sum:
                    if accepted_sum <= 50:
                        # skip if accepted_sum is too small
                        continue
                    result.append(
                        (email, department, lang, accepted_sum, user_added))

        return result

    def calc_stat(self, ai_generated, all_user_committed):
        per_user_ratio = self.calc_user_ai_gen_ratio(ai_generated,
                                                     all_user_committed)
        df = pd.DataFrame(per_user_ratio,
                          columns=[
                              'user_email', 'department', 'lang',
                              'ai_gen_lines', 'user_added_lines'
                          ])
        df['ratio'] = df.ai_gen_lines / df.user_added_lines

        def calc(df):
            ai_lines = df.ai_gen_lines.sum()
            all_lines = df.user_added_lines.sum()
            avg_ratio = ai_lines / all_lines
            print(
                f'AI代码生成占比: {avg_ratio:.2%}, ai gen lines: {ai_lines}, total committed lines: {all_lines}'
            )

        print('========== total ==========')
        calc(df)

        for lang in _languages:
            sub_df = df[df.lang == lang]
            if len(sub_df) == 0:
                continue
            print(f'========== lang {lang} ==========')
            calc(sub_df)

        departments = df.department.dropna().unique().tolist()
        print('departments', departments)

        departments.sort()
        print('departments', departments)

        for department in departments:
            sub_df = df[df.department == department]
            if len(sub_df) == 0:
                continue
            print(f'========== department {department} ==========')
            calc(sub_df)
