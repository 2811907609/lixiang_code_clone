import uuid
from typing import List

from inference_server.types import ChatCompletionResponseStreamChoice, ChatCompletionStreamResponse, DeltaMessage
from .types import EmbedChoice, EmbedResponse


def wrap_embed_response(tokens: List[float] | List[List[float]], model):
    data = []
    if isinstance(tokens[0], list):
        data = [
            EmbedChoice(index=i, embedding=tokens[i])
            for i in range(len(tokens))
        ]
    else:
        data = [EmbedChoice(index=0, embedding=tokens)]
    res = EmbedResponse(data=data, model=model)
    return res


def code_complete_response(text: str):
    choice = dict(index=0, text=text)
    id = 'cmpl-' + str(uuid.uuid4())
    body = dict(id=id, choices=[choice])
    return body


def gen_chat_completion(text: str, usage: dict, model=None):
    message = {
        'role': 'assistant',
        'content': text,
    }
    choice = dict(index=0, message=message)
    id = 'cmpl-' + str(uuid.uuid4())
    return dict(id=id, choices=[choice], model=model, usage=usage)


def gen_chat_stream_response(text: str,
                             model_name='',
                             request_id='',
                             created_time=None,
                             usage: dict = None):
    chunk_object_type = "chat.completion.chunk"
    choice_data = ChatCompletionResponseStreamChoice(
        index=0, delta=DeltaMessage(content=text), finish_reason=None)
    chunk = ChatCompletionStreamResponse(id=request_id,
                                         object=chunk_object_type,
                                         created=created_time,
                                         choices=[choice_data],
                                         model=model_name or '')
    if usage:
        chunk.usage = usage
    else:
        chunk.usage = {}
    return chunk
