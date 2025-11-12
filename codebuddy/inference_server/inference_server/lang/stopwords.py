from inference_server.config.features import feature_gate

from .language import get_language_property, gen_language_comment_line

# TODO, 存在encode的时候把多个字符编码成一个token的情况, 这样会导致stop token无法匹配
# <|EOT|> is eos of deepseek coder, yuyu's base model not set this well, so add it
_default_stop_words = [
    '<|EOT|>',
    '<EOT>',
    '<s>',
    '</s>',
    '<|endoftext|>',
    '<｜end▁of▁sentence｜>',
    '<｜fim▁hole｜>',
]


def get_stop_words(lang: str):
    if feature_gate.benchmark:
        return []
    if not lang:
        return _default_stop_words
    properties = get_language_property(lang)
    if properties and 'stop_words' in properties:
        # language prompt as stop words
        comment_line = gen_language_comment_line(lang)
        stop_words = _default_stop_words + properties['stop_words']
        if comment_line.endswith("\n\n"):
            comment_line = comment_line[:-2]
            if comment_line:
                stop_words.append(comment_line)
        return stop_words
    return _default_stop_words
