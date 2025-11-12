

from inference_server.modules.specedit.eval.eval_specedit import (
    run,
    analyze,
    analyze_results,
    analyze_single_case,
)


df1 = run('online.parquet', limit=50)


analyze_results(df1)


analyze_single_case(df1, 'cmpl-1b3cb813-7e95-4e5b-8b9f-3b622cb9f6aa')


analyze("online_evaluated.parquet")
