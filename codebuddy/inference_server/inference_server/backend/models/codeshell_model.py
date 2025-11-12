from inference_server.backend.common import register
from .transformers import TransformersGeneric


@register('codeshell_transformers')
class CodeShellTransformers(TransformersGeneric):
    # same to wizard coder
    def fim_prompt(self, prefix, suffix, lang=None):
        return f'<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>'
