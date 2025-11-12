from dataclasses import dataclass

from inference_server.processor.preprocess import trim_fim_tokens
from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register


@register('codestral')
@dataclass
class CodeStral(VLLMGeneric):
    BOS = '<s>'
    PREFIX_TOKEN = '[PREFIX]'
    FIM_TOKEN = '[MIDDLE]'
    SUFFIX_TOKEN = '[SUFFIX]'

    def fim_prompt(self, prefix, suffix, lang=None):
        special_tokens = [
            '<FILL_ME>', self.PREFIX_TOKEN, self.FIM_TOKEN, self.SUFFIX_TOKEN
        ]
        prefix, suffix = trim_fim_tokens(prefix,
                                         suffix,
                                         special_tokens=special_tokens)
        return f'{self.BOS}{self.SUFFIX_TOKEN}{suffix}{self.PREFIX_TOKEN}{prefix}'
