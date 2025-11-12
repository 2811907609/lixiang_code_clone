import os
from dataclasses import fields
from functools import lru_cache

# ruff: noqa: E402  # Module level import not at top of file


def disable_track():
    os.environ['DO_NOT_TRACK'] = '1'
    os.environ['VLLM_NO_USAGE_STATS'] = '1'


# should run disable track before import vllm
disable_track()

try:
    import vllm
    from vllm import AsyncEngineArgs
    from vllm.entrypoints.openai.cli_args import make_arg_parser
    from vllm.utils import FlexibleArgumentParser
except Exception as e:
    print('vllm not installed, please install it', e)

from inference_server.config import InstanceConfig
from inference_server.utils import getLogger

logger = getLogger(__name__)

# these args are not defined in AsyncEngineArgs, need to add them to the parser
_vllm_supported_args = {
    'enable_reasoning',
    'reasoning_parser',
    'disable_log_requests',
}


@lru_cache(maxsize=None)
def _get_supported_args():
    arg_fields = fields(AsyncEngineArgs)
    return {a.name for a in arg_fields} | _vllm_supported_args


# just enable a feature group to set multiple args
_feature_groups = {
    '_ngram_spec_decoding': {
        'speculative_config': {
            'num_speculative_tokens': 5,
            'method': 'ngram',
            'prompt_lookup_max': 5,
        },
    },
    '_enable_logprobs': {
        'max_logprobs': 5,
        'disable_logprobs_during_spec_decoding': False,
    },
}


def update_feature_groups(args: dict):
    params = {}
    enable_spec_edit = args.get('enable_spec_edit', False)
    if enable_spec_edit:
        from inference_server.modules.specedit.lib import patch_spec_edit
        patch_spec_edit()  #apply spec edit patch
        logger.info(f' spec decode {vllm.spec_decode.ngram_worker.NGramWorker}')

    # copy feature groups firstly so that args can override it
    for k, v in _feature_groups.items():
        if args.get(k):
            params.update(v)
            args.pop(k)

    if spec_tokens := args.get('num_speculative_tokens'):
        if params.get('speculative_config'):
            params['speculative_config']['num_speculative_tokens'] = spec_tokens

    params.update(args)
    return params


def create_async_args(modelpath: str,
                      trust_remote_code=True,
                      instance_config: InstanceConfig = None):
    parser = FlexibleArgumentParser(description="vLLM's remote OpenAI server.")
    parser = make_arg_parser(parser)
    args = parser.parse_args([])
    args.model = modelpath
    args.trust_remote_code = trust_remote_code
    args.disable_fastapi_docs = True

    model_params = instance_config.model_params
    params = update_feature_groups(model_params)

    supported_param_keys = _get_supported_args()
    for key in supported_param_keys:
        if key in params:
            v = params[key]
            setattr(args, key, v)

    return args
