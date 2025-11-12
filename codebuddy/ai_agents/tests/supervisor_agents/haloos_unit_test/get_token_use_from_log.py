


import re



def extract_step_tokens(text):
    """
    提取每条记录的step数、input token和output token数
    """
    # 正则表达式匹配模式
    # 修改正则表达式以处理：
    # 1. 可能存在的时间戳前缀 [2025-09-15 12:59:27]
    # 2. Output tokens后可能有换行符的情况
    # 3. 使用 .*? 来匹配可能的时间戳和其他前缀内容
    pattern = r'\[Step (\d+): Duration [\d.]+? seconds\| Input tokens: ([\d,]+)(?:\s*\n)?\s*\|\s*Output tokens:\s*([\d,]+)\]'

    matches = re.findall(pattern, text, re.DOTALL)

    results = []
    for match in matches:
        step_num = int(match[0])
        input_tokens = int(match[1].replace(',', ''))
        output_tokens = int(match[2].replace(',', ''))

        results.append({
            'step': step_num,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        })

    return results

def extract_from_file(file_path):
    """从文件中提取数据"""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        return extract_step_tokens(content)

def print_results(results):
    """格式化输出结果"""
    print(f"{'Step':<6} {'Input Tokens':<15} {'Output Tokens':<15}")
    print("-" * 40)

    for result in results:
        print(f"{result['step']:<6} {result['input_tokens']:<15,} {result['output_tokens']:<15,}")


# 获取连续的序列
def find_consecutive_sequences_in_order(data):
    """
    按照现有顺序找出step中的连续序列（不重新排序）
    """
    if not data:
        return []

    sequences = []
    current_sequence = [data[0]]

    for i in range(1, len(data)):
        current_step = data[i]['step']
        prev_step = data[i-1]['step']

        # 如果当前step比前一个step大1，则是连续的
        if current_step == prev_step + 1:
            current_sequence.append(data[i])
        else:
            # 连续序列结束，保存当前序列
            if len(current_sequence) > 1:  # 只保存长度大于1的序列
                sequences.append(current_sequence)
            current_sequence = [data[i]]

    # 添加最后一个序列
    if len(current_sequence) > 1:
        sequences.append(current_sequence)
    return sequences




# 获取每个序列最后一个数据的input和output token数，并验证每个序列内这个是最大的，验证每个序列是连续的

def get_all_coverage_sum_from_sequences(sequences, is_sop=False):
    print("hahah",len(sequences))
    for i in range(len(sequences)):
        print(i,"*****",sequences[i])

    sum_input_token = 0
    sum_output_token = 0

    if len(sequences) == 0:
        return sum_input_token, sum_output_token

    if is_sop:
        # 去掉第一个
        sequences = sequences[1:]
        print(len(sequences))
        # 最后一个最后一步
        last_one_input_tokens = sequences[-1][-1]['input_tokens']
        last_one_output_tokens = sequences[-1][-1]['output_tokens']
    else:
        last_one_input_tokens = 0
        last_one_output_tokens = 0

    for seq in sequences:

        if seq[0]['step'] != 1:
            continue

        # 检查是否是连续的
        for i in range(1, len(seq)):
            if seq[i]['step'] != seq[i-1]['step'] + 1:
                assert 1 == 2, f"非连续: {seq[i]['step']} {seq[i-1]['step']}"

        # 最后最大值
        sum_input_token += seq[-1]['input_tokens']
        sum_output_token += seq[-1]['output_tokens']

    sum_input_token += last_one_input_tokens
    sum_output_token += last_one_output_tokens

    return sum_input_token, sum_output_token



