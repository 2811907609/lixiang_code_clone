from dataclasses import dataclass

from inference_server.processor.preprocess import trim_fim_tokens
from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register
from inference_server.backend.infer_engines.sglang import SGLang
from .transformers import TransformersGeneric


class DeepseekCoderBase:
    PREFIX_TOKEN = '<｜fim▁begin｜>'
    FIM_TOKEN = '<｜fim▁hole｜>'
    SUFFIX_TOKEN = '<｜fim▁end｜>'

    def fim_prompt(self, prefix, suffix, lang=None):
        special_tokens = [
            '<FILL_ME>', self.PREFIX_TOKEN, self.FIM_TOKEN, self.SUFFIX_TOKEN
        ]
        prefix, suffix = trim_fim_tokens(prefix,
                                         suffix,
                                         special_tokens=special_tokens)
        return f'{self.PREFIX_TOKEN}{prefix}{self.FIM_TOKEN}{suffix}{self.SUFFIX_TOKEN}'


@register('deepseek_coder')
@dataclass
class DeepseekCoder(VLLMGeneric, DeepseekCoderBase):
    force_fim = True # force use fim even if there is no suffix


@register('deepseek_coder_sglang')
@dataclass
class DeepseekCoderSGLang(SGLang, DeepseekCoderBase):
    pass


@register('deepseek_coder_transformers')
@dataclass
class DeepseekCoderTransformers(TransformersGeneric, DeepseekCoderBase):
    pass
