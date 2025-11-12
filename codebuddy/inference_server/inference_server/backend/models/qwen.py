from dataclasses import dataclass

from inference_server.processor.preprocess import trim_fim_tokens
from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register


@register('qwen')
@dataclass
class Qwen(VLLMGeneric):
    """generic QWen, not QwenCoder. It doesn't support FIM. Mostly used for chat.
    Just inherit VLLMGeneric atm."""
    pass


class QwenCoderBase:
    PREFIX_TOKEN = '<|fim_prefix|>'
    FIM_TOKEN = '<|fim_middle|>'
    SUFFIX_TOKEN = '<|fim_suffix|>'

    def fim_prompt(self, prefix, suffix, lang=None):
        special_tokens = [
            '<FILL_ME>', self.PREFIX_TOKEN, self.FIM_TOKEN, self.SUFFIX_TOKEN
        ]
        prefix, suffix = trim_fim_tokens(prefix,
                                         suffix,
                                         special_tokens=special_tokens)
        return f'{self.PREFIX_TOKEN}{prefix}{self.SUFFIX_TOKEN}{suffix}{self.FIM_TOKEN}'


@register('qwen_coder')
@dataclass
class QwenCoder(VLLMGeneric, QwenCoderBase):
    pass

@register('qwen3coder')
@dataclass
class Qwen3Coder(VLLMGeneric):
    force_fim = True
    PREFIX_TOKEN = '<|fim_prefix|>'
    FIM_TOKEN = '<|fim_middle|>'
    SUFFIX_TOKEN = '<|fim_suffix|>'

    SYSTEM_PROMPT = """You are a raw code completion assistant.
Output ONLY the missing code fragment - no markdown, no ```, no language tags, no explanations.
The response must be directly insertable between the prefix and suffix code.
Never wrap the code in any formatting or markers."""

    def stop_words(self):
        return ['\n```', self.PREFIX_TOKEN, self.FIM_TOKEN, self.SUFFIX_TOKEN, '<|fim_pad|>', '<|repo_name|>', '<|file_sep|>', '<|endoftext|>', '<|im_end|>']

    def fim_prompt(self, prefix, suffix, lang=None):
        special_tokens = [
            '<FILL_ME>', self.PREFIX_TOKEN, self.FIM_TOKEN, self.SUFFIX_TOKEN
        ]
        prefix, suffix = trim_fim_tokens(prefix,
                                         suffix,
                                         special_tokens=special_tokens)
        fim_content = f'{self.PREFIX_TOKEN}{prefix}{self.SUFFIX_TOKEN}{suffix}{self.FIM_TOKEN}'
        chat_messages = f'''<|im_start|>system
{self.SYSTEM_PROMPT}<|im_end|>
<|im_start|>user
{fim_content}<|im_end|>
<|im_start|>assistant
```{lang}
'''
        return chat_messages
