import os

from repotools.text_parser import pretty_print
from repotools.text_parser.code_parser import CodeParser, Point


def test_code_parser():
    lang = os.getenv('LANG')
    content = '''
#include <math.h>
#include "local.h"

int sum(int a, int b) {
    return a+b;
}
'''
    code_parser = CodeParser(lang, content=content)
    names = code_parser.extract_include_names()
    print('names: ', names)


def test_extract_outlines():
    lang = os.getenv('TSLANG')
    file = os.getenv('FILE')
    code_parser = CodeParser(lang, filepath=file)
    outlines = code_parser.extract_outlines()
    print('outlines: ', outlines)

    current = code_parser.extract_current_snippet(Point(8, 0))
    print('current snippet', current)


def test_extract_entities():
    lang = os.getenv('TSLANG')
    file = os.getenv('FILE')
    code_parser = CodeParser(lang, filepath=file)
    root_node = code_parser._treesitter._ts_root_node
    pretty_print(root_node, bytes(code_parser.content, 'utf8'))
    code_parser.extract_name_entities()
