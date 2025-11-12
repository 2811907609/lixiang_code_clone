'''
use following to reload module
import importlib; importlib.reload(f)

'''

import logging

import uvloop

from inference_server.envs import config
from inference_server.backend import get_llm, get_and_update_llm, load_model_by_instance
from inference_server.server import register, run_server
from inference_server.server.prestart import prestart_check

logging.basicConfig(level=logging.DEBUG)


async def main():
    instance_name = config.INSTANCE_NAME
    config_path = config.CONFIG_PATH
    port = config.PORT
    if instance_name:
        instance_config, _ = await load_model_by_instance(
            instance_name, config_path=config_path)
        llm = get_llm()
    else:
        llm = await get_and_update_llm()

    # await warmup_all(instance_config)

    # register should happen after model is loaded since model load takes very long time
    await prestart_check()
    register(instance_config)

    await run_server(llm, port=port)


if __name__ == '__main__':
    uvloop.run(main())
