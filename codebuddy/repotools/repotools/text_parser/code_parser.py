from collections import defaultdict
from typing import Optional

from repotools.language import OutlineChunk, get_lang_config

from .treesitter import Point, Treesitter


class SafeDictEmpty(defaultdict):
    '''this dict will return "" for missing key, this is used
    in str.format so that "a {a}, b {b}".format(a=1) will not
    get error and will get "a 1, b ".
    '''

    def __missing__(self, key):
        return ''


class CodeParser:

    def __init__(
        self,
        lang: str,
        content: Optional[str] = None,
        filepath: Optional[str] = None,
    ) -> None:
        self._lang = lang
        self._lang_config = get_lang_config(lang)
        if content:
            self.content = content
        elif filepath:
            with open(filepath, 'r') as f:
                self.content = f.read()
        else:
            raise Exception('content or filepath must be provided')

        self._treesitter = Treesitter(lang, self.content)

    def extract_current_node(self, point: Point):
        '''注意tressitter query Point的行号列号都是从0开始的'''
        current_snippet_config = self._lang_config.current_snippet
        if current_snippet_config:
            if kinds := current_snippet_config.node_kinds:
                n = self._treesitter.extract_node_at_point(point)
                while n:
                    if n.type in kinds:
                        return n
                    n = n.parent

    def extract_current_snippet(self, point: Point):
        '''注意tressitter query Point的行号列号都是从0开始的'''
        current_node = self.extract_current_node(point)
        if current_node:
            return self._treesitter.node_text(current_node)

    def extract_name_entities(self, current_node=None):
        '''this will extract name entities, like type name, function name'''
        if not self._lang_config:
            raise Exception(f'no language config for {self._lang}')
        name_entities_config = self._lang_config.parse_name_entities
        if not name_entities_config.query:
            raise Exception(f'no outline query config for {self._lang}')
        matches = self._treesitter.query(name_entities_config.query,
                                         root=current_node)
        if not matches:
            return set()
        names = []
        for match in matches:
            matched = match[1]
            for _, nodes in matched.items():
                names.append(self._treesitter.node_text(nodes[0]))
        return set(names)

    def _trim_include_name(self, name: str) -> str:
        '''simple format, convert "math.h" -> math.h '''
        parse_config = self._lang_config.parse_includes
        if parse_config.trim_prefixes:
            name = name.lstrip(''.join(parse_config.trim_prefixes))
        if parse_config.trim_suffixes:
            name = name.rstrip(''.join(parse_config.trim_suffixes))
        return name

    def extract_include_names(self):
        '''this will extract include/import names of source code'''
        if not self._lang_config:
            raise Exception(f'no language config for {self._lang}')
        include_config = self._lang_config.parse_includes
        if not include_config.query:
            raise Exception(f'no query config for {self._lang}')

        matches = self._treesitter.query(include_config.query)
        if not matches:
            return []

        names = []
        for match in matches:
            for _, nodes in match[1].items():
                for node in nodes:
                    n = self._treesitter.node_text(node)
                    names.append(self._trim_include_name(n))
        return names

    def extract_outline_matches(self) -> list:
        '''this will extract outline matches of whole source code'''
        if not self._lang_config:
            raise Exception(f'no language config for {self._lang}')
        outline_config = self._lang_config.parse_outlines
        if not outline_config.query:
            raise Exception(f'no outline query config for {self._lang}')
        matches = self._treesitter.query(outline_config.query)
        if not matches:
            return []
        return [m[1] for m in matches]

    def extract_outline_signatures(self) -> dict:
        matches = self.extract_outline_matches()
        sig_map = {}
        for m in matches:
            for key, nodes in m.items():
                if key == 'sig_name':
                    sig_name = self._treesitter.node_text(nodes[0])
                    sig_map[sig_name] = m
        return sig_map

    def extract_outlines(self) -> list[OutlineChunk]:
        '''this will extract outlines of whole source code'''
        matches = self.extract_outline_matches()
        chunks = []
        for matched in matches:
            chunk = self.convert_match_to_outline_chunk(matched)
            if chunk:
                chunks.append(chunk)
        return chunks

    def convert_match_to_outline_chunk(self,
                                       matched: dict) -> Optional[OutlineChunk]:
        outline_config = self._lang_config.parse_outlines
        formatter = None
        tmpl_ctx = SafeDictEmpty()
        sig_name = ''
        for key, nodes in matched.items():
            node_text = self._treesitter.node_text(nodes[0])
            if key == 'sig_name':
                sig_name = node_text
            if key in outline_config.formatter:
                tmpl_ctx[key] = node_text
                formatter = outline_config.formatter[key]
        if formatter:
            text = formatter.fmt.format_map(tmpl_ctx)
            chunk = OutlineChunk(type=formatter.type_name,
                                 sig_name=sig_name,
                                 text=text)
            return chunk
