
# this is for vLLM V1

from typing import Optional

import numpy as np
from vllm.distributed.parallel_state import get_pp_group
from vllm.v1.spec_decode.ngram_proposer import NgramProposer
from vllm.v1.worker.gpu_model_runner import GPUModelRunner

from inference_server.backend.state import request_manager
from inference_server.modules.specedit.lib.constant import (
    is_ngram_spec_enabled,
    is_spec_edit_enabled,
)
from inference_server.utils import getLogger

logger = getLogger(__name__)


class MockVllmConfig:
    """Minimal config object to create NgramProposer without full VllmConfig"""
    def __init__(self, min_n=2, max_n=5, num_speculative_tokens=5, max_model_len=8192):
        self.speculative_config = MockSpeculativeConfig(min_n, max_n, num_speculative_tokens)
        self.model_config = MockModelConfig(max_model_len)


class MockSpeculativeConfig:
    def __init__(self, min_n, max_n, num_speculative_tokens):
        self.prompt_lookup_min = min_n
        self.prompt_lookup_max = max_n
        self.num_speculative_tokens = num_speculative_tokens


class MockModelConfig:
    def __init__(self, max_model_len):
        self.max_model_len = max_model_len


def create_ngram_proposer(min_n=2, max_n=5, num_speculative_tokens=5, max_model_len=8192):
    """Create NgramProposer instance without VllmConfig

    Args:
        min_n: Minimum length of the n-gram to match (default: 2)
        max_n: Maximum length of the n-gram to match (default: 5)
        num_speculative_tokens: Number of tokens to propose (default: 5)
        max_model_len: Maximum model length (default: 8192)

    Returns:
        NgramProposer instance
    """
    mock_config = MockVllmConfig(min_n, max_n, num_speculative_tokens, max_model_len)
    return NgramProposer(mock_config)


class SpecEditProposer(NgramProposer):
    def propose(
        self,
        context_token_ids: np.ndarray,
        output_token_ids: list[int]=None,
        req_id: str=None,
    ) -> Optional[np.ndarray]:
        return spec_edit_propose(self,
                                 context_token_ids,
                                 output_token_ids=output_token_ids,
                                 req_id=req_id)


def spec_edit_propose(instance: SpecEditProposer,
        context_token_ids: np.ndarray,
        output_token_ids: list[int]=None,
        req_id: str=None,
    ) -> Optional[np.ndarray]:
    logger.debug('================ ngram proposer')
    if req_id is None:
        return NgramProposer.propose(instance, context_token_ids)

    # 如果spec edit 在runtime disable了，直接fallback到 ngram
    if not is_spec_edit_enabled():
        # 如果 ngram 也disable了，直接返回 None（无草稿）
        if not is_ngram_spec_enabled():
            return None
        return NgramProposer.propose(instance, context_token_ids)

    stream_next_chunk = request_manager.get_stream_next_chunk(req_id)
    if not stream_next_chunk:
        logger.debug(f"stream_next_chunk not found for req_id {req_id}")
        return NgramProposer.propose(instance, context_token_ids)

    # Do not generate draft tokens beyond the max model length.
    k = min(instance.k, instance.max_model_len - context_token_ids.shape[0])
    if k <= 0:
        return None

    if output_token_ids is None:
        output_token_ids = []
    next_chunk_ids = stream_next_chunk.next_chunk(
        output_token_ids, k)

    if len(next_chunk_ids) == 0:
        return NgramProposer.propose(instance, context_token_ids)

    return np.array(next_chunk_ids[:k])


# patch the GPUModelRunner to add req_id to ngram propose method

class PatchGPUModelRunner(GPUModelRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # use specedit drafter
        if self.speculative_config and get_pp_group().is_last_rank:
            if self.speculative_config.method == "ngram":
                self.drafter = SpecEditProposer(self.vllm_config)

    def propose_ngram_draft_token_ids(
        self,
        sampled_token_ids: list[list[int]],
    ) -> list[list[int]]:
        # TODO(woosuk): Optimize.
        draft_token_ids: list[list[int]] = []
        for i, sampled_ids in enumerate(sampled_token_ids):
            num_sampled_ids = len(sampled_ids)
            if not num_sampled_ids:
                # Skip speculative decoding.
                draft_token_ids.append([])
                continue

            # Skip requests that require sampling parameters that are not
            # supported with speculative decoding.
            req_id = self.input_batch.req_ids[i]
            if req_id in self.input_batch.spec_decode_unsupported_reqs:
                draft_token_ids.append([])
                continue

            num_tokens = self.input_batch.num_tokens_no_spec[i]
            if num_tokens >= self.max_model_len:
                # Skip requests that have already reached the max model length.
                draft_token_ids.append([])
                continue

            output_token_ids = self.input_batch.req_output_token_ids[i]
            drafter_output = self.drafter.propose(
                self.input_batch.token_ids_cpu[i, :num_tokens],
                output_token_ids=output_token_ids,
                req_id=req_id)
            if drafter_output is None or len(drafter_output) == 0:
                draft_token_ids.append([])
            else:
                draft_token_ids.append(drafter_output.tolist())
        return draft_token_ids


def patch_spec_edit_v1():
    patch_gpu_model_runner()


def patch_gpu_model_runner():
    from vllm.v1.worker import gpu_model_runner
    if not hasattr(gpu_model_runner, 'OriginalGPUModelRunner'):
        gpu_model_runner.OriginalGPUModelRunner = gpu_model_runner.GPUModelRunner
    gpu_model_runner.GPUModelRunner = PatchGPUModelRunner
    logger.info(f'GPUModelRunner patched, now is {PatchGPUModelRunner.__name__}')
