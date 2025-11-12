from Levenshtein import distance

from inference_server.types import CompletionItem
from inference_server.utils.strings import is_blank

from .utils import is_block_closing_line


def fix_fim_multiline_duplicate(item: CompletionItem, *args, **kwargs):
    '''if user is typing in the middle of a line, and the AI outputs multiple
    lines.
    if the first line ends with the current line suffix, remove the suffix
    and use the first line.
    Otherwise, it is a bad completion, so we should return an empty string.
    '''
    if item.is_empty_output:
        return
    if item.at_line_end or len(item.out_lines) <= 1:
        return

    suffix = item.current_line_suffix.rstrip()
    if not suffix:
        return
    first_completion_line = item.out_lines[0].rstrip()
    if first_completion_line.endswith(suffix):
        trimmed_line = first_completion_line[:-len(suffix)]
        item.out_lines = [trimmed_line]
    else:
        item.out_lines = []
    item.fixed_kinds.add(fix_fim_multiline_duplicate.__name__)


def drop_duplicate_suffix(item: CompletionItem, *args, **kwargs):
    out_lines = item.out_lines
    if not out_lines:
        return
    suffix_lines = item.suffix_lines
    if not suffix_lines:
        return

    out_index = 0
    while out_index < len(out_lines) and is_blank(out_lines[out_index]):
        out_index += 1
    suffix_index = 0
    while suffix_index < len(suffix_lines) and is_blank(
            suffix_lines[suffix_index]):
        suffix_index += 1
    line_count = min(3,
                     len(out_lines) - out_index,
                     len(suffix_lines) - suffix_index)
    if line_count < 1:
        return
    out_text = ''.join(out_lines[out_index:out_index + line_count]).strip()
    if len(out_text) <= 1:
        return
    suffix_text = ''.join(suffix_lines[suffix_index:suffix_index +
                                       line_count]).strip()
    threshold = max(1, 0.05 * len(out_text), 0.05 * len(suffix_text))
    if distance(out_text, suffix_text) <= threshold:
        item.out_lines = []
        item.fixed_kinds.add(drop_duplicate_suffix.__name__)


def remove_duplicated_block_closing_line(item: CompletionItem, *args, **kwargs):
    out_lines = item.out_lines
    suffix_lines = item.suffix_lines
    if len(out_lines) < 2:
        return
    full_out_lines = [i for i in out_lines]
    full_out_lines[0] = item.current_line_prefix + full_out_lines[0]
    if not is_block_closing_line(full_out_lines, len(full_out_lines) - 1):
        return
    end_line = full_out_lines[-1]
    if not end_line.strip():
        return
    # Why from 1
    suffix_begin_index = 1
    while suffix_begin_index < len(suffix_lines) and is_blank(
            suffix_lines[suffix_begin_index]):
        suffix_begin_index += 1
    if suffix_begin_index >= len(suffix_lines):
        return
    suffix_begin_line = suffix_lines[suffix_begin_index]
    if end_line.startswith(suffix_begin_line.rstrip()) or \
        suffix_begin_line.startswith(end_line.rstrip()):
        item.out_lines = out_lines[:-1]
        item.out_lines[-1] = item.out_lines[-1].rstrip()
        item.fixed_kinds.add(remove_duplicated_block_closing_line.__name__)
