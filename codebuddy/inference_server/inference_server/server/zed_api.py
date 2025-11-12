import asyncio
import logging
import os
import random
import time
import uuid

from fastapi import FastAPI, Request

from inference_server.backend import get_llm
from inference_server.envs import config
from inference_server.server.request import is_from_redzone
from inference_server.telemetry.event import collect_fulledit

logger = logging.getLogger(__name__)


def setup_zed_apis(app: FastAPI):

    @app.post('/zed/predict')
    async def zed_predict_edits(request: Request):
        req = await request.json()
        outline = req.get('outline', '')
        input_events = req.get('input_events', '')
        input_excerpt = req.get('input_excerpt', '')
        logger.info(f'input_event: \n{input_events}')
        logger.info(f'input_excerpt: \n{input_excerpt}')
        speculated_output = req.get('speculated_output', '')
        diagnostic_groups = req.get('diagnostic_groups', [])  # noqa

        model = get_llm()
        result = await model.raw_generate(None,
                                          outline=outline,
                                          input_events=input_events,
                                          input_excerpt=input_excerpt,
                                          speculated_output=speculated_output)
        choices = result.choices
        if len(choices):
            output = choices[0].text
        else:
            output = ''
        logger.info(f'output_excerpt: \n{output}')
        request_id = uuid.uuid4().hex
        return {
            'request_id': request_id,
            'output_excerpt': output,
        }

    @app.post('/codebuddy/predict')
    async def codebuddy_predict_edits(request: Request):
        req = await request.json()

        input_events = req.get('event', '')
        editable = req.get('editable', '')
        editable_prefix = req.get('editable_prefix', '')
        editable_suffix = req.get('editable_suffix', '')
        input_excerpt = extract_input_excerpt(editable, editable_prefix,
                                              editable_suffix)

        use_spec_edit = random.random() <= 0.5
        original_draft_text = None
        if use_spec_edit:
            original_draft_text = gen_predict_draft(editable, editable_suffix)

        model = get_llm()
        max_tokens = 1500
        if max_t := os.getenv('MAX_TOKENS', None):
            max_tokens = int(max_t)

        result = await model.raw_generate(
            None,
            outline='',
            max_tokens=max_tokens,
            input_events=input_events,
            input_excerpt=input_excerpt,
            speculated_output='',
            original_draft_text=original_draft_text)

        event_data = {
            'id': result.id,
            'created': int(time.time()),
            'lpai_service_name': config.LPAI_SERVICE_NAME,
            'use_spec_edit': use_spec_edit,
            'response': result.model_dump(),
            'input_events': input_events,
            'input_excerpt': input_excerpt,
            'original_draft_text': original_draft_text,
        }

        if not is_from_redzone(request):
            asyncio.create_task(
                collect_fulledit(result.id, data=event_data)
            )

        choices = result.choices
        if len(choices):
            output = choices[0].text
        else:
            output = ''

        if not is_from_redzone(request):
            logger.info(f'output_excerpt: \n{output}')

        lpai_service_name = config.LPAI_SERVICE_NAME
        return {
            'completion_id': result.id,
            'output_excerpt': output,
            'lpai_model': lpai_service_name,
        }


def extract_input_excerpt(editable, editable_prefix, editable_suffix):
    input_excerpt = f"{editable_prefix}<|editable_region_start|>{editable}<|editable_region_end|>{editable_suffix}"
    return input_excerpt


def gen_predict_draft(core_content: str, suffix: str):
    draft = f"<|editable_region_start|>{core_content}<|editable_region_end|>{suffix}"
    return draft
