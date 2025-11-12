import requests

_default_host = 'https://lpai-inference-doudian.inner.chj.cloud'


def completion_by_lpai(service_name,
                       language,
                       prefix,
                       suffix,
                       max_tokens=None,
                       stop=None):
    """
    使用提供的服务名称、语言、前缀、后缀和停止符号，
    调用外部服务并返回结果。
    """
    host = _default_host
    url = f'{host}/inference/sc-ep/{service_name}/v1/completions'
    body = {
        'language': language,
        'segments': {
            'prefix': prefix,
            'suffix': suffix,
        },
        'stop': stop,
        'max_tokens': max_tokens or 64,
    }
    response = requests.post(url, json=body)
    try:
        res = response.json()
    except Exception:
        print(f'无法解析响应：{response.text}')
    return res
