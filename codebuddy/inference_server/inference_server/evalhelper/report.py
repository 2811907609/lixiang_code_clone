from typing import List, Set

import pandas as pd


def distribution_report(df,
                        columns: List[str] = None,
                        column_prefixes: Set[str] = None):
    columns = columns or []
    for c in df.columns:
        for prefix in column_prefixes:
            if c.startswith(prefix):
                columns.append(c)
    count = df[columns].count()
    average = df[columns].mean()
    median = df[columns].median()
    p80 = df[columns].quantile(0.80)
    p90 = df[columns].quantile(0.90)
    p95 = df[columns].quantile(0.95)
    p999 = df[columns].quantile(0.999)
    report_df = pd.DataFrame({
        'count': count,
        'Mean': average,
        'p50': median,
        'p80': p80,
        'p90': p90,
        'p95': p95,
        'p999': p999,
    })
    report_df = report_df.sort_index()
    return report_df
