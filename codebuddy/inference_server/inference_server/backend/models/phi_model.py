from inference_server.backend.common import register
from inference_server.backend.infer_engines.ct2 import CT2Generic


@register('ct2_phi_1_5', 'ct2_phi_2')
class CT2Phi(CT2Generic):
    # Phi 因为不支持fim，频繁出现多补的情况, 这里限定成行补全
    stop_words = ['\n', '\n\n']

    def fim_prompt(self, prefix, suffix, lang=None):
        # phi doesn't support fim, so we use a trick to make it work
        return prefix
