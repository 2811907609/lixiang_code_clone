from typing import List, Optional

from pydantic import BaseModel

from inference_server.types.usage import UsageInfo


class EmbedChoice(BaseModel):
    index: int
    object: str = "embedding"
    embedding: List[float]


class EmbedResponse(BaseModel):
    object: str = "list"
    data: List[EmbedChoice]
    model: str
    usage: Optional[UsageInfo] = None
