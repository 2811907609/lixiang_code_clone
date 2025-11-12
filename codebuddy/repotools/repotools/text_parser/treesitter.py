from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from tree_sitter import Language, Parser


@lru_cache(maxsize=100)
def get_language(lang: str) -> Optional[Language]:
    import tree_sitter_c as ts_c
    import tree_sitter_python as ts_python
    m = {
        'python': ts_python,
        'c': ts_c,
    }
    if lang in m:
        return Language(m[lang].language())
    else:
        raise Exception(f'language {lang} not supported')


def pretty_print(node, source_code, indent=0):
    """
    Recursively prints the Tree-sitter node and its children with indentation.

    :param node: The current Tree-sitter node to print.
    :param source_code: The original source code as bytes.
    :param indent: Current indentation level (used internally for recursion).
    """
    indentation = '  ' * indent
    node_type = node.type
    start_point = node.start_point  # (row, column)
    end_point = node.end_point
    text = source_code[node.start_byte:node.end_byte].decode('utf-8').strip()

    print(f"{indentation}{node_type} [{start_point} - {end_point}]: {text}")

    for child in node.children:
        pretty_print(child, source_code, indent + 1)
        if indent <= 1:
            print(f'\n{"-" * 20}\n')


@dataclass
class Point:
    '''same as treesitter point's row and col, it is 0 based.'''
    row: int
    col: int

    def __gt__(self, other):
        return self.row > other.row or (self.row == other.row and
                                        self.col > other.col)

    def __ge__(self, other):
        return self.row > other.row or (self.row == other.row and
                                        self.col >= other.col)

    def __lt__(self, other):
        return other > self

    def __le__(self, other):
        return other >= self


class Treesitter:

    def __init__(self, lang: str, content: str) -> None:
        self._lang = lang.lower()
        self._content = content
        self._ts_lang = get_language(lang)
        self._ts_tree = Parser(self._ts_lang).parse(bytes(content, 'utf8'))
        self._ts_root_node = self._ts_tree.root_node

    @property
    def root_node(self):
        return self._ts_root_node

    def node_text(self, n):
        if n:
            return n.text.decode('utf-8')

    def gen_query(self, query: str):
        return self._ts_lang.query(query)

    def query(self, query: str, root=None):
        if not root:
            root = self._ts_root_node
        q = self.gen_query(query)
        return q.matches(root)

    def extract_node_at_point(self, point: Point):
        p = (point.row, point.col)
        return self._ts_root_node.descendant_for_point_range(p, p)
