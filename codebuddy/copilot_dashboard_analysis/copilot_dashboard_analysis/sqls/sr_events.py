def sql_code_completion_events(start_date, end_date):
    sql = f'''
SELECT * FROM ep_code_db_starrocks_dwd.dwm_codebuddy_user_copilot_event_di
WHERE date_day >= '{start_date}' AND date_day <= '{end_date}'
    '''
    return sql


# 计算周活,is_leave = 'no'代表未离职
def sql_user_login_details(start_date, end_date):
    sql = f'''
    select *
    from ep_code_db_starrocks_dwd.dwd_codebuddy_user_login_df
    where date_day  between '{start_date}' and '{end_date}'
    and  is_leave = 'no'
    '''
    return sql
