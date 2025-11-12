import asyncio
from dataclasses import dataclass

from inference_server.backend.common import register


class Dummy:
    pass


class FakeEngine():
    is_running = True

    async def generate(self, *args, **kwargs):
        for i in range(1, 20):
            await asyncio.sleep(0.1)
            out = Dummy()
            out.text = f'hello {i}'
            out.token_ids = [1] * 10
            outputs = Dummy()
            outputs.prompt_token_ids = [1] * 10
            outputs.outputs = [out]
            yield outputs


# class FakeVLLM(VLLMGeneric):
@register('vllm_fake')
@dataclass
class FakeVLLM:
    model: None
    tokenizer: None

    @classmethod
    async def new_model(cls, *args, **kwargs):
        return FakeVLLM(FakeEngine(), tokenizer=None)

    async def code_complete(self,
                            lang: str,
                            prefix: str,
                            suffix: str = None,
                            **kwargs):
        await asyncio.sleep(0.1)
        return 'hello world', {}
