from typing import Optional
from pydantic import BaseModel
from .runtime import RuntimeInfo


class BenchmarkItem(BaseModel):
    runtime_info: RuntimeInfo

    epoch: Optional[float] = None
    modeltype: Optional[str] = None
    modelpath: Optional[str] = None
    modelname: Optional[str] = None
    modelsize: Optional[str] = None

    benchmark_time: str
    input_len: int
    max_new_tokens: int
    total_completion_tokens: int
    iterations: int

    walltime_duration: float
    tokens_per_second: float
    latency_sec: float
    first_token_latency: Optional[float] = None  # in ms
    per_token_time: float = None  # in ms

    use_dummy_tokenizer: bool = False
