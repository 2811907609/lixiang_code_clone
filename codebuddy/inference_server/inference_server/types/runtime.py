from typing import Optional
from pydantic import BaseModel


class RuntimeInfo(BaseModel):
    device: str
    torch_version: str
    cuda_version: str
    vllm_version: Optional[str] = None
    inf_type: Optional[str] = None
