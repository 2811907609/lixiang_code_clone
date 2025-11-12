import re

from inference_server.types import CompletionItem
from inference_server.types import UsageInfo
from inference_server.config.features import feature_gate


# sometimes, output text is not completed due to max_tokens limitation
# we just drop last line if got this situation
def trim_last_line(text, max_tokens, output_len):
    if feature_gate.benchmark:
        return text
    if output_len + 4 < max_tokens:
        return text
    return _trim_last_line(text)


def _trim_last_line(text):
    # avoid trim if there is only one line
    if '\n' not in text:
        return text
    last_newline_index = text.rfind('\n')
    return text[:last_newline_index] + '\n'


def fix_endline_partial_trim(item: CompletionItem,
                             *args,
                             finish_reason: str = None,
                             usage: UsageInfo = None,
                             **kwargs):

    def should_trim():
        if finish_reason in ('length', 'timeout'):
            return True
        output_token_len = usage.completion_tokens
        max_new_token_len = item.max_new_tokens()
        if output_token_len and max_new_token_len:
            # 接近输出上限时候，可能存在尾部不完全的情况，需要trim
            # 正常来说如果因为到达上限的原因，finish_reason是length
            # 某些情况下推理工具可能没有给这个reason，这里也特别处理下
            if output_token_len + 3 >= max_new_token_len:
                return True
        return False

    if should_trim():
        if len(item.out_lines) >= 2:
            item.out_lines.pop()
            item.fixed_kinds.add(fix_endline_partial_trim.__name__)


# sometimes, output text is not completed due to max_tokens limitation
# we just drop last word if got this situation
def trim_last_word(text, max_tokens, output_len):
    if feature_gate.benchmark:
        return text
    if output_len + 4 < max_tokens:
        return text
    # avoid trim if there is only one line
    if '\n' not in text:
        return text
    match = re.search(r'\w*$', text)
    if match:
        print('match', match.start())
        return text[:match.start()]
    else:
        return text
