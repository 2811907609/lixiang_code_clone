import logging
import os
from dataclasses import dataclass
from typing import Optional, Set

from repotools.language import OutlineChunk, get_lang_config
from repotools.repo.workspace import Workspace
from repotools.similarity import jacard
from repotools.text_parser import CodeParser, Point
from repotools.tokenize import simple_tokenize

logger = logging.getLogger(__name__)

_default_semi_score_threshold = 0.25


@dataclass
class RagIncludeOutput(OutlineChunk):
    score: float = 0.0
    path: Optional[str] = None


class Rag:

    def __init__(
        self,
        workdir: str,
        lang: str,
        current_file: Optional[str] = None,
        simi_score_threshold: float = _default_semi_score_threshold,
    ) -> None:
        self._lang = lang
        self._workdir = workdir
        self._semi_score_threshold = simi_score_threshold
        self._lang_config = get_lang_config(lang)

        lang_extensions = self._lang_config.file_extensions
        self._workspace = Workspace(workdir, exitensions=lang_extensions)
        self._current_file = current_file
        self._code_parser = CodeParser(lang, filepath=current_file)

    def fullpath(self, rel_path: str) -> str:
        return os.path.join(self._workdir, rel_path)

    def include_rag(self, point: Point) -> list[RagIncludeOutput]:
        '''根据当前代码函数块进行include文件的相似度召回'''
        current_snippet = self._code_parser.extract_current_snippet(point)
        if not current_snippet:
            return []
        current_snippet_tokens = simple_tokenize(current_snippet)
        include_names = self._code_parser.extract_include_names()
        all_chunks = []
        for name in include_names:
            chunks = self._include_rag_single_name(name, current_snippet_tokens,
                                                   point)
            all_chunks += chunks
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        return all_chunks

    def _include_rag_single_name(
        self,
        include_name: str,
        current_tokens: Set[str],
        point: Point,
    ) -> list[RagIncludeOutput]:
        closest_files = self._workspace.get_closest_files(self._current_file,
                                                          include_name,
                                                          top_count=1)
        similarity_chunks = []
        # top_count=1, so there will be only one file
        for file in closest_files:
            code_parser = CodeParser(self._lang, filepath=self.fullpath(file))
            outlines = code_parser.extract_outlines()
            for outline in outlines:
                outline_tokens = simple_tokenize(outline.text)
                score = jacard(current_tokens, outline_tokens)
                if score < self._semi_score_threshold:
                    continue
                # avoid float in JSON (NaN may lead to error)
                score = int(score * 1000)
                chunk = RagIncludeOutput(outline, path=file, score=score)
                similarity_chunks.append(chunk)
        return similarity_chunks

    def entity_rag(self, point: Point) -> list[RagIncludeOutput]:
        '''根据当前代码函数块里的命名实体进行include文件的相关性召回'''
        current_node = self._code_parser.extract_current_node(point)
        if not current_node:
            return []
        entity_names = self._code_parser.extract_name_entities(current_node)
        logging.debug(f'entity_names: {entity_names}')
        include_names = self._code_parser.extract_include_names()
        all_chunks = []
        for name in include_names:
            chunks = self._include_entity_rag_single_name(name, entity_names)
            all_chunks += chunks
        return all_chunks

    def _include_entity_rag_single_name(
        self,
        include_name: str,
        entity_names: Set[str],
    ) -> list[RagIncludeOutput]:
        closest_files = self._workspace.get_closest_files(self._current_file,
                                                          include_name,
                                                          top_count=1)
        chunks = []
        for file in closest_files:
            code_parser = CodeParser(self._lang, filepath=self.fullpath(file))
            outline_signatures = code_parser.extract_outline_signatures()
            for entity in entity_names:
                if entity in outline_signatures:
                    matched = outline_signatures[entity]
                    chunk = code_parser.convert_match_to_outline_chunk(matched)
                    if chunk:
                        chunks.append(chunk)
        return chunks
