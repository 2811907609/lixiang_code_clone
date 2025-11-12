import json
import re
from dataclasses import asdict, dataclass

import fire
import requests
import yaml


@dataclass
class LLMEndpoint:
    name: str
    uri: str
    to_be_eval: bool = True  # 设置模型是否需要被评估
    eval: bool = True  # 设置是否用来评估其他的模型


_endpoints = [
    LLMEndpoint(
        'codestral22b',
        'https://lpai-inference.inner.chj.cloud/inference/sc-ep/codestral-22b-awq/v1/chat/completions'
    ),
    LLMEndpoint(
        'ziya34b',
        'https://lpai-inference.inner.chj.cloud/inference/sc-ep/vllm-ziya-34b/v1/chat/completions'
    ),
    # gpt4-o is only used for evaluation
    LLMEndpoint('gpt4-o', 'http://localhost:7000/unittest/default/completions',
                False, True),
]


@dataclass
class PromptResult:
    model: str
    response: str


@dataclass
class EvalResult:
    model: str
    best_index: int = None
    res_content: str = None
    error: str = None


@dataclass
class TestCase:
    prompt: str = ''
    messages: list[dict] = None
    results: list[PromptResult] = None
    eval_prompt: list[dict] = None
    eval_results: list[EvalResult] = None

    def todict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.todict(), ensure_ascii=False)


def load_offline_cases(file):
    '''输入使用yaml格式可读性比json好多了(有多行文本)'''
    with open(file, 'r') as f:
        for data in yaml.safe_load_all(f):
            if data and data.get('messages'):
                yield TestCase(messages=data['messages'])


def get_result_from_llm(endpoint: LLMEndpoint,
                        testcase: TestCase) -> PromptResult:
    payload = {
        'messages': testcase.messages,
        'temperature': 0.5,
        'max_tokens': 1024,
    }
    result = requests.post(endpoint.uri, json=payload)
    if result.ok:
        llm_result = result.json()['choices'][0]['message']['content']
        return PromptResult(endpoint.name, response=llm_result)
    else:
        print(f'get bad ersult: {result.text}')


def get_result_from_llms(endpoints: list[LLMEndpoint],
                         testcase: TestCase) -> list[PromptResult]:
    results: list[PromptResult] = []
    for endpoint in endpoints:
        result = get_result_from_llm(endpoint, testcase)
        results.append(result)
    return results


def extract_number(s: str):
    # Define the regex pattern
    pattern = r'[Aa]nswer\s*#?(\d+)'

    # Use re.search to find the pattern
    match = re.search(pattern, s, re.MULTILINE)

    # If a match is found, extract and return the number
    if match:
        try:
            return int(match.group(1))
        except Exception as _:
            return None
    else:
        return None  # Or handle the case where no match is found


def gen_eval_prompt(tc: TestCase):
    sys_prompt = ''
    user_prompt = f'''I have a question and many answers. Please help me to find the best answer.

### Question
{tc.messages[0]['content']}
'''

    for i, result in enumerate(tc.results):
        if not result:
            continue
        user_prompt += f'''=== Answer #{i + 1} Begin
{result.response}
=== Answer #{i + 1} End

'''

    user_prompt += '''

## Instruction
For all answers above, please give me the best answer like `Answer #<number>`.
Attention:
  - You CAN ONLY return `Answer #<number>` back, no anything else.
  - You MUST NOT add any extra explantations or reasons.'''

    print(f'sys prompt {sys_prompt}')
    print(f'user prompt {user_prompt}')

    messages = [
        # {'role': 'system', 'content': sys_prompt},
        {
            'role': 'user',
            'content': user_prompt
        },
    ]
    return messages


def eval_results_by_llm(endpoint: LLMEndpoint, messages) -> EvalResult:
    if not endpoint.eval:
        return None
    result = requests.post(endpoint.uri,
                           json={
                               'messages': messages,
                               'temperature': 0,
                               'max_tokens': 10,
                           })
    eval_result = EvalResult(model=endpoint.name, best_index=None)
    if result.ok:
        print('json result====', result.json())
        llm_result = result.json()['choices'][0]['message']['content']
        eval_result.res_content = llm_result
        eval_result.best_index = extract_number(llm_result)
    else:
        print(f'get bad ersult: {result.text}')

    return eval_result


def eval_results_by_llms(endpoints, tc: TestCase):
    eval_results: list[EvalResult] = []
    eval_prompt_messages = gen_eval_prompt(tc)
    tc.eval_prompt = eval_prompt_messages
    for endpoint in endpoints:
        r = eval_results_by_llm(endpoint, eval_prompt_messages)
        if r:
            eval_results.append(r)
    return eval_results


def eval(testfile: str, outfile: str):
    to_be_evaled_endpoints = [i for i in _endpoints if i.to_be_eval]
    eval_endpoints = [i for i in _endpoints if i.eval]
    testcases = load_offline_cases(testfile)
    with open(outfile, 'w') as f_w:
        for tc in testcases:
            prompt_results = get_result_from_llms(to_be_evaled_endpoints, tc)
            tc.results = prompt_results
            eval_results = eval_results_by_llms(eval_endpoints, tc)
            tc.eval_results = eval_results
            # print(tc.json())
            f_w.write(tc.json() + '\n')
            print(f'===========\n{eval_results}')


def report(outfile: str):
    total_case = 0
    model_eval_result = {}
    model_eval_same_with_gpt4o = {}
    with open(outfile, 'r') as f:
        for line in f:
            total_case += 1
            tc_result = json.loads(line)
            eval_results = tc_result.get('eval_results', [])
            gpt4o_eval_index = -1
            for eval_result in eval_results:
                if eval_result.get('model') == 'gpt4-o':
                    gpt4o_eval_index = eval_result.get('best_index')

            for eval_result in eval_results:
                if model := eval_result.get('model'):
                    if model not in model_eval_result:
                        model_eval_result[model] = {}
                    if idx := eval_result.get('best_index'):
                        if idx == gpt4o_eval_index:
                            model_eval_same_with_gpt4o[
                                model] = model_eval_same_with_gpt4o.get(
                                    model, 0) + 1
                        c = model_eval_result[model].get(idx, 0)
                        model_eval_result[model][idx] = c + 1
    print(f'总计有 {total_case} 个测试用例')
    for model, result in model_eval_result.items():
        print(f'{model} 评估结果:')
        for idx, cnt in result.items():
            to_be_evaled_model = _endpoints[idx - 1].name
            print(f'  模型 {to_be_evaled_model} 答案被选中 {cnt}/{total_case} 次')
        if model != 'gpt4-o':
            print(
                f'  和 gpt4-o 评估结果一致的次数: {model_eval_same_with_gpt4o.get(model, 0)}/{total_case}'
            )


if __name__ == '__main__':
    cmds = {
        'eval': eval,
        'report': report,
    }
    fire.Fire(cmds)
