import re

_pattern_scp_like_uri = re.compile(r'^[\w\-]+@[\w\-\.]+:')  # git@xxxx:a/b/c.git


def is_scp_like_uri(uri: str) -> bool:
    return _pattern_scp_like_uri.match(uri) is not None
