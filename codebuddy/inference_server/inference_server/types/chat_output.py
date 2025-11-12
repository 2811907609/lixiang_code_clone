import time
from typing import List, Optional

from pydantic import BaseModel, Field

from inference_server.utils import random_uuid

from .usage import UsageInfo


class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionResponseStreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[str] = None

    def copy_and_trim_trace_info(self):
        copied = self.model_copy()
        return copied


class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{random_uuid()}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseStreamChoice]
    usage: Optional[UsageInfo] = Field(
        default=None, description="data about request and response")

    def copy_and_trim_trace_info(self):
        copied = self.model_copy()
        # if copied.usage:
        #     copied.usage = copied.usage.copy_and_trim_trace_info()
        copied.choices = [c.copy_and_trim_trace_info() for c in self.choices]
        return copied
