def sql_ai_generated_code(start_date: str):
    sql = f'''
with t as (
	select '{start_date}' as starttime
),
c1 as (
select date_day as date, user_name, department_2, user_email , lang, output_text
	,array_length(split(output_text, '\n')) line_count
from  ep_code_db_starrocks_dwd.dwm_codebuddy_user_copilot_event_di,t
where is_accepted  and date_day >= t.starttime
)
select * from c1
'''
    return sql


def sql_gerrit_changes(start_date: str):
    sql = f'''
select FROM_UNIXTIME(`timestamp`) as date, change_id, project, branch, origin
    ,GET_JSON_STRING(data, '$.owner') owner
    ,GET_JSON_STRING(data, '$.currentPatchSet.files') patch_files
from ep_sr_ods.ods_gerritprod_perceval_gerrit_review
where  FROM_UNIXTIME(`timestamp`)  >= '{start_date}'
    AND GET_JSON_STRING(data, '$.status') not in ('ABANDONED') -- 'MERGED' and 'NEW'
'''
    return sql


def sql_gitlab_commits(start_date: str):
    sql = f'''
select
	commitdt as date, commit, origin, files_key, commitdate, author, commitor , action, added, file,removed, source
from
ep_code_db_starrocks_dwd.dwd_all_perceval_git_commit
where commitdt >= '{start_date}'  and origin  like '%gitlab%'
'''
    return sql
