# ruff: noqa: E402  # Module level import not at top of file
import argparse
import asyncio
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import FastAPI
from packaging.version import Version

try:
    import vllm
    from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams
    from vllm.lora.request import LoRARequest
    from vllm.engine.async_llm_engine import AsyncEngineDeadError
    from vllm.entrypoints.openai.api_server import build_app, init_app_state
except Exception as e:
    print('vllm not installed, please install it', e)

from inference_server.backend.common import register
from inference_server.backend.basemodel import BaseModel
from inference_server.backend.state import request_manager
from inference_server.codebuddy.postprocess import (
    StopMatchType,
    dedup_multi_choices,
    fix_output,
    get_stop_match_type,
    trim_last_stop,
)
from inference_server.config import InstanceConfig
from inference_server.lang import get_stop_words
from inference_server.types import (
    CompletionContext,
    CompletionResponse,
    CompletionResponseChoice,
    OutputStat,
    RuntimeInfo,
    UsageInfo,
    attach_logprobs,
    default_completion_context,
)
from inference_server.utils import random_uuid, getLogger

from .vllm_args import create_async_args

logger = getLogger(__name__)


class VLLM(BaseModel):
    _enable_monitor = True

    def __post_init__(self):
        print('post init called')
        super().__init__()
        if self._enable_monitor:
            asyncio.create_task(self.start_monitor())

    async def heartbeat(self):
        engine = self.model
        await engine.check_health()
        return True


async def setup_vllm_api_server(args: argparse.Namespace,
                                **uvicorn_kwargs) -> None:
    """References:
    https://github.com/bentoml/BentoVLLM/blob/main/llama3.1-8b-instruct/service.py
    https://docs.ray.io/en/master/serve/tutorials/vllm-example.html
    https://github.com/vllm-project/vllm/blob/v0.7.2/vllm/entrypoints/openai/api_server.py#L876"""
    vllm_version = vllm.__version__
    logger.info("vLLM API server version %s", vllm_version)
    args.served_model_name = ['default']
    logger.info("args: %s", args)
    engine_args = AsyncEngineArgs.from_cli_args(args)
    engine = AsyncLLMEngine.from_engine_args(engine_args)

    app = build_app(args)
    if Version(vllm_version) <= Version('0.8.4'):
        config = await engine.get_model_config()
    else:
        config = await engine.get_vllm_config()
    await init_app_state(engine, config, app.state, args)
    return engine, app


