# this is for vLLM V1

import logging
from typing import List, Optional, Set, Tuple

import numpy as np
import torch
from inference_server.backend.state import request_manager
from inference_server.modules.specedit.lib.constant import (
    is_ngram_spec_enabled,
    is_spec_edit_enabled,
    original_worker_key,
)
from vllm import spec_decode
from vllm.model_executor.layers.sampler import SamplerOutput
from vllm.sequence import ExecuteModelRequest
from vllm.spec_decode.ngram_worker import NGramWorker

logger = logging.getLogger(__name__)


class SpecEditWorker(NGramWorker):

    def sampler_output(
        self,
        execute_model_req: ExecuteModelRequest,
        sample_len: int,
        # Unused parameter. NGramWorker does not use the KV Cache and
        # therefore does not need this parameter.
        seq_ids_with_bonus_token_in_last_step: Set[int],
    ) -> Tuple[Optional[List[Optional[SamplerOutput]]], bool]:
        """SpecEditWorker use original text as draft.
        """

        if not is_spec_edit_enabled():
            original_ngram_worker = get_original_ngram_worker()
            return original_ngram_worker.sampler_output(
                self, execute_model_req, sample_len,
                seq_ids_with_bonus_token_in_last_step)

        self._raise_if_unsupported(execute_model_req)

        has_spec_out = False
        token_id_list: List[Optional[torch.Tensor]] = []
        token_prob_list: List[Optional[torch.Tensor]] = []
        for _, seq_group_metadata in enumerate(
                execute_model_req.seq_group_metadata_list):
            request_id = seq_group_metadata.request_id
            stream_next_chunk = request_manager.get_stream_next_chunk(
                request_id)
            if not stream_next_chunk:
                token_id_list.append(None)
                token_prob_list.append(None)
                continue

            seq_data = next(iter(seq_group_metadata.seq_data.values()))
            # we use CPU since the text is often very long
            output_ids = seq_data.output_token_ids

            next_chunk_ids = stream_next_chunk.next_chunk(
                list(output_ids), sample_len)
            if len(next_chunk_ids) == 0:
                token_id_list.append(None)
                token_prob_list.append(None)
                continue
            next_chunk_ids = next_chunk_ids[:sample_len]
            # fill to fixed length
            if isinstance(next_chunk_ids, np.ndarray):
                last_val = next_chunk_ids[-1]
                next_chunk_ids = np.pad(
                    next_chunk_ids,
                    (0, sample_len - len(next_chunk_ids)),
                    mode="constant",
                    constant_values=last_val,
                )
                next_chunk_ids = torch.from_numpy(next_chunk_ids).to(
                    device=self.device, dtype=torch.long)
            else:
                if len(next_chunk_ids) < sample_len:
                    next_chunk_ids = next_chunk_ids + [next_chunk_ids[-1]] * (
                        sample_len - len(next_chunk_ids))
                next_chunk_ids = torch.tensor(next_chunk_ids,
                                              device=self.device,
                                              dtype=torch.long)

            token_id_list.append(next_chunk_ids)
            token_prob_list.append(
                torch.nn.functional.one_hot(next_chunk_ids,
                                            num_classes=self.vocab_size).to(
                                                torch.float32))
            has_spec_out = True

        if (not has_spec_out) and is_ngram_spec_enabled():
            original_ngram_worker = get_original_ngram_worker()
            return original_ngram_worker.sampler_output(
                self, execute_model_req, sample_len,
                seq_ids_with_bonus_token_in_last_step)

        if not is_ngram_spec_enabled():
            return None, None

        outputs: List[Optional[SamplerOutput]] = []
        for idx in range(len(execute_model_req.seq_group_metadata_list)):
            if token_id_list[idx] is None:
                outputs.append(None)
            else:
                outputs.append(
                    SamplerOutput(
                        outputs=None,
                        sampled_token_probs=token_prob_list[idx],
                        logprobs=torch.zeros((sample_len, self.vocab_size),
                                             dtype=torch.float32,
                                             device=self.device),
                        sampled_token_ids=token_id_list[idx],
                    ))

        return outputs, False

def patch_spec_edit_v0():
    from inference_server.modules.specedit.lib.spec_edit_worker_v0 import (
        SpecEditWorker,
    )

    if not hasattr(spec_decode, original_worker_key):
        setattr(spec_decode, original_worker_key, NGramWorker)
    spec_decode.ngram_worker.NGramWorker = SpecEditWorker
    logger.info(f'spec edit patched, now is {SpecEditWorker.__name__}')



def get_original_ngram_worker():
    """Returns the original NGramWorker class."""
    if hasattr(spec_decode, original_worker_key):
        return getattr(spec_decode, original_worker_key)
    return NGramWorker
