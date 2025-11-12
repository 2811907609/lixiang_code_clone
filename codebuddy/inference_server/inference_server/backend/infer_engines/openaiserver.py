'''
You can use a Generic OpenAI Server as backend
'''

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.completion_choice import Logprobs as OpenAILogprobs

from inference_server.config import InstanceConfig
from inference_server.lang import get_stop_words
from inference_server.types import (
    OutputStat,
    attach_logprobs_v2,
    UsageInfo,
    CompletionResponseChoice,
    CompletionResponse,
    CompletionContext,
    Logprob,
    default_completion_context,
)
from inference_server.codebuddy.postprocess import (
    fix_output,
    trim_last_line,
    trim_last_stop,
    dedup_multi_choices,
    StopMatchType,
    get_stop_match_type,
)
from inference_server.backend.common import register
from inference_server.backend.basemodel import BaseModel

logger = logging.getLogger(__name__)


def should_start(server_process):
    if server_process:
        if server_process is not None:
            logger.error(f'server process exited, code is {server_process}')
            return True
        return False
    else:
        return True


def launch_server(current_server_process, commands: list[str] = None):
    if not should_start(current_server_process):
        return
    return subprocess.Popen(commands)


# python -m sglang.launch_server --port 9130 --model-path /lpai/volumes/zxd-code-complete/data/models/qwen/Qwen2.5-0.5B-Instruct-AWQ  --log-requests  --mem-fraction-static 0.1  --trust-remote-code


