import logging
from dataclasses import dataclass

from transformers import CodeLlamaTokenizer

from inference_server.tokenizer import codellama_decode
from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register
from inference_server.backend.infer_engines.ct2 import CT2Generic
from inference_server.backend.infer_engines.tensorrtllm import TensorRTLLM
from .transformers import TransformersGeneric

logger = logging.getLogger(__name__)


class CodellamaBase:

    @classmethod
    def new_tokenizer(cls, modelpath: str, trust_remote_code=True, **kwargs):
        t = CodeLlamaTokenizer.from_pretrained(
            modelpath, trust_remote_code=trust_remote_code)
        return t

    def fim_prompt(self, prefix, suffix, lang=None):
        # format as "<PRE> {pre} <SUF>{suf} <MID>"
        # return f'<PRE> {prefix} <SUF>{suffix} <MID>'
        fillme = '<FILL_ME>'
        # fix bug in transforms when prefix or suffix has <FILL_ME>
        # code in transformers: text, text_pair = text.split(self.fill_token)
        if fillme in prefix:
            prefix = prefix.replace(fillme, 'FILLME')
        if not suffix:
            return prefix
        if fillme in suffix:
            suffix = suffix.replace(fillme, 'FILLME')
        return f'{prefix}{fillme}{suffix}'


@register('codellama_transformers')
class CodellamaTransformers(TransformersGeneric, CodellamaBase):

    def decode(self, token_ids, **kwargs):
        return codellama_decode(self.tokenizer, token_ids)


@register('ct2_codellama')
class CT2Codellama(CT2Generic, CodellamaBase):

    def gen_prompt_header(self, lang: str) -> str:
        ''' disable language prompt for codellama (we found it give bad result)'''
        return ''

    def decode(self, token_ids, **kwargs):
        return codellama_decode(self.tokenizer, token_ids)


@register('vllm_codellama')
@dataclass
class CodellamaVLLM(VLLMGeneric, CodellamaBase):
    model: None
    tokenizer: None
    use_default_system_prompt = True


@register('trt_codellama')
@dataclass
class CodellamaTRT(TensorRTLLM, CodellamaBase):
    pass
