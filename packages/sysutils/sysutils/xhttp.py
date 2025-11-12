'''
Most of time, package like requests is recommended.
However, since sysutils is only wrapper around system package.
I'd avoid envolving third-party packages.
But I may need to do some notifications to feishu group.
So add some simple http utils using urllib.
'''

import urllib.parse
import urllib.request
from dataclasses import dataclass

from .xjson import json_dumps, json_loads


@dataclass
class HttpResponse:
    status: int = None
    _content: bytes = None
    _text: str = None

    def ok(self):
        return self.status >= 200 and self.status < 300

    def text(self):
        if self._text is None:
            self._text = self._content.decode('utf-8')
        return self._text

    def json(self):
        return json_loads(self.text())


def _send_json(url, method, json_data=None, headers=None):
    json_data = json_dumps(json_data).encode('utf-8')
    if not headers:
        headers = {
            'Content-Type': 'application/json',
        }
    else:
        has_content_type = False
        for k in headers:
            if k.lower() == 'content-type':
                has_content_type = True
                break
        if not has_content_type:
            headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(url,
                                 method=method,
                                 data=json_data,
                                 headers=headers)
    with urllib.request.urlopen(req) as response:
        status = response.status
        content = response.read()
        return HttpResponse(status=status, _content=content)


def post_json(url, json=None, headers=None):
    return _send_json(url, 'POST', json, headers)


def encode_header_value(value: str) -> str:
    """
    安全地编码header值，确保符合HTTP header规范

    Args:
        value: 原始字符串值

    Returns:
        str: URL编码后的字符串，适合用作HTTP header值
    """
    if not value:
        return value

    # 对包含非ASCII字符的值进行URL编码
    try:
        # 首先尝试编码为ASCII，如果失败则进行URL编码
        value.encode('ascii')
        return value
    except UnicodeEncodeError:
        # 包含非ASCII字符，进行URL编码，保留常用的安全字符
        return urllib.parse.quote(value, safe='/:')
