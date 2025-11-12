from dataclasses import dataclass

from inference_server.processor.preprocess import trim_fim_tokens
from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register


class LlamaBase:
    FILLME = '<FILL_ME>'

    def fim_prompt(self, prefix, suffix, lang=None):
        special_tokens = [
            self.FILLME,
        ]
        prefix, suffix = trim_fim_tokens(prefix,
                                         suffix,
                                         special_tokens=special_tokens)
        return f'{prefix}{self.FILLME}{suffix}'


@register('llama3')
@dataclass
class Llama3(VLLMGeneric, LlamaBase):
    pass
