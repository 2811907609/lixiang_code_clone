language_properties = {
    'golang': {
        'comment':
            '//',
        'stop_words': [
            '\n//',
            '\nfunc',
            '\nimport',
            '\npackage',
            'package ',  # deepseek coder may returns package xxx
        ],
    },
    'python': {
        'comment':
            '#',
        'stop_words': [
            '\n#',
            '\n\n\n',
            '\ndef',
            '\nclass',
            '\nfrom',
            '\nprint',  # for phi-1, it always gives a demo like print(fab(5))
        ],
    },
    'javascript': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nfunction',
            '\nimport',
            '\nclass',
        ],
    },
    'typescript': {
        'comment':
            '//',
        'stop_words': [
            '\n//',
            '\nfunction',
            '\nimport',
            '\nclass',
            '\ninterface',
            '\ntype',
        ],
    },
    'java': {
        'comment': '//',
        'stop_words': ['\n//',],
    },
    'c': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nextern',
            '\ntypedef',
            '\nunion',
            '\nvoid',
        ],
    },
    'cpp': {
        'comment':
            '//',
        'stop_words': [
            '\n//',
            '\nextern',
            '\ntypedef',
            '\nunion',
            '\nvoid',
            '\nnamespace',
            '\ntemplate',
            '\nusing',
        ],
    },
    'rust': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nmod',
            '\nuse',
        ],
    },
    'lua': {
        'comment': '--',
        'stop_words': ['\n--',],
    },
    'sql': {
        'comment': '--',
        'stop_words': ['\n--',],
    },
}

language_alias = {
    'go': 'golang',
    'c++': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'hpp': 'cpp',
    'cppm': 'cpp',
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
}

for k, v in language_alias.items():
    if k not in language_properties:
        language_properties[k] = language_properties[v]


def get_language_property(lang: str):
    return language_properties.get(lang, {})


def get_language_comment_mark(lang: str) -> str:
    if lang in language_properties:
        return language_properties[lang].get('comment', '')
    return ''


def gen_language_comment_line(lang: str):
    # TODO disable language prompt line
    if not lang:
        return ''
    comment = get_language_comment_mark(lang)
    if not comment:
        return ''
    return f'{comment} this is {lang} code\n\n'
