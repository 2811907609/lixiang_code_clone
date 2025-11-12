import os


def _trim_value(s):
    if len(s) >= 2:
        if s[0] == '"' and s[-1] == '"':
            return s[1:-1]
        if s[0] == "'" and s[-1] == "'":
            return s[1:-1]
    return s


def load_env_file(env_file_path):
    envs = {}
    with open(env_file_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[len('export '):]
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k:
                envs[k] = _trim_value(v)
    for k, v in envs.items():
        os.environ[k] = v
