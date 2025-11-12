from inference_server.types import (
    CompletionItem,
    CompletionResponse,
    PromptComposeInfo,
)

from .endline import fix_endline_partial_trim
from .fix_duplicate import (
    drop_duplicate_suffix,
    fix_fim_multiline_duplicate,
    remove_duplicated_block_closing_line,
)
from .fix_markdown import remove_markdown_code_blocks

_fixes = [
    remove_markdown_code_blocks,
    fix_endline_partial_trim,
    fix_fim_multiline_duplicate,
    drop_duplicate_suffix,
    remove_duplicated_block_closing_line,
]


def fix_output(prompt: PromptComposeInfo, output: CompletionResponse):
    for choice in output.choices:
        choice.origin_text = choice.text
        item = CompletionItem(prompt)
        item.set_output(choice.text)
        finish_reason = choice.finish_reason
        for fix in _fixes:
            fix(item, finish_reason=finish_reason, usage=output.usage)
        choice.text = item.output_text()
        choice.set_fix_kinds(item.fixed_kinds)
