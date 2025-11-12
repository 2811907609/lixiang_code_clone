def show_benchmark_result():
    import pandas as pd
    import duckdb

    # pd.describe_option()
    pd.options.display.max_rows = 1000
    pd.options.display.max_columns = 1000
    pd.options.display.width = 1000

    rows = duckdb.sql(
        '''select strftime(to_timestamp(epoch), '%Y/%m/%d %H:%M') as date, * exclude(epoch, benchmark_time, modelpath, modelname)
    from read_json_auto("/mnt/volumes/zxd-code-complete/data/benchmark_results/*.json", union_by_name=true)
    where  latency_sec is not null and modeltype = 'vllm_codellama'
    order by input_len,max_tokens,date desc limit 200
''').df()
    print(rows)


# show_benchmark_result()
