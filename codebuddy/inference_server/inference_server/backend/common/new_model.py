import os

from typing import Optional

from inference_server.config import InstanceConfig
from inference_server.backend.common.register_cls import get_class_by_model_type, get_class_by_name
from inference_server.backend.state import get_llm, set_llm
from inference_server.utils import getLogger

logger = getLogger(__name__)

_env_prefix = 'EP_LLM_'


def get_params_from_env():
    params = {}
    for k, v in os.environ.items():
        if k.startswith(_env_prefix):
            k = k[len(_env_prefix):].lower()
            params[k] = v
    return params


async def init_llm_v2(ins: InstanceConfig):
    model_type = ins.model_type
    if not model_type:
        logger.error(f'Model type "{model_type}" not specified')
        exit(1)
    cls = get_class_by_model_type(model_type)
    return await cls.new_model(instance_config=ins, **ins.model_params)


async def init_llm(instance_config: Optional[InstanceConfig] = None):
    if instance_config and instance_config.embeddings:
        return await init_llm_v2(instance_config)

    model_type = instance_config.model_type
    if not model_type:
        logger.error(f'Model type "{model_type}" not specified')
        exit(1)
    cls = get_class_by_model_type(model_type)
    if not cls:
        logger.error(f'unsupported model type: {model_type}')
        exit(1)
    model_path = instance_config.model_path
    if not model_path:
        logger.error('you must give a modelpath')
        exit(1)
    params = instance_config.model_params
    transformer_modelpath = params.pop('transformer_model_path', None)
    llm = await cls.new_model(model_path,
                              transformer_modelpath=transformer_modelpath,
                              instance_config=instance_config,
                              **params)
    return llm


async def get_and_update_llm(instance_config: Optional[InstanceConfig] = None):
    if not instance_config:
        return await _get_and_update_llm(instance_config=None)
    if not instance_config.is_multi_instance:
        m = await _get_and_update_llm(instance_config=instance_config,
                                      instance_name=instance_config.name)
        set_llm(m, 'default')
        return m
    for _, ins in instance_config.subinstances.items():
        await _get_and_update_llm(ins, ins.name)


async def _get_and_update_llm(instance_config: Optional[InstanceConfig] = None,
                              instance_name='default'):
    '''help only used in jupyter notebook/ipython, to avoid long loading time
of large models.'''
    llm = get_llm(instance_name)
    if not llm:
        m = await init_llm(instance_config)
        set_llm(m, instance_name)
        return m
    else:
        # get class name of old model and get it from globals since we may have update it
        clsname = llm.__class__.__name__
        cls = get_class_by_name(clsname)
        m = cls.renew(llm)
        if hasattr(llm, 'cleanup'):
            await llm.cleanup()
        set_llm(m, instance_name)
        return m
