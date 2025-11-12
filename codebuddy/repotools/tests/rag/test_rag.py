import os

from repotools.rag import Point, Rag


def test_include_rag():
    ''' Run it like following
    TSLANG=c WORKSPACE=~/code/opensource/postgres FILE=/Users/zhangxudong/code/opensource/postgres/src/backend/access/heap/visibilitymap.c uv run pytest -vv -s -k test_include
    '''
    lang = os.getenv('TSLANG')
    file = os.getenv('FILE')
    workdir = os.getenv('WORKSPACE')

    r = Rag(workdir=workdir, lang=lang, current_file=file)
    chunks = r.include_rag(Point(192, 0))
    for c in chunks:
        print('include rag chunks: ', c)


def test_entity_rag():
    ''' Run it like following
    TSLANG=c WORKSPACE=~/code/opensource/postgres FILE=/Users/zhangxudong/code/opensource/postgres/src/backend/access/heap/visibilitymap.c  uv run pytest -vv -s -k test_entity_rag
    '''
    lang = os.getenv('TSLANG')
    file = os.getenv('FILE')
    workdir = os.getenv('WORKSPACE')

    r = Rag(workdir=workdir, lang=lang, current_file=file)
    chunks = r.entity_rag(Point(192, 0))
    for c in chunks:
        print('entity rag chunks: ', c)
