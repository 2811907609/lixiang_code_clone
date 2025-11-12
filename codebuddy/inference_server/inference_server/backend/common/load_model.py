import os

from inference_server.config import Config, InstanceConfig
from .new_model import get_and_update_llm
from inference_server.backend.state import get_llm


async def load_model_by_instance(instance,
                                 config_path=None,
                                 model_path=None,
                                 num_speculative_tokens=None,
                                 enable_spec_edit=False,
                                 **kwargs):
    # # Import models here to avoid circular import while ensuring registration
    # import inference_server.backend.models  # noqa

    config = Config(config_path)
    instance_config = config.load_instance(instance)

    if model_path:
        instance_config.model_path = model_path
    if num_speculative_tokens:
        kwargs['num_speculative_tokens'] = num_speculative_tokens
    if enable_spec_edit:
        kwargs['enable_spec_edit'] = True

    if 'speculative_model' in kwargs and kwargs['speculative_model'] is None:
        kwargs.pop('speculative_model')
    if 'gpu_memory_utilization' in kwargs and kwargs['gpu_memory_utilization'] is None:
        kwargs.pop('gpu_memory_utilization')

    instance_config.model_params.update(kwargs)

    if envs := instance_config.get('env'):
        for k, v in envs.items():
            os.environ[k] = v
    await get_and_update_llm(instance_config=instance_config)
    return instance_config, config


async def warmup_instance(ins: InstanceConfig):
    ''' warmup each model, since some model (Lora) is lazy loaded'''
    llm = get_llm(ins.name)
    if ins.embeddings:
        llm.embed('hello')
        return
    models = ins.get('models', {})
    for model_name in models:
        # embedding model do not have completion function, no need to warmup
        if hasattr(llm, 'code_complete_v2'):
            await llm.code_complete_v2('python',
                                       '# test',
                                       '',
                                       max_tokens=4,
                                       model_name=model_name)


_warmup_done = False


async def warmup_all(ins: InstanceConfig):
    global _warmup_done
    if _warmup_done:
        return

    if not ins.is_multi_instance:
        await warmup_instance(ins)
    for _, sub_instance in ins.subinstances.items():
        await warmup_instance(sub_instance)
    _warmup_done = True
