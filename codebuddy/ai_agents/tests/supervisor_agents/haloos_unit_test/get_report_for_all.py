import os

from ai_agents.modules.haloos_auto_workflow.report_parse.function_coverage_report_parse import parse_coverage_report, get_coverage_summary
from tests.supervisor_agents.haloos_unit_test.get_token_use_from_log import get_token_from_file,get_money_of_token_use
import json
import csv
def get_coverage_for_give_path(test_repo_path):
    coverage_json = {}

    try:
        # 解析覆盖率报告
        coverage_file = os.path.join(test_repo_path, 'build/artifacts/gcov/gcovr/GcovCoverageResults.functions.html')
        result = parse_coverage_report(coverage_file, enhanced=True)
        summary = get_coverage_summary(result)
        coverage_json['coverage'] = summary

    except Exception as e:
        print(f"获取覆盖率失败: {e}")
        # coverage = 0.0
        summary = {'lines_coverage':0.0,'functions_coverage':0.0,'branches_coverage':0.0}
    # 返回总体覆盖率
    return summary

def coverage_to_csv(json_data, csv_path):
    # 需要排除base_path，只处理每个测试项
    rows = []
    for name, info in json_data.items():
        if name == "base_path":
            continue
        row = {
            "name": name,
            "line_count": info.get("line_count", ""),
            "lines_coverage": info.get("coverage", {}).get("lines", 0),
            "functions_coverage": info.get("coverage", {}).get("functions", 0),
            "branches_coverage": info.get("coverage", {}).get("branches", 0),
            'sum_input_token':info.get("sum_input_token", ""),
            'sum_output_token':info.get("sum_output_token", ""),
            "total_use": info.get("total_use", ""),
            "sum_input_token_round_list": info.get("sum_input_token_round_list", ""),
            "sum_output_token_round_list": info.get("sum_output_token_round_list", ""),
            "all_coverage_data": info.get("all_coverage_data", ""),
            "first_round_coverage": info.get("first_round_coverage", ""),
            "first_round_use": info.get("first_round_use", ""),
            "round_count": info.get("round_count", ""),

        }
        rows.append(row)


    # rows基于line_count排序
    rows.sort(key=lambda x: x["line_count"], reverse=False)
    # 写入csv
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "line_count", "lines_coverage", "functions_coverage", "branches_coverage",'sum_input_token', 'sum_output_token', 'total_use','sum_input_token_round_list',"sum_output_token_round_list","all_coverage_data",'first_round_coverage','first_round_use','round_count'])
        writer.writeheader()
        writer.writerows(rows)

def get_coverage_path_repo_round(folder_path, log_file_base_dir, save_path, is_sop):
    # 获取下一级文件和文件夹名称
    files = os.listdir(folder_path)

    json_data = {'base_path': folder_path}

    # 获取完整路径和文件（夹）名称
    for name in files:
        full_path = os.path.join(folder_path, name)

        print("name",name)
        # 读取readme文件
        src_file_name = name.replace('_test','.c')

        log_file = os.path.join(log_file_base_dir,src_file_name,'log.txt')

        # 直接用项目内的
        src_file_full_path = os.path.join(full_path,'src',src_file_name)
        with open(src_file_full_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        json_data[name] = {}
        json_data[name]['line_count'] = line_count

        print(f"名称: {name}, 路径: {full_path}")
        coverage_json = get_coverage_for_give_path(full_path)
        json_data[name]['coverage'] = coverage_json
        # 获取token花费

        try:
            sum_input_token, sum_output_token, sum_input_token_round_list, sum_output_token_round_list,all_coverage_data  = get_token_from_file(log_file, is_sop)

            json_data[name]['sum_input_token'] = sum_input_token
            json_data[name]['sum_output_token'] = sum_output_token
            json_data[name]['total_use'] = get_money_of_token_use(sum_input_token, sum_output_token)
            json_data[name]['sum_input_token_round_list'] = sum_input_token_round_list
            json_data[name]['sum_output_token_round_list'] = sum_output_token_round_list

            all_coverage_data_final = all_coverage_data[-1]
            json_data[name]['all_coverage_data'] = all_coverage_data_final # 取最后一个
        except Exception:
            json_data[name]['sum_input_token'] = 0
            json_data[name]['sum_output_token'] = 0
            json_data[name]['total_use'] = 0
            json_data[name]['sum_input_token_round_list'] = []
            json_data[name]['sum_output_token_round_list'] = []

            all_coverage_data_final = 0
            json_data[name]['all_coverage_data'] = 0

        try:
            json_data[name]['first_round_coverage'] = all_coverage_data_final[1] # 取最后一个
        except Exception:
            json_data[name]['first_round_coverage'] = 0

        print(log_file)
        try:
            json_data[name]['first_round_use'] = get_money_of_token_use(sum_input_token_round_list[0], sum_output_token_round_list[0])
        except Exception:
            json_data[name]['first_round_use'] = -1

        try:
            json_data[name]['round_count'] = len(all_coverage_data_final) - 1
        except Exception:
            json_data[name]['round_count'] = 0

    json_data_str = json.dumps(json_data, indent=4)
    print(json_data_str)
    coverage_to_csv(json_data, save_path)


def calculate_money_use_from_list_file(log_file_list,model_name):
    all_use = 0
    for log_file in log_file_list:
        sum_input_token, sum_output_token, sum_input_token_round_list, sum_output_token_round_list,all_coverage_data  = get_token_from_file(log_file, is_sop=True)

        money = get_money_of_token_use(sum_input_token, sum_output_token,model_name)
        all_use += money

    return all_use
