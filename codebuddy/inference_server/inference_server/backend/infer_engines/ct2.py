import logging
import time
from dataclasses import dataclass

from transformers import AutoTokenizer

from inference_server.lang import get_stop_words
from inference_server.utils import find_min_index, getLogger
from inference_server.codebuddy.postprocess import trim_last_line, trim_last_stop

from inference_server.backend.basemodel import BaseModel

logger = getLogger(__name__)


@dataclass
class CT2Generic(BaseModel):
    model: None
    tokenizer: None
    inf_type = 'ct2'

    # key is openAI standard param name, value is ct2 supported param name
    params_mapping = {
        'top_p': 'sampling_topp',
        'top_k': 'sampling_topk',
        'temperature': 'sampling_temperature',
    }
    supported_params = [
        'asynchronous',
        'stops',
        'max_length',
        'include_prompt_in_result',
        'repetition_penalty',
        'length_penalty',
        'sampling_topp',
        'sampling_topk',
        'sampling_temperature',
    ]

    @classmethod
    async def new_model(cls,
                        modelpath: str,
                        trust_remote_code=True,
                        transformer_modelpath=None,
                        **kwargs):
        if not kwargs.get('dtype'):
            kwargs.pop('dtype')

        import ctranslate2
        ctranslate2.set_log_level(logging.INFO)  # more log info
        device = kwargs.get('device', 'cuda')
        dtype = kwargs.get('dtype',
                           'default')  # you can use this to quantize on loading
        max_queued_batches = kwargs.get('max_queued_batches', 0)  # default 0
        inter_threads = kwargs.get('inter_threads', 6)
        generator = ctranslate2.Generator(modelpath,
                                          device=device,
                                          compute_type=dtype,
                                          inter_threads=inter_threads,
                                          max_queued_batches=max_queued_batches)
        if hasattr(cls, 'new_tokenizer'):
            tokenizer = cls.new_tokenizer(transformer_modelpath,
                                          trust_remote_code=trust_remote_code)
        else:
            tokenizer = AutoTokenizer.from_pretrained(
                transformer_modelpath, trust_remote_code=trust_remote_code)
        return cls(model=generator, tokenizer=tokenizer)

    def _generate(self, tokens, **kwargs):
        '''ct2 default params
        max_batch_size 0
        beam_size 1
        patience 1
        num_hypotheses 1
        length_penalty 1
        repetition_penalty 1
        no_repeat_ngram_size 0
        disable_unk False
        end_token None
        return_end_token False
        max_length 512
        sampling_topk 1
        sampling_topp 1
        sampling_temperature 1
        '''
        params = {}
        for openai_param, ct2_param in self.params_mapping.items():
            if openai_param in kwargs:
                params[ct2_param] = kwargs.pop(openai_param)

        stops = kwargs.pop('stops', []) or []
        for k in self.supported_params:
            if k in kwargs:
                params[k] = kwargs[k]
        logger.info(f'llm params===============: {params}')

        output_str = ''
        output_token_ids = []

        if stops:
            # ct2 doesn't support stop token, so we use a trick to make it work
            def streaming_callback(output, *args, **kwargs):
                nonlocal output_str
                nonlocal output_token_ids
                output_token_ids.append(output.token_id)
                output_str = self.decode(output_token_ids)
                if isinstance(output_str, list) and len(output_str) > 0:
                    output_str = output_str[0]

                min_index = find_min_index(output_str, stops)
                if min_index != -1:
                    output_str = output_str[:min_index]
                    return True
        else:
            streaming_callback = None

        results = self.model.generate_batch([tokens],
                                            callback=streaming_callback,
                                            **params)
        # def sync_gen():
        #     return self.model.generate_batch([tokens],
        #         callback=streaming_callback,
        #         **kwargs)
        # loop = asyncio.get_event_loop()
        # results = await loop.run_in_executor(None, lambda: sync_gen())

        result = results[0].result()  # when asynchronous=True
        # result = results[0] # when asynchronous=False
        if stops:
            return output_str, len(output_token_ids)
        else:
            token_ids = result.sequences_ids[0]
            return self.decode(token_ids), len(token_ids)

    async def code_complete(self,
                            lang: str,
                            prefix: str,
                            suffix: str = None,
                            **kwargs):
        starttime = time.perf_counter()
        prompt, prompt_info = self.gen_prompt(lang, prefix, suffix)

        stops = kwargs.pop('stop', []) or []
        stops += get_stop_words(lang)
        stops = stops + self.stop_words()
        max_tokens = kwargs.pop('max_tokens', 64)
        tokens = self.tokenizer.convert_ids_to_tokens(
            self.tokenizer.encode(prompt))
        text, output_token_len = self._generate(tokens,
                                                asynchronous=True,
                                                stops=stops,
                                                max_length=max_tokens,
                                                include_prompt_in_result=False,
                                                **kwargs)
        # await asyncio.sleep(0.001) # give a chance for other task to run
        duration_sec = time.perf_counter() - starttime
        usage = {
            'prompt_tokens': len(tokens),  # openai field
            'completion_tokens': output_token_len,
            'total_tokens': len(tokens) + output_token_len,
            'duration_sec': duration_sec,
            'inf_type': self.inf_type,
            'prompt_compose_info': prompt_info,
        }
        text = trim_last_line(text, max_tokens, output_token_len)
        text = trim_last_stop(text, stops)
        return text, usage
