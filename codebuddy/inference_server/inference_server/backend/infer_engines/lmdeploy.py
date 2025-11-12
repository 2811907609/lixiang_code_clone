import logging
import time
import uuid
from dataclasses import dataclass

from transformers import AutoTokenizer
from openai import AsyncOpenAI

from inference_server.lang import get_stop_words
from inference_server.types import CompletionResponse
from inference_server.backend.common import register
from inference_server.backend.basemodel import BaseModel

logger = logging.getLogger(__name__)


@register('lmdeploy_generic')
@dataclass
class LMDeployGeneric(BaseModel):
    model: None
    tokenizer: None
    instance_config: None
    inf_type = 'lmdeploy'

    @classmethod
    async def new_model(cls,
                        modelpath: str,
                        instance_config=None,
                        trust_remote_code=True,
                        transformer_modelpath=None,
                        **kwargs):
        client = AsyncOpenAI(
            api_key='local_no_key',
            base_url='http://0.0.0.0:23333/v1',
        )
        tokenizer = AutoTokenizer.from_pretrained(
            transformer_modelpath, trust_remote_code=trust_remote_code)
        return cls(model=client,
                   tokenizer=tokenizer,
                   instance_config=instance_config)

    async def code_complete_v2(self,
                               lang: str,
                               prefix: str,
                               suffix: str = None,
                               model_name=None,
                               **kwargs) -> CompletionResponse:
        starttime = time.perf_counter()
        completion_id = 'cmpl-' + str(uuid.uuid4())
        prompt, prompt_info = self.gen_prompt(lang, prefix, suffix)

        stop = kwargs.pop('stop', []) or []
        stop += get_stop_words(lang)

        res = await self.model.completions.create(
            model='default',
            prompt=prompt,
            # stream=True,
        )
        # lmdeploy use sequence number from 1 and it will get repeat value
        res.id = completion_id
        duration_sec = time.perf_counter() - starttime
        if res.usage:
            res.usage.inf_type = self.inf_type
            res.usage.duration_sec = duration_sec
            res.usage.prompt_compose_info = prompt_info
        return res
