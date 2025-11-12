import asyncio

%load_ext autoreload # noqa
%autoreload 2 # noqa

from benchmark.benchmark import run_benchmark, load_config


async def run_ct2_codellama(instance):
    configpath = './benchmark/config.json'
    instance = 'ct2-codellama-finetuned'
    config = load_config(configpath)
    if not config:
        return
    model_basedir = config.get('model_basedir')
    instance_config = config.get('instances', {}).get(instance)
    await run_benchmark(model_basedir, instance_config.get('env'),
                        use_dummy=True,
                        input_len=64, max_tokens=64)


%time asyncio.run(run_ct2_codellama('ct2-codellama-finetuned')) # noqa
