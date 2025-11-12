from inference_server.backend import get_llm
from inference_server.externalservice.codebuddy_fe import get_record_by_completion_id
from inference_server.externalservice.ep_lpai_service import completion_by_lpai


async def reproduce_by_completion_id(completion_id, **kwargs):
    record = get_record_by_completion_id(completion_id)
    prompt = record.get('prompt')

    lang = prompt.get('language')
    prefix = prompt.get('segments', {}).get('prefix')
    suffix = prompt.get('segments', {}).get('suffix')
    stop = prompt.get('stop', [])

    return await get_llm().code_complete_v2(lang,
                                            prefix,
                                            suffix,
                                            stop=stop,
                                            **kwargs)


def reproduce_completion_id_by_lpai_service(service_name, completion_id):
    record = get_record_by_completion_id(completion_id)
    prompt = record.get('prompt')

    lang = prompt.get('language')
    prefix = prompt.get('segments', {}).get('prefix')
    suffix = prompt.get('segments', {}).get('suffix')
    # suffix = suffix[:80]
    print(f'prefix=========================\n{prefix}')
    print(f'suffix=========================\n{suffix}')
    print('================================')

    res = completion_by_lpai(service_name, lang, prefix, suffix)
    return res
