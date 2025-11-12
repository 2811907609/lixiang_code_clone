def parse_kv_pairs(s, sep=";"):
    '''parse kv paris from string like a=123;b=456;c=hello '''
    pairs = s.split(sep)
    result = {}
    for pair in pairs:
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k] = v
    return result


def is_blank(line: str) -> bool:
    return not line.strip()