@register('vllm_generic', 'vllm_phi')
@dataclass
class VLLMGeneric(VLLM):
    model: None
    tokenizer: None
    instance_config: InstanceConfig = None
    app: FastAPI = None
    inf_type = 'vllm'

    @classmethod
    async def new_model(cls,
                        modelpath: str,
                        trust_remote_code=True,
                        instance_config=None,
                        **kwargs):
        args = create_async_args(modelpath,
                                 instance_config=instance_config)

        if hasattr(cls, 'CHAT_TEMPLATE'):
            args.chat_template = cls.CHAT_TEMPLATE
        engine_client, app = await setup_vllm_api_server(args)

        return cls(model=engine_client,
                   tokenizer=None,
                   instance_config=instance_config,
                   app=app)

    @classmethod
    def runtime_info(cls) -> RuntimeInfo:
        info = BaseModel.runtime_info()
        info.vllm_version = vllm.__version__
        info.inf_type = cls.inf_type
        return info

    def subapp(self) -> Optional[FastAPI]:
        return self.app

    async def get_tokenizer(self):
        return await self.model.get_tokenizer()

    def gen_lora_request(self, lora):
        c = self.instance_config
        if not c:
            raise ValueError('instance_config is not set')
        loras = c.get('lora', {}).get('loras')
        if not loras:
            raise ValueError(
                f'model do not support lora, lora {lora} not found')
        lora_config = loras.get(lora)
        if not lora_config:
            raise ValueError(f'lora {lora} not found in config')
        lora_id = lora_config['id']
        lora_path = lora_config['path']
        return LoRARequest(lora, lora_id, lora_path)

    async def code_complete_v2(self,
                               lang: str,
                               prefix: str,
                               suffix: str = None,
                               model_name=None,
                               no_prompt_cutoff=False,
                               should_abort=None,
                               **kwargs) -> CompletionResponse:
        ctx = default_completion_context()
        params = self.instance_params(model_name=model_name) or {}
        params.update(kwargs)
        if not params.get('n'):
            params['n'] = 1

        # use greedy for normal code completion
        if params['n'] == 1:
            if 'temperature' not in params:
                params['temperature'] = 0
        # set a large temperature when n > 1
        if params['n'] > 1 and (not kwargs.get('temperature')):
            params['temperature'] = 0.3

        rag_min_length = params.pop('rag_min_length', 0)
        prefix_limit = params.pop('prefix_limit', 3000)
        prompt, prompt_info = self.gen_prompt(lang,
                                              prefix,
                                              suffix,
                                              no_prompt_cutoff=no_prompt_cutoff,
                                              prefix_limit=prefix_limit,
                                              rag_min_length=rag_min_length)

        stop = params.pop('stop', []) or []
        stop += get_stop_words(lang)
        # model can configure model specific stop words, like <|fim_pad|>
        stop += self.stop_words()

        prompt_info.stop = stop

        max_tokens = params.pop('max_tokens', 128)
        prompt_info.max_new_tokens = max_tokens
        res = await self.generate_no_stream(prompt,
                                            stop=stop,
                                            max_tokens=max_tokens,
                                            model_name=model_name,
                                            ctx=ctx,
                                            should_abort=should_abort,
                                            **params)
        fix_output(prompt_info, res)
        duration_sec = time.perf_counter() - ctx.start_time

        res.ft_model_info = self.instance_config.ft_model_info
        if res.usage:
            res.usage.abtest = dict()
            res.usage.inf_type = self.inf_type
            res.usage.duration_sec = duration_sec
            res.usage.prompt_compose_info = prompt_info

        # await collect_prompt_and_response(res.id, completion=res)

        return res

    async def generate_no_stream(self,
                                 prompt,
                                 model_name=None,
                                 ctx: CompletionContext = None,
                                 should_abort=None,
                                 original_draft_text=None,
                                 disable_multi_stop_words=False,
                                 **kwargs) -> CompletionResponse:
        start_time = time.perf_counter()
        params = kwargs
        if 'temperature' not in params:
            params['temperature'] = 0.01
        if 'top_p' not in params:
            params['top_p'] = 0.9
        if 'max_tokens' not in params:
            params['max_tokens'] = 128
        if lora := params.pop('lora', None):
            params['lora_request'] = self.gen_lora_request(lora)

        choice_map: Dict[int, CompletionResponseChoice] = {}
        # TODO should use request_id as completion_id
        completion_id = 'cmpl-' + str(uuid.uuid4())
        request_id = random_uuid()  # for vllm internal engine
        async for result in self.vllm_async_generate_stream(
                prompt,
                prompt_token_ids=None,
                request_id=request_id,
                should_abort=should_abort,
                original_draft_text=original_draft_text,
                disable_multi_stop_words=disable_multi_stop_words,
                **params):
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
                await self.abort_request(request_id)
                break
        choices: List[CompletionResponseChoice] = []
        completion_tokens = 0
        stop = kwargs.get('stop', [])
        for _, c in choice_map.items():
            c.text = trim_last_stop(c.text, stop)
            choices.append(c)
            completion_tokens += c.choice_info.get('completion_tokens', 0)
        choices = dedup_multi_choices(choices)
        prompt_tokens = choices[0].choice_info.get('prompt_tokens', 0)
        output_stat = choices[0].choice_info.get('output_stat', None)
        decoding_steps = choices[0].choice_info.get('decoding_steps', None)
        duration_sec = time.perf_counter() - start_time
        usage = UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            decoding_steps=decoding_steps,
            total_tokens=completion_tokens + prompt_tokens,
            output_stat=output_stat,
            duration_sec=duration_sec,
        )
        return CompletionResponse(id=completion_id,
                                  model='',
                                  choices=choices,
                                  usage=usage)

    async def chat_complete(self, messages, is_redzone=None, **kwargs):
        max_tokens = kwargs.pop('max_tokens', 4096)
        stop = kwargs.pop('stop', []) or []
        stop += get_stop_words('')
        # add_generation_prompt=True will add sth like `Assistant: ` to the end of the prompt
        # so that output will not begin with `Assistant: `
        chat_template = getattr(self, 'CHAT_TEMPLATE', None)
        tokenizer = await self.get_tokenizer()
        prompt = tokenizer.apply_chat_template(messages,
                                               chat_template=chat_template,
                                               add_generation_prompt=True,
                                               tokenize=False)
        params = self.default_chat_params()
        supported_param_keys = [
            'stream',
            'top_p',
            'temperature',
            'frequency_penalty',
            'repetition_penalty',
            'original_draft_text',
        ]
        for key in supported_param_keys:
            if key in kwargs:
                params[key] = kwargs[key]
        if not is_redzone:
            logger.info(f'prompt { prompt[:100] }')
        request_id = random_uuid()
        if kwargs.get('stream'):
            async for _, _, delta_completion, usage in self.vllm_async_generate_stream(
                    prompt,
                    stop=stop,
                    max_tokens=max_tokens,
                    request_id=request_id,
                    **params):
                if len(delta_completion) == 0:
                    continue
                yield delta_completion, usage
            return
        else:
            yield await self.vllm_async_generate(prompt,
                                                 stop=stop,
                                                 max_tokens=max_tokens,
                                                 request_id=request_id,
                                                 **params)

    async def encode_original_draft_text(self, request_id, draft_text):
        tokenizer = await self.get_tokenizer()
        token_ids = tokenizer.encode(draft_text)
        request_manager.set_stream_next_chunk(request_id, token_ids)

    async def abort_request(self, request_id):
        await self.model.abort(request_id)
        request_manager.remove_request(request_id)

    async def _vllm_generate(self,
                             prompt,
                             prompt_token_ids,
                             sampling_params,
                             request_id,
                             lora_request=None,
                             options=None):
        params = dict(request_id=request_id,)
        if lora_request:
            params['lora_request'] = lora_request

        if not prompt_token_ids:
            tokenizer = await self.get_tokenizer()
            prompt_token_ids = tokenizer(prompt).input_ids
        inputs = {
            'prompt': prompt,
            'prompt_token_ids': prompt_token_ids,
        }
        output_gen = self.model.generate(inputs,
                                         sampling_params=sampling_params,
                                         **params)
        # the generator here will output a few in each iteration, we only need the final one
        output = None
        starttime = time.perf_counter()
        finished_index_set = set()
        output_stats = {}
        first_token_latency = None
        first_token_time = None
        first_token_len = 0  # 首次推出的tokens的长度
        decoding_steps = 0

        topk_mean_threshold = (options or {}).get('topk_mean_threshold')
        topk_mean_active_ratio = (options or {}).get('topk_mean_active_ratio')
        topk_mean_token_num = (options or {}).get('topk_mean_token_num', 3)

        async for res in output_gen:
            decoding_steps += 1
            for output in res.outputs:
                i = output.index
                if i in finished_index_set:
                    continue

                if i in output_stats:
                    output_stat = output_stats[i]
                else:
                    output_stat = OutputStat(
                        topk_mean_threshold=topk_mean_threshold,
                        topk_mean_active_ratio=topk_mean_active_ratio,
                        topk_mean_token_num=topk_mean_token_num,
                    )
                    output_stats[i] = output_stat

                this_token_time = time.perf_counter()
                if not first_token_latency:
                    first_token_time = this_token_time
                    first_token_latency = 1000.0 * (this_token_time - starttime)
                    first_token_len = len(output.token_ids)

                token_len_after_first_output = len(
                    output.token_ids) - first_token_len
                if token_len_after_first_output:
                    output_stat.per_token_time = 1000.0 * (
                        this_token_time -
                        first_token_time) / token_len_after_first_output

                output_stat.first_token_latency = first_token_latency

                completion = output.text
                cumulative_logprob = output.cumulative_logprob
                output_stat.cumulative_logprob = output.cumulative_logprob
                # inf/-inf is not standard json, some languages like golang do not
                # support it, we need to convert it
                attach_logprobs(output_stat, output.logprobs)

                if output.cumulative_logprob is not None:
                    if (not output_stat.logprob_lt1_idx
                       ) and cumulative_logprob <= -1:
                        output_stat.logprob_lt1_idx = len(completion)

                    if (not output_stat.logprob_lt3_idx
                       ) and cumulative_logprob <= -3:
                        output_stat.logprob_lt3_idx = len(completion)

                    if output_stat.first_token_logprob is None:
                        output_stat.first_token_logprob = cumulative_logprob

                prompt_token_len = len(res.prompt_token_ids)
                completion_token_len = len(output.token_ids)
                usage = {
                    'prompt_tokens': prompt_token_len,
                    'completion_tokens': completion_token_len,
                    'total_tokens': prompt_token_len + completion_token_len,
                    'first_token_logprob': output_stat.first_token_logprob,
                    'logprob_lt1_idx': output_stat.logprob_lt1_idx,
                    'logprob_lt3_idx': output_stat.logprob_lt3_idx,
                    'decoding_steps': decoding_steps,
                    'output_stat': output_stat.model_dump(),
                }
                if finish_reason := output.finish_reason:
                    usage['finish_reason'] = finish_reason

                if output_stat.should_drop_due_to_logprob():
                    logger.info('vllm stop due to stop logprob')
                    usage['finish_reason'] = 'stop_by_logprob'
                    yield (i, '', usage)
                    await self.abort_request(request_id)
                    return

                received = yield (
                    i,
                    output.text,
                    usage,
                )
                if received:
                    seq, stop_words = received
                    logger.info(
                        f'vllm stop due to stop {stop_words}, <<<{completion}>>>'
                    )
                    finished_index_set.add(seq)
                    # stop by us, we need to abort this request to save CPU/GPU resources
                    if len(finished_index_set) == len(res.outputs):
                        await self.abort_request(request_id)
                    return

    async def vllm_async_generate(self,
                                  prompt,
                                  prompt_token_ids=None,
                                  temperature=0.01,
                                  top_p=0.9,
                                  max_tokens=128,
                                  request_id=None,
                                  **kwargs):
        completion = ''
        usage = {}
        async for result in self.vllm_async_generate_stream(
                prompt,
                prompt_token_ids=prompt_token_ids,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                request_id=request_id,
                **kwargs):
            completion, _, usage = result[1], result[2], result[3]
        return completion, usage

    async def vllm_async_generate_stream(self,
                                         prompt,
                                         prompt_token_ids=None,
                                         temperature=0,
                                         top_p=0.9,
                                         max_tokens=128,
                                         lora_request=None,
                                         request_id=None,
                                         should_abort=None,
                                         original_draft_text=None,
                                         disable_multi_stop_words=False,
                                         **kwargs):
        stop = kwargs.pop('stop', []) or []
        sampling_keys = [
            'n', 'frequency_penalty', 'repetition_penalty', 'top_p', 'top_k',
            'min_p', 'logprobs', 'include_stop_str_in_output'
        ]
        params = {i: kwargs[i] for i in sampling_keys if i in kwargs}
        if not top_p:
            top_p = 0.9
        sampling_params = SamplingParams(temperature=temperature,
                                           top_p=top_p,
                                           max_tokens=max_tokens,
                                           **params)
        if original_draft_text:
            # just let it work at background, we don't need to block here
            # TODO seems that no need to run in background
            await self.encode_original_draft_text(request_id,
                                                  original_draft_text)

        logger.info(f'vllm sampling_params: {sampling_params}')
        output_gen = self._vllm_generate(prompt,
                                         prompt_token_ids,
                                         sampling_params,
                                         request_id,
                                         lora_request=lora_request,
                                         options=kwargs)
        previous_completions = [''] * sampling_params.n
        aggregated_str = ''
        i = None
        usage = {}
        try:
            async for result in output_gen:
                i, completion, usage = result[0], result[1], result[2]
                delta_completion = completion[len(previous_completions[i]):]
                previous_completions[i] = completion

                if disable_multi_stop_words:
                    yield i, completion, delta_completion, usage
                    continue

                if should_abort:
                    ok, reason = await should_abort()
                    if ok:
                        usage['finish_reason'] = reason
                        yield i, completion, delta_completion, usage
                        return

                for ch in delta_completion:
                    aggregated_str += ch
                    stop_type, stop_words = get_stop_match_type(
                        aggregated_str, stop)
                    if stop_type == StopMatchType.WHOLE:
                        # send back choice and stop words to engine so that engine can stop earlier
                        output_gen.asend(  # spellchecker:disable-line
                            (i, stop_words))
                        usage['finish_reason'] = 'stop'
                        usage['stopped_by'] = stop_words
                        # Remove the matched stop word from completion
                        completion_without_stop = trim_last_stop(completion, [stop_words])
                        yield i, completion_without_stop, '', usage
                        return
                    if stop_type == StopMatchType.PREFIX:
                        continue
                    yield i, completion, aggregated_str, usage
                    aggregated_str = ''

            yield i, completion, aggregated_str, usage
        except AsyncEngineDeadError:
            logger.error(
                'vllm engine dead, it is upstream bug, should exit and restart')
            # TODO should clean ray cluster used when tensor_parallel_size > 1
            sys.exit(1)
