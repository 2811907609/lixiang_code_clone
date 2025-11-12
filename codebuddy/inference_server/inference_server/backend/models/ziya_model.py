from inference_server.backend.vllm import VLLMGeneric
from inference_server.backend.common import register


class ZiyaBase:
    CHAT_TEMPLATE = '''
{%- for message in messages -%}
    {%- if message['role'] == 'user' -%}
        {{- '<human>: ' + message['content'] + ' ' -}}
    {%- elif message['role'] == 'assistant' -%}
        {{- '<bot>: ' + message['content'] + ' ' -}}
    {%- endif -%}
{%- endfor -%}

{%- if add_generation_prompt -%}
    {{- '<bot>:' -}}
{% endif %}
'''


@register('vllm_ziya')
class VLLMZiya(VLLMGeneric, ZiyaBase):

    def default_chat_params(self):
        return dict(
            repetition_penalty=1.1,
            temperature=0.7,
        )
