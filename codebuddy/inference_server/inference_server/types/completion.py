import re
import time
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel


class PromptComposeInfo(BaseModel):
    used_prefix: str = ''
    used_suffix: str = ''
    used_rag: str = ''
    language_header_length: int = 0
    rag_length: int = 0
    rag_used_length: int = 0
    prefix_length: int = 0
    prefix_used_length: int = 0
    suffix_length: int = 0
    suffix_used_length: int = 0

    stop: list[str] = None
    max_new_tokens: int = None

    no_prompt_cutoff: bool = False


def split_lines(text: str) -> list[str]:
    '''split lines and add '\n' to each line except the last one'''
    if not text:
        return []
    lines = text.split('\n')
    for i in range(len(lines) - 1):
        lines[i] = lines[i] + '\n'
    if lines[-1] == '':
        lines.pop()
    return lines


_reg_only_auto_closing_close_chars = re.compile(r'^([)\]}>"\'`,;]|(\/>))*$')


def is_at_line_end(suffix: str) -> bool:
    '''|hello| is not at line end
    ||, |}|, |]|, |]])| are at line end
    '''
    s = (suffix or '').rstrip()
    if not s:
        return True
    return _reg_only_auto_closing_close_chars.match(s)


class CompletionItem:

    def __init__(self, prompt_info: Optional[PromptComposeInfo]):
        self._prompt = prompt_info
        self.prefix_lines = split_lines(prompt_info.used_prefix)
        self.suffix_lines = split_lines(prompt_info.used_suffix)

        if self.prefix_lines:
            self.current_line_prefix = self.prefix_lines[-1]
        else:
            self.current_line_prefix = ''

        if self.suffix_lines:
            self.current_line_suffix = self.suffix_lines[0]
        else:
            self.current_line_suffix = ''

        self.at_line_end = is_at_line_end(self.current_line_suffix)

        self.out_lines: Optional[list[str]] = None
        self.is_empty_output = False

        self.fixed_kinds = set()  # fixes applied

    def set_output(self, output_text: str):
        if not output_text:
            self.out_lines = []
            self.is_empty_output = True
            return
        self.out_lines = split_lines(output_text)

    def output_text(self) -> str:
        return ''.join(self.out_lines)

    def max_new_tokens(self) -> int:
        return self._prompt.max_new_tokens


@dataclass
class CompletionContext:
    start_time: float
    timeout_duration: float

    def is_timeout(self) -> bool:
        return time.perf_counter() - self.start_time > self.timeout_duration


def default_completion_context() -> CompletionContext:
    return CompletionContext(
        start_time=time.perf_counter(),
        # 当前agent 侧限制了1.1s就超时就报错，这里我们需要控制减少agent超时的情况
        # agent 那边超时后是直接报错，那怕推理了很多也都废了
        timeout_duration=0.75,
    )
