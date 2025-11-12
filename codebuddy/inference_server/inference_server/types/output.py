import time
from typing import Optional

from pydantic import BaseModel, Field, SkipValidation
from inference_server.utils import random_uuid
from .usage import UsageInfo

# from .usage import UsageInfo

# StopReason = Literal['stop', 'length', 'stop_by_logprob', 'timeout']


class CompletionResponseChoice(BaseModel):
    index: int
    text: str
    # logprobs: Optional[LogProbs] = None
    finish_reason: Optional[str] = None

    origin_text: Optional[str] = None
    choice_info: Optional[dict] = None

    def copy_and_trim_trace_info(self):
        copied = self.model_copy()
        if copied.choice_info:
            copied.choice_info = copied.choice_info.copy()
            copied.choice_info.pop('output_stat', None)
        return copied

    def set_fix_kinds(self, kinds: set[str]):
        if kinds:
            if not self.choice_info:
                self.choice_info = dict()
            self.choice_info['fix_kinds'] = list(kinds)


class CompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"cmpl-{random_uuid()}")
    object: str = "text_completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[SkipValidation[CompletionResponseChoice]]
    usage: Optional[UsageInfo] = None
    ## finetune info
    ft_model_info: Optional[dict] = None

    def to_event(self, is_redzone=False):
        if not is_redzone:
            return self

    def copy_and_trim_trace_info(self):
        copied = self.model_copy()
        copied.ft_model_info = None
        if copied.usage:
            copied.usage = copied.usage.copy_and_trim_trace_info()
        copied.choices = [c.copy_and_trim_trace_info() for c in self.choices]
        return copied
