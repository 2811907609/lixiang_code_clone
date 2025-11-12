import asyncio
import time
from dataclasses import dataclass

import torch

from transformers import AutoTokenizer

from inference_server.utils import getLogger, random_uuid
from inference_server.types.usage import UsageInfo
from inference_server.backend.basemodel import BaseModel

from inference_server.types import (
    CompletionResponseChoice,
    CompletionResponse,
)

try:
    import tensorrt_llm
    from tensorrt_llm.runtime import ModelRunner
except ImportError:
    print("TensorRT-LLM not installed")

logger = getLogger(__name__)
'''
https://github.com/NVIDIA/TensorRT-LLM/blob/main/examples/run.py
'''


@dataclass
class TensorRTLLM(BaseModel):
    model: None
    tokenizer: None
    instance_config: None
    inf_type = 'trt'

    @classmethod
    async def new_model(cls,
                        modelpath: str,
                        instance_config=None,
                        tokenizer_path: str = None,
                        trust_remote_code: bool = True,
                        **kwargs):
        runtime_rank = tensorrt_llm.mpi_rank()
        logger.info(
            f'TensorRTLLM model with modelpath: {modelpath}  and tokenizer_path: {tokenizer_path} kwargs: {kwargs}'
        )
        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path, trust_remote_code=trust_remote_code)
        runner_cls = ModelRunner
        runner_kwargs = dict(engine_dir=modelpath, rank=runtime_rank)
        runner = runner_cls.from_dir(**runner_kwargs)
        return cls(model=runner,
                   tokenizer=tokenizer,
                   instance_config=instance_config)

    async def code_complete_v2(self,
                               lang: str,
                               prefix: str,
                               suffix: str,
                               max_tokens: int = 128,
                               temperature: float = 0.01,
                               top_p: float = 0.9,
                               **kwargs):
        await asyncio.sleep(0.001)
        starttime = time.perf_counter()
        tokenizer = self.tokenizer
        prompt, prompt_info = self.gen_prompt(lang, prefix, suffix)
        input_ids = tokenizer.encode(prompt,
                                     add_special_tokens=True,
                                     truncation=True)
        batch_input_ids = [torch.tensor(input_ids, dtype=torch.int32)]
        input_len = len(input_ids)
        pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
        with torch.no_grad():
            outputs = self.model.generate(
                batch_input_ids,
                max_new_tokens=max_tokens,
                pad_id=pad_id,
                end_id=tokenizer.eos_token_id,
                temperature=temperature,
                top_p=top_p,
                output_sequence_lengths=True,
                return_dict=True,
            )
            torch.cuda.synchronize()

        output_ids = outputs['output_ids'][0][0]

        print(f'output==========={output_ids}')
        output_text = tokenizer.decode(output_ids[input_len:])
        completion_id = f'cmpl-{random_uuid()}'
        choice = CompletionResponseChoice(
            index=0,
            text=output_text,
        )
        duration_sec = time.perf_counter() - starttime
        usage = UsageInfo(
            prompt_tokens=input_len,
            completion_tokens=len(output_ids) - input_len,
            total_tokens=len(output_ids),
            inf_type=self.inf_type,
            duration_sec=duration_sec,
            prompt_compose_info=prompt_info,
        )
        return CompletionResponse(id=completion_id,
                                  model='',
                                  choices=[choice],
                                  usage=usage)
