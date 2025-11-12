from dataclasses import dataclass

from inference_server.backend.common import register
from inference_server.backend.vllm import VLLMGeneric


def gen_edit_prediction_prompt(input_events: str, input_excerpt: str,
                               speculated_output: str=''):
    return f'''Instruction:
You are a code completion assistant and your task is to analyze user edits and then rewrite an excerpt that the user provides, suggesting the appropriate edits within the excerpt, taking into account the cursor location.

User Edits:
{input_events}

User Excerpt:
{input_excerpt}

Response:
'''


@register('zed')
@dataclass
class ZedModel(VLLMGeneric):

    async def raw_generate(self,
                           _prompt,
                           *args,
                           max_tokens=600,
                           original_draft_text=None,
                           **kwargs):
        input_events = kwargs.get('input_events', '')
        input_excerpt = kwargs.get('input_excerpt', '')
        speculated_output = kwargs.get('speculated_output', '')
        prompt = gen_edit_prediction_prompt(input_events, input_excerpt,
                                            speculated_output)

        res = await self.generate_no_stream(
            prompt,
            max_tokens=max_tokens,
            original_draft_text=original_draft_text,
            disable_multi_stop_words=True,
            **kwargs)
        return res