@register('openaiserver')
@dataclass
class OpenAIServer(BaseModel):
    server_process: None
    client: Optional[AsyncOpenAI]
    instance_config: None
    inf_type = 'openaiserver'

    @classmethod
    async def new_model(
            cls,
            model_path,  # not used, for compatibility
            commands: list[str] = None,
            server_base_uri: str = None,
            instance_config: InstanceConfig = None,
            **kwargs):
        if not (commands or server_base_uri):
            raise ValueError('commands or server base uri is required')
        print(f'commands {commands}, server_base_uri, {server_base_uri}')
        base_url = server_base_uri
        if not base_url:
            server_process = launch_server(None, commands=commands)
            base_url = 'http://0.0.0.0:9130/v1'
        else:
            server_process = None
        client = AsyncOpenAI(
            api_key='local_no_key',
            base_url=base_url,
        )
        return cls(server_process=server_process,
                   client=client,
                   instance_config=instance_config)

    async def code_complete_v2(self,
                               lang: str,
                               prefix: str,
                               suffix: str = None,
                               model_name=None,
                               **kwargs) -> CompletionResponse:
        ctx = default_completion_context()
        params = self.instance_params(model_name=model_name) or {}
        params.update(kwargs)

        # set a large temperature when n > 1
        n = kwargs.get('n') or 1
        if n > 1 and (not kwargs.get('temperature')):
            params['temperature'] = 0.3

        rag_min_length = params.pop('rag_min_length', 0)
        prefix_limit = params.pop('prefix_limit', 3000)
        prompt, prompt_info = self.gen_prompt(lang,
                                              prefix,
                                              suffix,
                                              prefix_limit=prefix_limit,
                                              rag_min_length=rag_min_length)

        stop = params.pop('stop', []) or []
        stop += get_stop_words(lang)
        prompt_info.stop = stop

        max_tokens = params.pop('max_tokens', 128)
        gen_params = dict(
            prompt=prompt,
            logprobs=5,
            n=n,
            temperature=0,
            max_tokens=max_tokens,
        )
        res = await self.non_stream_gen(stop, gen_params, ctx=ctx)
        fix_output(prompt_info, res)
        duration_sec = time.perf_counter() - ctx.start_time

        if res.usage:
            res.usage.inf_type = self.inf_type
            res.usage.duration_sec = duration_sec
            res.usage.prompt_compose_info = prompt_info

        # await collect_prompt_and_response(res.id, completion=res)
        return res

    async def non_stream_gen(self,
                             stop,
                             gen_params,
                             ctx: CompletionContext = None,
                             **kwargs):
        choice_map: Dict[int, CompletionResponseChoice] = {}
        # TODO should use request_id as completion_id
        completion_id = 'cmpl-' + str(uuid.uuid4())
        # request_id = random_uuid()  # for vllm internal engine
        async for result in self.stream_gen(stop, gen_params, **kwargs):
            # index, completion, _, usage = result[0], result[1], result[2], result[3]
            index = result[0]
            usage_info = result[3]
            is_timeout = False
            if ctx and ctx.is_timeout():
                is_timeout = True
                usage_info['finish_reason'] = 'timeout'
                usage_info.pop('stopped_by', None)
            choice = CompletionResponseChoice(
                index=index,
                text=result[1],
                finish_reason=usage_info.get('finish_reason'),
                choice_info=usage_info,
            )
            choice_map[index] = choice
            if is_timeout:
                await self.abort_request()
                break

        choices: List[CompletionResponseChoice] = []
        completion_tokens = 0
        stop = gen_params.get('stop', [])
        for _, c in choice_map.items():
            c.text = trim_last_line(c.text, gen_params['max_tokens'],
                                    c.choice_info.get('completion_tokens', 0))
            c.text = trim_last_stop(c.text, stop)
            choices.append(c)
            completion_tokens += c.choice_info.get('completion_tokens', 0)
        choices = dedup_multi_choices(choices)
        if choices:
            prompt_tokens = choices[0].choice_info.get('prompt_tokens', 0)
            output_stat = choices[0].choice_info.get('output_stat', None)
        else:
            prompt_tokens = 0
            output_stat = None
        usage = UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=completion_tokens + prompt_tokens,
            output_stat=output_stat,
        )
        return CompletionResponse(id=completion_id,
                                  model='',
                                  choices=choices,
                                  usage=usage)

    async def _stream_gen(
            self,
            # prompt,
            gen_params,
            **kwargs):
        if 'model' not in gen_params:
            gen_params['model'] = 'default'
        gen_params['stream'] = True
        gen_params['stream_options'] = dict(include_usage=True)

        topk_mean_threshold = (kwargs or {}).get('topk_mean_threshold')
        topk_mean_active_ratio = (kwargs or {}).get('topk_mean_active_ratio')
        topk_mean_token_num = (kwargs or {}).get('topk_mean_token_num', 3)

        start_time = time.perf_counter()
        finished_index_set = set()
        output_stats = {}
        first_token_latency = None
        first_token_time = None
        first_token_len = 0  # 首次推出的tokens的长度

        stream = await self.client.completions.create(**gen_params)
        async for chunk in stream:
            # id = chunk.id # we may use id later, id and index are mapped
            # each iteration will get one choice, for n=N, each is separated
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            index = choice.index
            delta_text = choice.text
            logprobs = convert_openai_logprobs_to_vllm(choice.logprobs)

            if index in output_stats:
                output_stat = output_stats[index]
                output_stat.logprobs.append(logprobs)
            else:
                output_stat = OutputStat(
                    output_token_length=0,
                    topk_mean_threshold=topk_mean_threshold,
                    topk_mean_active_ratio=topk_mean_active_ratio,
                    topk_mean_token_num=topk_mean_token_num,
                )
                output_stats[index] = output_stat
                output_stat.logprobs = [logprobs]

            # sglang don't support spec decode atm, so it is 1 token
            output_stat.output_token_length += 1

            this_token_time = time.perf_counter()
            if not first_token_latency:
                first_token_time = this_token_time
                first_token_latency = 1000.0 * (this_token_time - start_time
                                               )  # ms
                first_token_len = 1

            token_len_after_first_output = output_stat.output_token_length - first_token_len
            if token_len_after_first_output:
                output_stat.per_token_time = 1000.0 * (
                    this_token_time -
                    first_token_time) / token_len_after_first_output

            output_stat.first_token_latency = first_token_latency

            attach_logprobs_v2(output_stat)

            usage = {}
            if output_stat.should_drop_due_to_logprob():
                logger.info('vllm stop due to stop logprob')
                usage['finish_reason'] = 'stop_by_logprob'
                yield usage, index, delta_text, output_stat
                await self.abort_request()
                return

            received = yield usage, index, delta_text, output_stat
            if received:
                received_index, stop_word = received
                logger.info(
                    f'openaiserver stop due to stop {stop_word}, <<<{index} {delta_text}>>>'
                )
                finished_index_set.add(received_index)
                if len(finished_index_set) == len(output_stats):
                    await self.abort_request()
                return

    async def stream_gen(self, stop, gen_params, **kwargs):
        stop = stop or []
        stream = self._stream_gen(gen_params, **kwargs)
        n = gen_params.get('n') or 1
        current_completions = [''] * n
        aggregated_strs = [''] * n
        usage = {}
        try:
            async for result in stream:
                _usage, index, delta_text, output_stat = result
                usage['output_stat'] = output_stat
                for ch in delta_text:
                    aggregated_strs[index] += ch
                    stop_type, stop_words = get_stop_match_type(
                        aggregated_strs[index], stop)
                    if stop_type == StopMatchType.WHOLE:
                        # send back choice and stop words to engine so that engine can stop earlier
                        stream.asend(  # spellchecker:disable-line
                            (index, stop_words))
                        usage['finish_reason'] = 'stop'
                        usage['stopped_by'] = stop_words
                        yield index, current_completions[index], '', usage
                        return
                    if stop_type == StopMatchType.PREFIX:
                        continue
                    current_completions[index] += aggregated_strs[index]
                    yield index, current_completions[index], aggregated_strs[
                        index], usage
                    aggregated_strs[index] = ''
            # 上面for最后迭代如果走到PREFIX 部分匹配里面去的时候，aggregated_strs 里面是会有剩余token的
            for index, aggregated_str in enumerate(aggregated_strs):
                if aggregated_str:
                    current_completions[index] += aggregated_str
                    yield index, current_completions[
                        index], aggregated_str, usage
        except Exception as e:
            logger.error(f'stream_gen error: {e}')

    async def abort_request(self):
        logger.info('will implement later since sglang does not expose api')


def convert_openai_logprobs_to_vllm(logprobs: OpenAILogprobs) -> dict[Logprob]:
    '''我们之前一直用的是vllm，vllm的logprobs格式跟 openai 的不一样，通常应该跟 openai 保持一致，但是vllm
     格式的已经入库保存了很久了并且被使用了，以后都转换成vllm格式的'''
    # openAI 是dict的形式，vllm是list[dict]的形式
    result = []
    if not (logprobs and logprobs.top_logprobs):
        return None
    top_logprobs = logprobs.top_logprobs[0]
    for text, logprob in top_logprobs.items():
        log = Logprob(p=logprob, t=text)
        result.append(log)
    result.sort(key=lambda x: x.p, reverse=True)
    for i, logprob in enumerate(result):
        logprob.r = i + 1  # rank is 1-based

    return {i.t: i for i in result}