def get_agent_from_sequences(sequences, max_steps = 80):

    sum_input_token = 0
    sum_output_token = 0
    max_steps = 0
    assert(len(sequences)) <= 2, f'{len(sequences)}'
    if len(sequences) == 0:
        return sum_input_token, sum_output_token

    last_one_input_tokens = 0
    last_one_output_tokens = 0

    for seq in sequences:
        if seq[0]['step'] != 1:
            continue

        # 检查是否是连续的
        for i in range(1, len(seq)):
            if seq[i]['step'] != seq[i-1]['step'] + 1:
                assert 1 == 2, f"非连续: {seq[i]['step']} {seq[i-1]['step']}"

        # 最后最大值
        sum_input_token += seq[-1]['input_tokens']
        sum_output_token += seq[-1]['output_tokens']

        max_steps = len(seq)

        assert max_steps <= max_steps

    sum_input_token += last_one_input_tokens
    sum_output_token += last_one_output_tokens

    return sum_input_token, sum_output_token,max_steps


def get_coverage_from_log(content):
    pattern = r'历史覆盖率\[(.*?)\]'
    matches = re.findall(pattern, content)
    all_data = []
    for match in matches:
        numbers = [float(x.strip()) for x in match.split(',')]
        all_data.append(numbers)

    return all_data

def get_token_from_file(file_path,is_sop=False):

    split_round = '>>>>> 第'

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    all_coverage_data = get_coverage_from_log(content)


    content_list = content.split(split_round)[1:]

    sum_input_token = 0
    sum_output_token = 0

    sum_input_token_list = []
    sum_output_token_list = []
    # sop token有bug？
    for content_item in content_list:
        results = extract_step_tokens(content_item)
        # # 提取数据
        # results = extract_from_file(file_path)

        # 找出连续的step序列，有可能最后一个
        consecutive_sequences = find_consecutive_sequences_in_order(results)

        sum_input_token_, sum_output_token_ = get_all_coverage_sum_from_sequences(consecutive_sequences, is_sop=is_sop)

        sum_input_token += sum_input_token_
        sum_output_token += sum_output_token_

        sum_input_token_list.append(sum_input_token_)
        sum_output_token_list.append(sum_output_token_)
    # print("sum_output_token_list",sum_output_token_list)
    return sum_input_token, sum_output_token, sum_input_token_list, sum_output_token_list,all_coverage_data

def find_new_run_with_finditer(text):
    """使用 finditer 查找所有匹配"""
    pattern = r'New run - ([^\s─\n]+)'
    results = []

    # 先收集所有匹配
    matches = list(re.finditer(pattern, text))

    # 计算每个匹配的行号和end_index
    for i, match in enumerate(matches):
        # 计算行号：统计匹配位置之前的换行符数量
        start_line = text[:match.start()].count('\n')
        content = match.group(1).strip()

        # 如果有下一个匹配，end_index为下一个匹配的开始位置
        # 否则为-1
        if i < len(matches) - 1:
            end_line = text[:matches[i + 1].start()].count('\n')
        else:
            end_line = -1

        results.append({
            'start_line': start_line,
            'content': content,
            'position': match.start(),
            'end_line': end_line
        })

    return results

def print_agent_aggregation(agent_aggregation):
    for agent, info in agent_aggregation.items():
        items = [f"'{k}': {v}" for k, v in info.items() if k != 'all_data']
        print(f"{agent}: {{{', '.join(items)}}}")

def get_token_usage_and_agent_call_from_log(file_path,is_sop=True):
    # 详细信息
    split_round = '>>>>> 第'

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    content_list = content.split(split_round)[1:]


    sum_output_token_list = []

    # 循环
    for round_content_item in content_list:
        round_content_item_line_list = round_content_item.split('\n')
        agent_results = find_new_run_with_finditer(round_content_item)

        for agent_result in agent_results:

            agent_content = round_content_item_line_list[agent_result['start_line']:agent_result['end_line']]
            agent_content = '\n'.join(agent_content)

            # 每次循环内agent切分
            results_agent = extract_step_tokens(agent_content)
            # # 提取数据
            # results = extract_from_file(file_path)

            # 找出连续的step序列，有可能最后一个
            consecutive_sequences = find_consecutive_sequences_in_order(results_agent)

            if len(consecutive_sequences) > 2:
                print(agent_content)
                for i in range(len(results_agent)):
                    print(results_agent[i])

                for i in range(len(consecutive_sequences)):
                    print("consecutive_sequences",consecutive_sequences[i])
            sum_input_token_, sum_output_token_, agent_steps = get_agent_from_sequences(consecutive_sequences)

            sum_output_token_list.append({'agent_name':agent_result['content'], 'sum_input_token':sum_input_token_, 'sum_output_token':sum_output_token_ ,'agent_steps':agent_steps})

    # print("sum_output_token_list",sum_output_token_list)
    return sum_output_token_list


