import asyncio
import logging
import sys
import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from inference_server.backend.basemodel import BaseModel
from inference_server.backend import get_llm
from inference_server.telemetry import collect_prompt_and_response
from inference_server.server.zed_api import setup_zed_apis
from inference_server.server.request import request_model, is_from_redzone

from .response import (
    code_complete_response,
    gen_chat_stream_response,
    gen_chat_completion,
    wrap_embed_response,
)

logger = logging.getLogger(__name__)


async def _shutdown():
    logger.info('will shutdown!!!')
    await asyncio.sleep(1)
    sys.exit(1)


async def run_server(llm: BaseModel, port=8080):
    app = FastAPI()

    setup_zed_apis(app)

    @app.api_route('/v1/health', methods=['GET', 'HEAD', 'POST'])
    async def health():
        return PlainTextResponse('ok')

    @app.post('/control/shutdown')
    async def shutdown():
        asyncio.create_task(_shutdown())
        return PlainTextResponse('will shutdown!!!')

    @app.post('/v1/embeddings')
    async def embed(request: Request):
        req = await request.json()
        input = req.get('input')

        if not is_from_redzone(request):
            logger.info(f'Received embedding request: {input}')

        model_name = req.get('model')
        model = get_llm(model_name)
        tokens = model.embed(input)
        tokens = tokens.tolist()
        res = wrap_embed_response(tokens, model_name)
        return res.model_dump()

    @app.post('/v1/reranking')
    async def reranking(request: Request):
        req = await request.json()
        query = req.get('query')
        inputs = req.get('inputs')
        model_name = req.get('model')
        model = get_llm(model_name)
        scores = model.predict_scores(query, inputs)
        response = dict(scores=scores)
        return response

    @app.post('/v1/completions')
    async def complete(request: Request):
        req = await request.json()
        lang = req.pop('language', '')
        segments = req.pop('segments', {})
        extra = req.pop('extra') or {}
        enable_model_params_config = extra.get('enable_model_params_config', False)
        no_prompt_cutoff = enable_model_params_config
        prefix = segments.get('prefix', '') or ''
        suffix = segments.get('suffix', '') or ''
        prompt = req.pop('prompt', '') or ''
        if prompt and (not prefix):
            prefix = prompt

        logger.info(f'completion request: lang, {lang}')
        if not is_from_redzone(request):
            logger.info(f'completion request: params, {req}')
            # avoid log too much lines
            logger.info(f'completion request: prefix\n{prefix[-400:]}')
            logger.info(f'completion request: suffix\n{suffix[:100]}')

        async def should_abort():
            if await request.is_disconnected():
                logger.info('client connection aborted.')
                return True, 'conn_closed'
            return False, ''

        s = ''
        try:
            name = request_model(request)
            body = await asyncio.wait_for(llm.code_complete_v2(
                lang,
                prefix,
                suffix,
                model_name=name,
                no_prompt_cutoff=no_prompt_cutoff,
                should_abort=should_abort,
                **req),
                                            timeout=8)
            body.model = name

            if not is_from_redzone(request):
                asyncio.create_task(
                    collect_prompt_and_response(body.id, completion=body))

            trimmed_body = body.copy_and_trim_trace_info()
            return trimmed_body
        except asyncio.TimeoutError:
            print('get timeout')
        return code_complete_response(s)

    @app.post('/v1/chat/completions')
    async def chat_complete(request: Request):
        req = await request.json()
        is_redzone = is_from_redzone(request)
        stream = req.pop('stream', False)
        messages = req.pop('messages', []) or []
        s = ''
        usage = {}
        request_id = 'cmpl-' + str(uuid.uuid4())
        model = request_model(request)
        created_time = int(time.monotonic())

        if stream:

            async def stream_generator():
                final_usage = {}
                async for s, usage in llm.chat_complete(messages,
                                                        stream=True,
                                                        is_redzone=is_redzone,
                                                        **req):
                    chunk = gen_chat_stream_response(s,
                                                     request_id=request_id,
                                                     model_name=model,
                                                     created_time=created_time,
                                                     usage={})
                    chunk = chunk.copy_and_trim_trace_info()
                    chunkBytes = chunk.model_dump_json().encode('utf-8')
                    yield b'data: ' + chunkBytes + b'\n\n'
                    final_usage = usage

                # send a final chunk with usage, content should be empty
                chunk = gen_chat_stream_response('',
                                                 request_id=request_id,
                                                 model_name=model,
                                                 created_time=created_time,
                                                 usage=final_usage)
                chunk = chunk.copy_and_trim_trace_info()
                chunkBytes = chunk.model_dump_json().encode('utf-8')
                yield b'data: ' + chunkBytes + b'\n\n'

                yield b'data: [DONE]\n\n'

            return StreamingResponse(content=stream_generator(),
                                     media_type='text/event-stream')
        try:
            s, usage = await asyncio.wait_for(anext(
                llm.chat_complete(messages, is_redzone=is_redzone, **req)),
                                              timeout=30)
        except asyncio.TimeoutError:
            print('get timeout')
        res = gen_chat_completion(s, usage, model=model)
        return res

    # when deploy multiple embedding models, llm is None
    if llm and isinstance(llm, BaseModel):
        subapp = llm.subapp()
        if subapp:
            app.mount('/vllm', subapp)

    # use uvicorn.run will block llm engine in ipython since ipython also
    # has its own async loop
    # uvicorn.run(app, host='0.0.0.0', port=int(port))
    uvicorn_config = uvicorn.Config(app, host='0.0.0.0', port=int(port))
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()
