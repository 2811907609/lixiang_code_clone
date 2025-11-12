import logging
from dataclasses import dataclass
from threading import Thread

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer

from inference_server.lang import get_stop_words
from inference_server.backend.common import register
from inference_server.backend.basemodel import BaseModel
from inference_server.codebuddy.postprocess import (
    trim_last_line,
    trim_last_stop,
    StopMatchType,
    get_stop_match_type,
)

from inference_server.types import (
    CompletionResponseChoice,
    CompletionResponse,
)

logger = logging.getLogger(__name__)


class StoppingCriteriaSub(StoppingCriteria):

    def __init__(self, prompt_len=0, stop_words=None, tokenizer=None):
        super().__init__()
        self.prompt_len = prompt_len
        self.stop_words = stop_words or []
        self.tokenizer = tokenizer

    def __call__(self, output_ids: torch.LongTensor, scores: torch.FloatTensor):
        text = self.tokenizer.batch_decode(output_ids)[0]
        text = text[self.prompt_len:]
        for word in self.stop_words:
            idx = text.find(word)
            if idx >= 0:
                return True
        return False


@register('transformer_generic')
@dataclass
class TransformersGeneric(BaseModel):
    model: None
    tokenizer: None
    instance_config: None
    inf_type = 'transformers'

    @classmethod
    async def new_model(cls,
                        modelpath: str,
                        trust_remote_code=True,
                        instance_config=None,
                        **kwargs):
        dtype = kwargs.pop('dtype', None)
        if hasattr(cls, 'new_tokenizer'):
            tokenizer = cls.new_tokenizer(modelpath,
                                          trust_remote_code=trust_remote_code)
        else:
            tokenizer = AutoTokenizer.from_pretrained(
                modelpath,
                # torch_dtype=torch_dtype,
                trust_remote_code=trust_remote_code)
        model_supported_param_keys = ['attn_implementation', 'load_in_8bit']
        model_params = {
            k: kwargs[k] for k in model_supported_param_keys if k in kwargs
        }
        if dtype:
            torch_dtype = getattr(torch, dtype)
            model_params['torch_dtype'] = torch_dtype
        model = AutoModelForCausalLM.from_pretrained(
            modelpath,
            # load_in_4bit=True,
            trust_remote_code=trust_remote_code,
            **model_params)
        # for deepseek only
        model.generation_config.pad_token_id = model.generation_config.eos_token_id
        if 'load_in_8bit' not in model_params:
            model = model.to('cuda')
        return cls(model=model,
                   tokenizer=tokenizer,
                   instance_config=instance_config)

    async def code_complete_v2(self,
                               lang: str,
                               prefix: str,
                               suffix: str = None,
                               **kwargs) -> CompletionResponse:
        prompt, _ = self.gen_prompt(lang, prefix, suffix)
        max_tokens = kwargs.get('max_tokens', 64)
        tokens = self.tokenizer(prompt,
                                return_tensors='pt',
                                return_attention_mask=False).to('cuda')
        input_len = tokens['input_ids'].shape[1]
        stop = kwargs.pop('stop', []) or []
        stop += get_stop_words(lang)
        stop += self.stop_words()
        stopping_criteria = StoppingCriteriaList([
            StoppingCriteriaSub(prompt_len=len(prompt),
                                stop_words=stop,
                                tokenizer=self.tokenizer)
        ])
        outputs = self.model.generate(**tokens,
                                      max_new_tokens=max_tokens,
                                      pad_token_id=self.tokenizer.eos_token_id,
                                      stopping_criteria=stopping_criteria)
        # transformers has a weird logic, that it will remove the first whitespace
        if hasattr(self, 'decode'):
            text = self.decode(outputs[0][input_len:])
        else:
            text = self.tokenizer.decode(outputs[0][input_len:])
        text = trim_last_line(text, max_tokens, outputs.shape[1] - input_len)
        text = trim_last_stop(text, stop)
        choice = CompletionResponseChoice(index=1, text=text)
        res = CompletionResponse(model='', choices=[choice], usage={})
        return res

    async def chat_complete(self, messages, **kwargs):
        max_tokens = kwargs.pop('max_tokens', 2048)
        stop = kwargs.pop('stop', []) or []
        stop += get_stop_words('')
        prompt = self.tokenizer.apply_chat_template(messages,
                                                    add_generation_prompt=True,
                                                    tokenize=False)
        logger.info(f'prompt { prompt }')
        if kwargs.get('stream'):
            for s in self.stream_output(prompt, max_tokens, stop=stop):
                if not s:
                    continue
                yield s, {}
        else:
            output_text = ''
            for s in self.stream_output(prompt, max_tokens, stop=stop):
                if not s:
                    continue
                output_text += s
            yield output_text, {}

    def stream_output(self, prompt, max_new_tokens, stop=None, **kwargs):
        inputs = self.tokenizer([prompt],
                                add_special_tokens=False,
                                return_tensors='pt').to('cuda')
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(
            inputs,
            streamer=streamer,
            max_new_tokens=max_new_tokens,
            pad_token_id=self.tokenizer.eos_token_id,
            # eos_token_id=self.tokenizer.eos_token_id,
            use_cache=True,
        )
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        aggregated_str = ''
        for t in streamer:
            if not t:
                continue
            if not stop:
                yield t
            for ch in t:
                aggregated_str += ch
                stop_type, _ = get_stop_match_type(aggregated_str, stop)
                if stop_type == StopMatchType.WHOLE:
                    yield ''
                    return
                if stop_type == StopMatchType.PREFIX:
                    continue
                yield aggregated_str
                aggregated_str = ''
        yield aggregated_str

        thread.join(60)
