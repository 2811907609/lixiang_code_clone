from typing import Optional

from pydantic import BaseModel

from .completion import PromptComposeInfo
from .output_stat import OutputStat


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0
    completion_tokens: Optional[int] = 0
    decoding_steps: Optional[int] = None
    # 以下非官方字段，用于记录一些debug信息
    inf_type: Optional[str] = None
    duration_sec: Optional[float] = None
    prompt_compose_info: Optional[PromptComposeInfo] = None
    output_stat: Optional[OutputStat] = None
    abtest: Optional[dict] = None

    def copy_and_trim_trace_info(self):
        copied = self.model_copy()
        copied.output_stat = None
        copied.prompt_compose_info = None
        return copied
