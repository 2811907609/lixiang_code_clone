from dataclasses import dataclass

from inference_server.backend.common import register
from inference_server.backend.infer_engines.openaiserver import OpenAIServer


@register('sglang')
@dataclass
class SGLang(OpenAIServer):
    inf_type = 'sglang'