# 聚合每一种agent花销，聚合所有花销
def aggregate_agent_costs(sum_output_token_list):
    """
    聚合每种agent的花销和总花销
    """
    agent_aggregation = {}
    total_input_tokens = 0
    total_output_tokens = 0
    total_steps = 0

    # 按agent类型聚合
    for item in sum_output_token_list:
        agent_name = item['agent_name']
        input_tokens = item['sum_input_token']
        output_tokens = item['sum_output_token']
        steps = item['agent_steps']

        if agent_name not in agent_aggregation:
            agent_aggregation[agent_name] = {
                'count': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_steps': 0,
                'all_data':[]
            }

        agent_aggregation[agent_name]['count'] += 1
        agent_aggregation[agent_name]['total_input_tokens'] += input_tokens
        agent_aggregation[agent_name]['total_output_tokens'] += output_tokens
        agent_aggregation[agent_name]['total_steps'] += steps
        agent_aggregation[agent_name]['all_data'].append(item)

        # 累计总量
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_steps += steps

    return agent_aggregation, total_input_tokens, total_output_tokens, total_steps

def get_money_of_token_use(sum_input_token,sum_output_token, model_name):
    money_use = {
        'claude4':{'input_use':0.022,'output_use':0.108},
        'deepseek3.1':{'input_use':0.004,'output_use':0.012},
    }
    if model_name in money_use:
        input_use = money_use[model_name]['input_use']
        output_use = money_use[model_name]['output_use']
    else:
        raise ValueError(f"不支持的模型名称: {model_name}")

    total_use = sum_input_token / 1000 * input_use + sum_output_token / 1000 * output_use

    # 保留三位小数
    total_use = round(total_use, 3)
    return total_use
def calculate_money_use_different_model(agent_aggregation):
    # map_info = {
    #     'dependency_generator':'claude4',
    #     'dependency_fixer':'claude4',
    #     'unit_test_analyzer':'claude4',
    #     'unit_test_fixer':'deepseek3.1',
    #     'unit_test_agent':'deepseek3.1',
    #     'unit_test_append': 'deepseek3.1'
    # }

    map_info = {
        'dependency_generator':'claude4',
        'dependency_fixer':'claude4',
        'unit_test_analyzer':'claude4',
        'unit_test_fixer':'claude4',
        'unit_test_agent':'claude4',
        'unit_test_append': 'claude4'
    }

    all_money_use = 0
    for agent, info in agent_aggregation.items():
        model_name = map_info.get(agent)
        agent_money = get_money_of_token_use(info['total_input_tokens'], info['total_output_tokens'], model_name)
        agent_aggregation[agent]['agent_money'] = agent_money

        all_money_use += agent_money

    print("all_money_use",all_money_use)

    return agent_aggregation

def calculate_agent_use_from_list(log_file_list):


    sum_output_token_list_all = []
    for log_file in log_file_list:
        sum_output_token_list = get_token_usage_and_agent_call_from_log(log_file, is_sop=True)
        sum_output_token_list_all.extend(sum_output_token_list)

    agent_aggregation, total_input_tokens, total_output_tokens, total_steps = aggregate_agent_costs(sum_output_token_list_all)

    # all_money = get_money_of_token_use(total_input_tokens,total_output_tokens)
    agent_aggregation = calculate_money_use_different_model(agent_aggregation)
    print_agent_aggregation(agent_aggregation)
