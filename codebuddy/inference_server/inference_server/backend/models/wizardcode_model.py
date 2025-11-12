from inference_server.backend.common import register
from inference_server.backend.infer_engines.ct2 import CT2Generic


@register('ct2_wizardcoder')
class CT2WizardCoder(CT2Generic):

    def fim_prompt(self, prefix, suffix, lang=None):
        return f'<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>'
