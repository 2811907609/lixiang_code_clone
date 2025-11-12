
from dataclasses import dataclass

from inference_server.backend.common import register
from inference_server.backend.vllm import VLLMGeneric

# https://huggingface.co/agentica-org/DeepSWE-Preview

@register('deepswe')
@dataclass
class DeepSWE(VLLMGeneric):
    """DeepSWE-Preview is trained on top of Qwen3-32B with thinking mode enabled.
    With just 200 steps of RL training, SWE-Bench-Verified score increases by ~20%."""
    pass
