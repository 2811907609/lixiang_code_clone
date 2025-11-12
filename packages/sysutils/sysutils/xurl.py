from urllib.parse import urlparse

_schemes = ['ssh', 'http', 'https', 'ftp']


def has_scheme(u: str):
    for scheme in _schemes:
        if u.startswith(scheme + '://'):
            return True
    return False


def url_parse(u: str):
    if u.startswith('//'):
        return urlparse(u)
    else:
        if has_scheme(u):
            return urlparse(u)
        else:
            return urlparse('//' + u)
