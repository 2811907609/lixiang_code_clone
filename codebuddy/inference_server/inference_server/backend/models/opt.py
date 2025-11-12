from dataclasses import dataclass

from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register


class OptBase:
    CHAT_TEMPLATE = '''
{%- for message in messages -%}
    {%- if message['role'] == 'user' -%}
        {{- 'Question: ' + message['content'] + ' ' -}}
    {%- elif message['role'] == 'assistant' -%}
        {{- 'Answer: ' + message['content'] + ' ' -}}
    {%- endif -%}
{%- endfor -%}

{%- if add_generation_prompt -%}
    {{- 'Answer:' -}}
{% endif %}
'''


@register('opt')
@dataclass
class Opt(VLLMGeneric, OptBase):
    pass


'''
from inference_server.backend.infer_engines.sglang import SGLang

@register('opt_sglang')
@dataclass
class OptSGLang(SGLang, OptBase):
    # sglang do not support opt currently
    raise NotImplementedError
'''
